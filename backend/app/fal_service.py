import asyncio
import logging
import tempfile
import urllib.request

import fal_client

from app.config import settings

logger = logging.getLogger("reskin.fal_service")

_client = fal_client.AsyncClient(key=settings.fal_key)


class FalApiError(Exception):
    """Fal.ai returned an error or an unexpected response."""


class FalContentPolicyError(FalApiError):
    """Fal.ai rejected the request because it was flagged by its content checker."""


class FalTimeoutError(Exception):
    """Fal.ai call exceeded the configured timeout."""


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


def _raise_fal_error(exc: fal_client.FalClientError) -> None:
    if isinstance(exc, fal_client.FalClientHTTPError) and "content_policy_violation" in str(exc):
        raise FalContentPolicyError(str(exc)) from exc
    raise FalApiError(str(exc)) from exc


def download_image(url: str) -> str:
    """Download a Fal.ai result image to a local temp file and return its path."""
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


def build_prompt(user_prompt: str) -> str:
    return (
        f"{user_prompt.strip()}. "
        "Keep the product itself (shape, colors, logo, proportions) perfectly "
        "unchanged; only modify the background, setting, lighting or "
        f"model/mannequin as described. {_HAND_ANATOMY_HINT}"
    )


async def generate_image(image_paths: list[str], prompt: str, aspect_ratio: str = "auto") -> dict:
    enhanced_prompt = build_prompt(prompt)
    print("-----")
    print(enhanced_prompt)
    print("-----")
    try:
        image_urls = await asyncio.wait_for(
            asyncio.gather(*(_client.upload_file(path) for path in image_paths)),
            timeout=settings.fal_timeout_seconds,
        )
        logger.info("%d image(s) uploaded to Fal CDN", len(image_urls))

        result = await asyncio.wait_for(
            _client.subscribe(
                settings.fal_model,
                arguments={
                    "prompt": enhanced_prompt,
                    "image_urls": image_urls,
                    "num_images": 1,
                    "output_format": "png",
                    "aspect_ratio": aspect_ratio,
                },
                with_logs=True,
            ),
            timeout=settings.fal_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        logger.exception("Fal.ai call timed out")
        raise FalTimeoutError("Fal.ai call timed out") from exc
    except fal_client.FalClientError as exc:
        logger.exception("Fal.ai call failed")
        _raise_fal_error(exc)

    images = result.get("images") or []
    if not images:
        logger.error("Fal.ai response contained no images: %s", result)
        raise FalApiError("Fal.ai response contained no images")

    return {
        "image_url": images[0]["url"],
        "description": result.get("description", ""),
    }


async def generate_image_from_text(prompt: str, aspect_ratio: str = "auto") -> dict:
    enhanced_prompt = f"{prompt.strip()}. {_HAND_ANATOMY_HINT}"
    try:
        result = await asyncio.wait_for(
            _client.subscribe(
                settings.fal_text_to_image_model,
                arguments={
                    "prompt": enhanced_prompt,
                    "num_images": 1,
                    "output_format": "png",
                    "aspect_ratio": aspect_ratio,
                },
                with_logs=True,
            ),
            timeout=settings.fal_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        logger.exception("Fal.ai text-to-image call timed out")
        raise FalTimeoutError("Fal.ai call timed out") from exc
    except fal_client.FalClientError as exc:
        logger.exception("Fal.ai text-to-image call failed")
        _raise_fal_error(exc)

    images = result.get("images") or []
    if not images:
        logger.error("Fal.ai response contained no images: %s", result)
        raise FalApiError("Fal.ai response contained no images")

    return {
        "image_url": images[0]["url"],
        "description": result.get("description", ""),
    }
