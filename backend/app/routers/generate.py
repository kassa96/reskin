import logging
import os
import tempfile
import time

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.fal_service import FalApiError, FalTimeoutError, generate_image
from app.schemas import ErrorResponse, GenerateResponse

logger = logging.getLogger("reskin.generate")

router = APIRouter(prefix="/api", tags=["generate"])


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=code, message=message).model_dump(),
    )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    image: UploadFile = File(...),
    prompt: str = Form(...),
):
    if image.content_type not in settings.allowed_mime_types:
        return _error(
            400,
            "unsupported_format",
            "Le fichier doit être au format JPG, PNG ou WEBP.",
        )

    if not prompt or not prompt.strip():
        return _error(
            400,
            "empty_prompt",
            "Merci de décrire la transformation souhaitée.",
        )

    contents = await image.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        return _error(
            413,
            "file_too_large",
            f"L'image dépasse la taille maximale autorisée ({settings.max_upload_mb} Mo).",
        )

    suffix = os.path.splitext(image.filename or "")[1] or ".jpg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        logger.info(
            "generate request received: filename=%s size=%d prompt_len=%d",
            image.filename,
            len(contents),
            len(prompt),
        )

        start = time.monotonic()
        result = await generate_image(tmp_path, prompt)
        duration = time.monotonic() - start
        logger.info("Fal.ai call succeeded in %.2fs", duration)

        return GenerateResponse(image_url=result["image_url"], description=result["description"])

    except FalTimeoutError:
        return _error(
            504,
            "fal_timeout",
            "Le service de génération met trop de temps à répondre. Réessayez.",
        )
    except FalApiError:
        return _error(
            502,
            "fal_api_error",
            "Le service de génération d'image a rencontré une erreur. Réessayez.",
        )
    except Exception:
        logger.exception("Unexpected error during image generation")
        return _error(
            500,
            "internal_error",
            "Une erreur inattendue est survenue. Réessayez.",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
