"""La couche IA passe uniquement par Meta : Wonder (texte) et Image (visuel)."""

import asyncio
import os
import sys
from types import SimpleNamespace

os.environ.setdefault("META_API_KEY", "test-meta-key")

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    BadRequestError,
)
from pydantic import ValidationError

from app import meta_image_service, prompt_service
from app.config import Settings


class _FakeTextChatCompletions:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        message = SimpleNamespace(content=self.content, refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeTextClient:
    def __init__(self, completions: _FakeTextChatCompletions):
        self.chat = SimpleNamespace(completions=completions)


class _FakeImages:
    def __init__(self, url="https://cdn.meta/test.png"):
        self.url = url
        self.edit_calls: list[dict] = []
        self.generate_calls: list[dict] = []

    async def edit(self, **kwargs):
        self.edit_calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(url=self.url)])

    async def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(url=self.url)])


class _FakeImageClient:
    def __init__(self, images: _FakeImages):
        self.images = images


class _FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeHttp:
    def __init__(self, payload):
        self.payload = payload
        self.posts: list[dict] = []

    async def post(self, url, data=None, files=None):
        self.posts.append({"url": url, "data": data, "files": files})
        return _FakeHttpResponse(self.payload)


def _make_jpeg_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image as PILImage

    img = PILImage.new("RGB", (8, 8), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image as PILImage

    img = PILImage.new("RGB", (8, 8), color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://api.meta.ai/v1/images/edits")


def test_meta_model_defaults():
    settings = Settings(**{"META_API_KEY": "y"})
    assert settings.prompt_model == "muse-wonder-1.0"
    assert settings.image_model == "muse-image-1.0"
    assert settings.meta_base_url == "https://api.meta.ai/v1"


def test_meta_api_key_must_not_be_empty():
    with pytest.raises(ValidationError):
        Settings(**{"META_API_KEY": "   "})


def test_model_api_key_alias_accepted():
    settings = Settings(**{"MODEL_API_KEY": "y"})
    assert settings.meta_api_key == "y"


def test_no_legacy_provider_left():
    assert "anthropic" not in sys.modules
    assert "llama_api_client" not in sys.modules
    assert "fal_client" not in sys.modules
    assert not hasattr(Settings, "model_fields") or "fal_key" not in Settings.model_fields


def test_fixed_prompts_cover_pipeline_steps():
    assert "white studio background" in prompt_service.build_person_cleanup_prompt()
    swap = prompt_service.build_identity_swap_prompt()
    assert "IDENTICAL to Image 1" in swap
    assert "Image 2" in swap


def test_identity_swap_preserves_everything_but_appearance():
    prompt = prompt_service.build_identity_swap_prompt()
    for expected in (
        "same framing and crop",
        "same pose and position of the person",
        "same background",
        "the person becomes the person from Image 2",
        "face, hair, skin tone AND outfit",
        "the product itself stays exactly as in Image 1",
        "Do not blend facial features",
        "ONE coherent person",
    ):
        assert expected in prompt


def test_generate_edit_result_original_appearance_skips_swap(monkeypatch):
    from app.routers import generate as gen_mod

    calls: list[dict] = []

    async def _fake_generate(image_paths, prompt, aspect_ratio="auto"):
        calls.append(
            {"image_paths": list(image_paths), "prompt": prompt, "aspect_ratio": aspect_ratio}
        )
        return {"image_url": "https://cdn.meta/out.png", "description": ""}

    monkeypatch.setattr(gen_mod, "generate_image", _fake_generate)
    monkeypatch.setattr(gen_mod, "download_image", lambda url: "/tmp/fake.png")
    monkeypatch.setattr(gen_mod, "build_enhanced_prompt", lambda *a: "refined prompt")

    result, intermediates = asyncio.run(
        gen_mod._generate_edit_result(
            "/tmp/orig.jpg", "/tmp/ref.jpg", "Sac", "Sac cuir", "fond doré", "1:1",
            False, "original",
        )
    )

    assert len(calls) == 1
    assert calls[0]["image_paths"] == ["/tmp/orig.jpg"]
    assert result["image_url"] == "https://cdn.meta/out.png"
    assert intermediates == []


def test_enhanced_prompt_with_background_adds_hard_constraint(tmp_path, monkeypatch):
    image = tmp_path / "product.jpg"
    image.write_bytes(_make_jpeg_bytes())
    completions = _FakeTextChatCompletions("an enhanced prompt")
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    prompt_service.build_enhanced_prompt(
        str(image), "Robe", "Robe en coton", "fond lumineux", True
    )

    (call,) = completions.calls
    user_text = call["messages"][1]["content"][1]["text"]
    assert "Hard constraint: keep the original background exactly as it is" in user_text


def test_enhanced_prompt_without_flag_has_no_hard_constraint(tmp_path, monkeypatch):
    image = tmp_path / "product.jpg"
    image.write_bytes(_make_jpeg_bytes())
    completions = _FakeTextChatCompletions("an enhanced prompt")
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    prompt_service.build_enhanced_prompt(
        str(image), "Robe", "Robe en coton", "fond lumineux"
    )

    (call,) = completions.calls
    user_text = call["messages"][1]["content"][1]["text"]
    assert "Hard constraint" not in user_text


def test_build_prompt_demands_high_quality():
    prompt = meta_image_service.build_prompt("fond uni")
    assert "high resolution" in prompt
    assert "sharp fine details" in prompt


def test_build_prompt_protects_small_product_details():
    prompt = meta_image_service.build_prompt("fond uni")
    assert "reproduce its exact details with maximum fidelity" in prompt
    assert "do not redraw, simplify" in prompt


def test_edit_system_prompt_forces_detail_inventory():
    assert "enumerate its visible" in prompt_service._EDIT_SYSTEM_PROMPT
    assert "micro-details" in prompt_service._EDIT_SYSTEM_PROMPT


def test_generate_edit_result_swap_is_single_pass(monkeypatch):
    from app.routers import generate as gen_mod

    calls: list[dict] = []

    async def _fake_generate(image_paths, prompt, aspect_ratio="auto"):
        calls.append(
            {"image_paths": list(image_paths), "prompt": prompt, "aspect_ratio": aspect_ratio}
        )
        return {"image_url": "https://cdn.meta/out.png", "description": ""}

    monkeypatch.setattr(gen_mod, "generate_image", _fake_generate)
    monkeypatch.setattr(gen_mod, "download_image", lambda url: "/tmp/fake.png")
    monkeypatch.setattr(
        gen_mod, "build_enhanced_prompt", lambda *args: (_ for _ in ()).throw(AssertionError("no refine expected"))
    )

    result, intermediates = asyncio.run(
        gen_mod._generate_edit_result(
            "/tmp/orig.jpg", "/tmp/ref.jpg", "Sac", "Sac cuir", "", "1:1"
        )
    )

    assert len(calls) == 2
    assert calls[0]["aspect_ratio"] == "auto"
    assert "neutral pose" in calls[0]["prompt"].lower() or "studio" in calls[0]["prompt"].lower()
    assert calls[1]["image_paths"] == ["/tmp/orig.jpg", "/tmp/fake.png"]
    assert calls[1]["aspect_ratio"] == "auto"
    assert "IDENTICAL to Image 1" in calls[1]["prompt"]
    assert result == {"image_url": "https://cdn.meta/out.png", "description": ""}
    assert intermediates == ["/tmp/fake.png", "/tmp/fake.png"]


def test_generate_edit_result_swap_then_refines_with_prompt(monkeypatch):
    from app.routers import generate as gen_mod

    calls: list[dict] = []

    async def _fake_generate(image_paths, prompt, aspect_ratio="auto"):
        calls.append(
            {"image_paths": list(image_paths), "prompt": prompt, "aspect_ratio": aspect_ratio}
        )
        return {"image_url": "https://cdn.meta/out.png", "description": ""}

    monkeypatch.setattr(gen_mod, "generate_image", _fake_generate)
    monkeypatch.setattr(gen_mod, "download_image", lambda url: "/tmp/fake.png")
    monkeypatch.setattr(gen_mod, "build_enhanced_prompt", lambda *a: "refined prompt")

    result, intermediates = asyncio.run(
        gen_mod._generate_edit_result(
            "/tmp/orig.jpg", "/tmp/ref.jpg", "Sac", "Sac cuir", "fond doré", "16:9", True
        )
    )

    assert len(calls) == 3
    assert calls[2]["image_paths"] == ["/tmp/fake.png"]
    assert calls[2]["aspect_ratio"] == "16:9"
    assert calls[2]["prompt"] == "refined prompt"
    assert result["image_url"] == "https://cdn.meta/out.png"
    assert intermediates == ["/tmp/fake.png", "/tmp/fake.png"]


def test_original_appearance_without_prompt_is_nothing_to_do():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    files = {
        "image": ("product.jpg", _make_jpeg_bytes(), "image/jpeg"),
        "person_image": ("person.jpg", _make_jpeg_bytes(), "image/jpeg"),
    }
    data = {
        "product_name": "Sac",
        "product_description": "Sac cuir",
        "prompt": "",
        "aspect_ratio": "auto",
        "mannequin_id": "",
        "appearance_source": "original",
    }
    response = client.post("/api/generate", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["error"] == "nothing_to_do"


def test_generate_edit_result_without_person_is_single_edit(monkeypatch):
    from app.routers import generate as gen_mod

    calls: list[dict] = []

    async def _fake_generate(image_paths, prompt, aspect_ratio="auto"):
        calls.append(
            {"image_paths": list(image_paths), "prompt": prompt, "aspect_ratio": aspect_ratio}
        )
        return {"image_url": "https://cdn.meta/out.png", "description": ""}

    monkeypatch.setattr(gen_mod, "generate_image", _fake_generate)
    monkeypatch.setattr(gen_mod, "download_image", lambda url: "/tmp/fake.png")
    monkeypatch.setattr(gen_mod, "build_enhanced_prompt", lambda *a: "refined prompt")

    result, intermediates = asyncio.run(
        gen_mod._generate_edit_result(
            "/tmp/orig.jpg", None, "Sac", "Sac cuir", "fond doré", "1:1"
        )
    )

    assert len(calls) == 1
    assert calls[0]["image_paths"] == ["/tmp/orig.jpg"]
    assert calls[0]["aspect_ratio"] == "1:1"
    assert intermediates == []


def test_extract_text_from_string_content():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  hello  "))]
    )
    assert prompt_service._extract_text(response) == "hello"


def test_extract_text_empty_content():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
    )
    assert prompt_service._extract_text(response) == ""
    assert prompt_service._extract_text(SimpleNamespace(choices=[])) == ""


def test_data_url_format():
    assert prompt_service._data_url("image/png", "QUJD") == "data:image/png;base64,QUJD"


def test_build_enhanced_prompt_uses_wonder_with_image(tmp_path, monkeypatch):
    image = tmp_path / "product.jpg"
    image.write_bytes(b"\xff\xd8fake-jpeg")
    completions = _FakeTextChatCompletions("an enhanced prompt")
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    result = prompt_service.build_enhanced_prompt(
        str(image), "Robe", "Robe en coton", "fond de marché"
    )

    assert result == "an enhanced prompt"
    (call,) = completions.calls
    assert call["model"] == "muse-wonder-1.0"
    roles = [m["role"] for m in call["messages"]]
    assert roles == ["system", "user"]
    items = call["messages"][1]["content"]
    assert {i["type"] for i in items} == {"image_url", "text"}
    assert items[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_build_text_to_image_prompt_sends_text_only(monkeypatch):
    completions = _FakeTextChatCompletions("a scene prompt")
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    result = prompt_service.build_text_to_image_prompt("Robe", "Robe en coton", "marché")

    assert result == "a scene prompt"
    (call,) = completions.calls
    assert call["messages"][1]["content"] == [
        {"type": "text", "text": "Product name: Robe\nProduct description: Robe en coton\nRequested scene: marché"}
    ]


def test_wonder_api_error_becomes_prompt_generation_error(monkeypatch):
    from openai import OpenAIError

    completions = _FakeTextChatCompletions(error=OpenAIError("boom"))
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))
    with pytest.raises(prompt_service.PromptGenerationError):
        prompt_service.build_text_to_image_prompt("Robe", "Robe en coton", "marché")


