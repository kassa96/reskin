import logging
import os
import re
import tempfile
import urllib.request
from io import BytesIO
from typing import NoReturn

import httpx
from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI
from PIL import Image

from app.config import settings

logger = logging.getLogger("reskin.meta_image")

# Muse Image (muse-image-1.0) via la Meta Model API : génération text-to-image
# (POST /v1/images/generations) et retouche multi-images
# (POST /v1/images/edits), même base URL et même clé que Muse Wonder.
_client = AsyncOpenAI(
    base_url=settings.meta_base_url,
    api_key=settings.meta_api_key,
    timeout=settings.meta_timeout_seconds,
)

# L'édition multi-images passe par httpx directement : le SDK OpenAI nomme
# les champs fichiers `image[]` alors que l'API Meta exige `image[0]`,
# `image[1]`, ... numérotés consécutivement.
_http = httpx.AsyncClient(
    base_url=settings.meta_base_url,
    headers={"Authorization": f"Bearer {settings.meta_api_key}"},
    timeout=settings.meta_timeout_seconds,
)


class MetaImageApiError(Exception):
    """Meta Model API image endpoint returned an error or unexpected response."""


class MetaImageContentPolicyError(MetaImageApiError):
    """Muse Image rejected the request (content filter)."""


class MetaImageTimeoutError(Exception):
    """Muse Image call timed out."""


ALLOWED_ASPECT_RATIOS = {
    "auto",
    "21:9",
    "16:9",
    "3:2",
    "4:3",
    "5:4",
    "1:1",
    "4:5",
    "3:4",
    "2:3",
    "9:16",
}

_CONTENT_POLICY_RE = re.compile(
    r"content[\s_\-]?policy|policy[\s_\-]?violation|content[\s_\-]?filter|safety|blocked",
    re.IGNORECASE,
)

_MIME_BY_PIL_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
_MIME_BY_EXTENSION = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _size_for_aspect_ratio(aspect_ratio: str) -> str | None:
    """Map our "W:H" ratio to the "WxH" size string Muse Image expects.

    The size only sets the aspect ratio, not exact pixels, so any WxH with
    the right proportions works. "auto" means omitting the argument and
    letting the model choose the dimensions.
    """
    if aspect_ratio == "auto":
        return None
    width, _, height = aspect_ratio.partition(":")
    return f"{int(width) * 100}x{int(height) * 100}"


def _guess_mime(path: str, content: bytes) -> str:
    """Best-effort MIME type for an upload: sniffed bytes, else extension."""
    try:
        with Image.open(BytesIO(content)) as img:
            img.load()
            mime = _MIME_BY_PIL_FORMAT.get((img.format or "").upper())
            if mime:
                return mime
    except Exception:
        pass
    return _MIME_BY_EXTENSION.get(os.path.splitext(path)[1].lower().lstrip("."), "image/png")


def download_image(url: str) -> str:
    """Download a Muse Image result image to a local temp file and return its path."""
    with urllib.request.urlopen(url) as response:
        data = response.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(data)
        return tmp.name


_HAND_ANATOMY_HINT = (
    "If a person appears in the photo, render their hands and fingers with correct, "
    "natural anatomy: exactly five fingers per hand, no extra, missing, fused or "
    "malformed fingers."
)

_QUALITY_HINT = (
    "Render in high resolution with sharp fine details, clean edges, accurate "
    "colors and a professional studio finish."
)

_DETAIL_FIDELITY_HINT = (
    "If the product is small in the frame, reproduce its exact details with maximum "
    "fidelity — do not redraw, simplify, stylize, move or resize it; keep logos, "
    "text, positions of hands or needles, and textures pixel-faithful."
)


def build_prompt(user_prompt: str) -> str:
    return (
        f"{user_prompt.strip()}. "
        "Keep the product itself (shape, colors, logo, proportions) perfectly "
        "unchanged; only modify the background, setting, lighting or "
        f"model/mannequin as described. {_HAND_ANATOMY_HINT} {_QUALITY_HINT} "
        f"{_DETAIL_FIDELITY_HINT}"
    )


def _extract_image_url(result) -> str:
    if isinstance(result, dict):
        data = result.get("data") or []
        url = data[0].get("url") if data else None
    else:
        data = getattr(result, "data", None) or []
        url = data[0].url if data else None
    if not url:
        logger.error("Muse Image response contained no image URL: %s", result)
        raise MetaImageApiError("Muse Image response contained no image")
    return url


def _raise_meta_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (APITimeoutError, httpx.TimeoutException)):
        logger.exception("Muse Image call timed out")
        raise MetaImageTimeoutError("Muse Image call timed out") from exc
    message = str(exc)
    if isinstance(exc, (APIError, httpx.HTTPStatusError)) and _CONTENT_POLICY_RE.search(message):
        raise MetaImageContentPolicyError(message) from exc
    if isinstance(exc, (APIError, APIConnectionError, httpx.HTTPError)):
        logger.exception("Muse Image call failed")
        raise MetaImageApiError(message) from exc
    logger.exception("Muse Image call failed")
    raise MetaImageApiError(message) from exc


async def generate_image(image_paths: list[str], prompt: str, aspect_ratio: str = "auto") -> dict:
    enhanced_prompt = build_prompt(prompt)
    files = []
    for index, path in enumerate(image_paths):
        with open(path, "rb") as f:
            content = f.read()
        filename = os.path.basename(path) or f"image-{index}.png"
        files.append((f"image[{index}]", (filename, content, _guess_mime(path, content))))
    data: dict = {
        "model": settings.image_model,
        "prompt": enhanced_prompt,
        "n": "1",
        "response_format": "url",
        "output_format": "png",
    }
    if (size := _size_for_aspect_ratio(aspect_ratio)) is not None:
        data["size"] = size
    try:
        response = await _http.post("/images/edits", data=data, files=files)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        _raise_meta_error(exc)

    return {"image_url": _extract_image_url(payload), "description": ""}


async def generate_image_from_text(prompt: str, aspect_ratio: str = "auto") -> dict:
    enhanced_prompt = f"{prompt.strip()}. {_HAND_ANATOMY_HINT} {_QUALITY_HINT} {_DETAIL_FIDELITY_HINT}"
    kwargs: dict = {
        "model": settings.image_model,
        "prompt": enhanced_prompt,
        "n": 1,
        "response_format": "url",
        "output_format": "png",
    }
    if (size := _size_for_aspect_ratio(aspect_ratio)) is not None:
        kwargs["size"] = size
    try:
        result = await _client.images.generate(**kwargs)
    except Exception as exc:
        _raise_meta_error(exc)

    return {"image_url": _extract_image_url(result), "description": ""}
