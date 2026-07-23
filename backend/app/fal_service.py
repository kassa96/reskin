import asyncio
import logging

import fal_client

from app.config import settings

logger = logging.getLogger("reskin.fal_service")

_client = fal_client.AsyncClient(key=settings.fal_key)


class FalApiError(Exception):
    """Fal.ai returned an error or an unexpected response."""


class FalTimeoutError(Exception):
    """Fal.ai call exceeded the configured timeout."""


def build_prompt(user_prompt: str) -> str:
    return (
        f"{user_prompt.strip()}. "
        "Keep the product itself (shape, colors, logo, proportions) perfectly "
        "unchanged; only modify the background, setting, lighting or "
        "model/mannequin as described."
    )


async def generate_image(image_path: str, prompt: str) -> dict:
    enhanced_prompt = build_prompt(prompt)
    try:
        image_url = await asyncio.wait_for(
            _client.upload_file(image_path),
            timeout=settings.fal_timeout_seconds,
        )
        logger.info("Image uploaded to Fal CDN")

        result = await asyncio.wait_for(
            _client.subscribe(
                settings.fal_model,
                arguments={
                    "prompt": enhanced_prompt,
                    "image_urls": [image_url],
                    "num_images": 1,
                    "output_format": "png",
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
        raise FalApiError(str(exc)) from exc

    images = result.get("images") or []
    if not images:
        logger.error("Fal.ai response contained no images: %s", result)
        raise FalApiError("Fal.ai response contained no images")

    return {
        "image_url": images[0]["url"],
        "description": result.get("description", ""),
    }