def test_empty_model_answer_becomes_prompt_generation_error(monkeypatch):
    completions = _FakeTextChatCompletions("   ")
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))
    with pytest.raises(prompt_service.PromptGenerationError):
        prompt_service.build_text_to_image_prompt("Robe", "Robe en coton", "marché")


class _SeqTextChatCompletions:
    """Fake returning a scripted answer sequence (empty then text)."""

    def __init__(self, contents: list):
        self.contents = list(contents)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.contents.pop(0) if self.contents else ""
        message = SimpleNamespace(content=content, refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_chat_completion_retries_once_on_empty_answer(monkeypatch, tmp_path):
    image = tmp_path / "product.jpg"
    image.write_bytes(_make_jpeg_bytes())
    completions = _SeqTextChatCompletions(["  ", "recovered prompt"])
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    result = prompt_service.build_enhanced_prompt(
        str(image), "Robe", "Robe en coton", "fond lumineux"
    )

    assert result == "recovered prompt"
    assert len(completions.calls) == 2


def test_enhanced_prompt_falls_back_when_no_transformation(tmp_path, monkeypatch):
    image = tmp_path / "product.jpg"
    image.write_bytes(_make_jpeg_bytes())
    completions = _SeqTextChatCompletions(["", ""])
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    result = prompt_service.build_enhanced_prompt(
        str(image), "Robe", "Robe en coton", ""
    )

    assert "Enhance this product photo for professional e-commerce" in result
    assert len(completions.calls) == 2


def test_enhanced_prompt_fallback_keeps_background_lock(tmp_path, monkeypatch):
    image = tmp_path / "product.jpg"
    image.write_bytes(_make_jpeg_bytes())
    completions = _SeqTextChatCompletions(["", ""])
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    result = prompt_service.build_enhanced_prompt(
        str(image), "Robe", "Robe en coton", "", True
    )

    assert "Enhance this product photo" in result
    assert "Hard constraint: keep the original background exactly as it is" in result


def test_enhanced_prompt_still_raises_with_transformation(monkeypatch, tmp_path):
    image = tmp_path / "product.jpg"
    image.write_bytes(_make_jpeg_bytes())
    completions = _SeqTextChatCompletions(["", ""])
    monkeypatch.setattr(prompt_service, "_client", _FakeTextClient(completions))

    with pytest.raises(prompt_service.PromptGenerationError):
        prompt_service.build_enhanced_prompt(
            str(image), "Robe", "Robe en coton", "fond lumineux"
        )
    assert len(completions.calls) == 2


def test_size_mapping_for_muse_image():
    assert meta_image_service._size_for_aspect_ratio("auto") is None
    assert meta_image_service._size_for_aspect_ratio("16:9") == "1600x900"
    assert meta_image_service._size_for_aspect_ratio("1:1") == "100x100"
    assert meta_image_service._size_for_aspect_ratio("9:16") == "900x1600"


def test_extract_image_url():
    result = SimpleNamespace(data=[SimpleNamespace(url="https://cdn.meta/a.png")])
    assert meta_image_service._extract_image_url(result) == "https://cdn.meta/a.png"
    with pytest.raises(meta_image_service.MetaImageApiError):
        meta_image_service._extract_image_url(SimpleNamespace(data=[]))


def test_timeout_error_mapping():
    with pytest.raises(meta_image_service.MetaImageTimeoutError):
        meta_image_service._raise_meta_error(APITimeoutError(request=_request()))


def test_content_policy_error_mapping():
    response = httpx.Response(400, request=_request())
    error = BadRequestError("content_policy_violation", response=response, body=None)
    with pytest.raises(meta_image_service.MetaImageContentPolicyError):
        meta_image_service._raise_meta_error(error)


def test_generic_api_error_mapping():
    error = APIError("boom", request=_request(), body=None)
    with pytest.raises(meta_image_service.MetaImageApiError):
        meta_image_service._raise_meta_error(error)
    conn_error = APIConnectionError(message="boom", request=_request())
    with pytest.raises(meta_image_service.MetaImageApiError):
        meta_image_service._raise_meta_error(conn_error)


def test_generate_image_calls_muse_image_edit(tmp_path, monkeypatch):
    product = tmp_path / "product.jpg"
    product.write_bytes(_make_jpeg_bytes())
    person = tmp_path / "person.jpg"
    person.write_bytes(_make_jpeg_bytes())
    http = _FakeHttp({"data": [{"url": "https://cdn.meta/test.png"}]})
    monkeypatch.setattr(meta_image_service, "_http", http)

    result = asyncio.run(
        meta_image_service.generate_image(
            [str(product), str(person)], "fond de marché", "16:9"
        )
    )

    assert result == {"image_url": "https://cdn.meta/test.png", "description": ""}
    (post,) = http.posts
    assert post["url"] == "/images/edits"
    assert post["data"]["model"] == "muse-image-1.0"
    assert post["data"]["size"] == "1600x900"
    assert post["data"]["response_format"] == "url"
    assert "marché" in post["data"]["prompt"]
    keys = [key for key, _ in post["files"]]
    assert keys == ["image[0]", "image[1]"]
    assert all(mime == "image/jpeg" for _, (_, _, mime) in post["files"])


def test_generate_image_auto_omits_size(tmp_path, monkeypatch):
    product = tmp_path / "product.jpg"
    product.write_bytes(_make_jpeg_bytes())
    http = _FakeHttp({"data": [{"url": "https://cdn.meta/test.png"}]})
    monkeypatch.setattr(meta_image_service, "_http", http)

    asyncio.run(meta_image_service.generate_image([str(product)], "fond uni", "auto"))

    (post,) = http.posts
    assert "size" not in post["data"]
    assert [key for key, _ in post["files"]] == ["image[0]"]


def test_generate_image_http_error_mapping(tmp_path, monkeypatch):
    product = tmp_path / "product.jpg"
    product.write_bytes(_make_jpeg_bytes())

    class _BoomHttp:
        async def post(self, *args, **kwargs):
            raise httpx.ConnectTimeout("down", request=_request())

    monkeypatch.setattr(meta_image_service, "_http", _BoomHttp())
    with pytest.raises(meta_image_service.MetaImageTimeoutError):
        asyncio.run(meta_image_service.generate_image([str(product)], "fond", "auto"))


def test_detect_image_mime_accepts_real_format():
    from app.routers.generate import _detect_image_mime

    assert _detect_image_mime(_make_jpeg_bytes()) == "image/jpeg"
    assert _detect_image_mime(_make_png_bytes()) == "image/png"


def test_detect_image_mime_rejects_corrupt():
    from app.routers.generate import _ImageValidationError, _detect_image_mime

    with pytest.raises(_ImageValidationError) as exc_info:
        _detect_image_mime(b"not-an-image-at-all")
    assert exc_info.value.response.status_code == 400
    with pytest.raises(_ImageValidationError):
        _detect_image_mime(b"\xff\xd8fake-truncated")


def test_encode_image_sniffs_true_format(tmp_path):
    png_as_jpg = tmp_path / "photo.jpg"
    png_as_jpg.write_bytes(_make_png_bytes())

    media_type, _ = prompt_service._encode_image(str(png_as_jpg))

    assert media_type == "image/png"


def test_extract_image_url_from_dict():
    assert (
        meta_image_service._extract_image_url({"data": [{"url": "https://x/y.png"}]})
        == "https://x/y.png"
    )
    with pytest.raises(meta_image_service.MetaImageApiError):
        meta_image_service._extract_image_url({"data": []})


def test_http_status_error_mapping():
    response = httpx.Response(400, request=_request())
    policy = httpx.HTTPStatusError("content policy violation", request=_request(), response=response)
    with pytest.raises(meta_image_service.MetaImageContentPolicyError):
        meta_image_service._raise_meta_error(policy)

    other = httpx.HTTPStatusError("bad request", request=_request(), response=response)
    with pytest.raises(meta_image_service.MetaImageApiError):
        meta_image_service._raise_meta_error(other)


def test_generate_image_from_text_calls_generations(monkeypatch):
    images = _FakeImages()
    monkeypatch.setattr(meta_image_service, "_client", _FakeImageClient(images))

    result = asyncio.run(
        meta_image_service.generate_image_from_text("une robe sur un marché", "1:1")
    )

    assert result["image_url"] == "https://cdn.meta/test.png"
    (call,) = images.generate_calls
    assert call["model"] == "muse-image-1.0"
    assert call["size"] == "100x100"
