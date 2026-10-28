import asyncio
import logging
import os
import tempfile
import time
from io import BytesIO
from typing import Awaitable

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from app.config import settings
from app.meta_image_service import (
    ALLOWED_ASPECT_RATIOS,
    MetaImageApiError,
    MetaImageContentPolicyError,
    MetaImageTimeoutError,
    download_image,
    generate_image,
    generate_image_from_text,
)
from app.mannequins import get_mannequin_path
from app.prompt_service import (
    PromptGenerationError,
    build_enhanced_prompt,
    build_identity_swap_prompt,
    build_person_cleanup_prompt,
    build_text_to_image_prompt,
)
from app.schemas import ErrorResponse, GenerateResponse

logger = logging.getLogger("reskin.generate")

router = APIRouter(prefix="/api", tags=["generate"])


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=code, message=message).model_dump(),
    )


class _ImageValidationError(Exception):
    def __init__(self, response: JSONResponse):
        self.response = response


_MIME_BY_PIL_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def _detect_image_mime(contents: bytes) -> str:
    """Return the true MIME type after fully decoding the image.

    Sniffs the actual bytes (not the extension) and rejects corrupt,
    truncated or undecodable files with a clear 400 instead of a 502 from
    the provider.
    """
    try:
        with Image.open(BytesIO(contents)) as img:
            img.load()
            mime = _MIME_BY_PIL_FORMAT.get((img.format or "").upper())
    except Exception:
        mime = None
    if mime is None or mime not in settings.allowed_mime_types:
        raise _ImageValidationError(
            _error(
                400,
                "unreadable_image",
                "L'image semble corrompue, tronquée ou illisible. "
                "Envoyez un fichier JPG, PNG ou WEBP valide.",
            )
        )
    return mime


async def _read_and_validate_image(image: UploadFile) -> bytes:
    if image.content_type not in settings.allowed_mime_types:
        raise _ImageValidationError(
            _error(400, "unsupported_format", "Le fichier doit être au format JPG, PNG ou WEBP.")
        )

    contents = await image.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise _ImageValidationError(
            _error(
                413,
                "file_too_large",
                f"L'image dépasse la taille maximale autorisée ({settings.max_upload_mb} Mo).",
            )
        )
    _detect_image_mime(contents)
    return contents


def _save_temp_image(contents: bytes, filename: str | None) -> str:
    suffix = os.path.splitext(filename or "")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        return tmp.name


async def _timed(coro: Awaitable[dict], log_msg: str) -> dict:
    start = time.monotonic()
    result = await coro
    logger.info(log_msg, time.monotonic() - start)
    return result


async def _generate_edit_result(
    tmp_path: str,
    person_tmp_path: str | None,
    product_name: str,
    product_description: str,
    prompt_value: str,
    aspect_ratio: str,
    keep_background: bool = False,
    appearance_source: str = "reference",
) -> tuple[dict, list[str]]:
    """Runs the edit pipeline; returns (result, intermediate_tmp_paths_to_clean_up).

    The person swap ("reference" appearance) is a single transfer pass
    directly on the ORIGINAL photo: framing, crop, pose, action, background
    and lighting are preserved by construction — only the person changes,
    adopting the reference's appearance (face, hair, skin tone, outfit).
    One pass means no recomposition step can reinvent the layout, and fewer
    generative passes means less drift overall. With the "original" appearance
    the swap is skipped entirely and the original presenter is kept.
    """
    source_path = tmp_path
    intermediate_paths: list[str] = []

    if person_tmp_path and appearance_source == "original":
        logger.info("Appearance source is the original person — skipping the swap")

    if person_tmp_path and appearance_source == "reference":
        # Step 0: standardize the reference person photo first. An unusual
        # pose, tight crop or cluttered background in the raw reference gives
        # the swap an ambiguous identity source — cleaning it up first (full
        # body, neutral pose, plain background) fixes that. Aspect ratio is
        # fixed to "auto" here since this is only an internal reference image,
        # not part of the final output.
        clean_person_result = await _timed(
            generate_image([person_tmp_path], build_person_cleanup_prompt(), "auto"),
            "Muse Image person-reference cleanup call succeeded in %.2fs",
        )
        clean_person_path = await asyncio.to_thread(
            download_image, clean_person_result["image_url"]
        )
        intermediate_paths.append(clean_person_path)

        # Step 1: swap the identity directly on the original photo. Everything
        # stays pixel-faithful by construction (same base image, aspect "auto"
        # so no reframing is requested); only face/hair/skin become Image 2's.
        # Clothing, pose, background and product are explicitly kept.
        swap_result = await _timed(
            generate_image(
                [tmp_path, clean_person_path],
                build_identity_swap_prompt(),
                "auto",
            ),
            "Muse Image identity-swap call succeeded in %.2fs",
        )
        source_path = await asyncio.to_thread(download_image, swap_result["image_url"])
        intermediate_paths.append(source_path)

        if not prompt_value:
            # The swapped image is already the desired final result — no
            # transformation was requested, so a further edit pass would only
            # risk drifting away from it.
            logger.info("No transformation requested — using identity-swap result as-is")
            return swap_result, intermediate_paths

    # Step 2 (or the only step, without a person swap): apply the user's own
    # prompt as a single-image edit. The reference photo is deliberately not
    # reintroduced here — the identity is already baked into source_path.
    enhanced_prompt = await asyncio.to_thread(
        build_enhanced_prompt,
        source_path,
        product_name,
        product_description,
        prompt_value,
        keep_background,
    )
    logger.info(
        "Enhanced edit prompt built from product info + image%s",
        " + replaced presenter" if person_tmp_path else "",
    )
    result = await _timed(
        generate_image([source_path], enhanced_prompt, aspect_ratio),
        "Muse Image edit call succeeded in %.2fs",
    )
    return result, intermediate_paths


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    image: UploadFile | None = File(None),
    person_image: UploadFile | None = File(None),
    prompt: str = Form(""),
    product_name: str = Form(...),
    product_description: str = Form(...),
    aspect_ratio: str = Form("auto"),
    mannequin_id: str = Form(""),
    keep_background: bool = Form(False),
    appearance_source: str = Form("reference"),
):
    if not product_name or not product_name.strip():
        return _error(
            400,
            "empty_product_name",
            "Merci de renseigner le nom du produit.",
        )

    if not product_description or not product_description.strip():
        return _error(
            400,
            "empty_product_description",
            "Merci de renseigner la description du produit.",
        )

    if aspect_ratio not in ALLOWED_ASPECT_RATIOS:
        return _error(
            400,
            "invalid_aspect_ratio",
            "Format d'image invalide.",
        )

    if appearance_source not in ("reference", "original"):
        return _error(
            400,
            "invalid_appearance_source",
            "Choix d'apparence invalide.",
        )

    has_image = image is not None and bool(image.filename)
    has_uploaded_person_image = person_image is not None and bool(person_image.filename)
    mannequin_id_value = (mannequin_id or "").strip()
    prompt_value = (prompt or "").strip()

    # An explicitly uploaded person photo takes precedence over a preset
    # mannequin — the mannequin is only a default fallback.
    mannequin_path = None
    if mannequin_id_value and not has_uploaded_person_image:
        mannequin_path = get_mannequin_path(mannequin_id_value)
        if mannequin_path is None:
            return _error(400, "mannequin_not_found", "Le mannequin sélectionné est introuvable.")

    has_person_image = has_uploaded_person_image or mannequin_path is not None

    if not has_image and not prompt_value:
        return _error(
            400,
            "empty_input",
            "Ajoutez une image, décrivez l'image à générer, ou les deux.",
        )

    if has_person_image and not has_image:
        return _error(
            400,
            "person_image_without_product_image",
            "Ajoutez d'abord une photo du produit pour pouvoir y remplacer la personne.",
        )

    if has_person_image and appearance_source == "original" and not prompt_value:
        return _error(
            400,
            "nothing_to_do",
            "Rien à transformer : décrivez la retouche souhaitée ou choisissez "
            "la nouvelle personne pour l'apparence.",
        )

    contents = b""
    if has_image:
        try:
            contents = await _read_and_validate_image(image)
        except _ImageValidationError as exc:
            return exc.response

    person_contents = b""
    if has_uploaded_person_image:
        try:
            person_contents = await _read_and_validate_image(person_image)
        except _ImageValidationError as exc:
            return exc.response

    tmp_paths: list[str] = []
    try:
        if has_image:
            tmp_path = _save_temp_image(contents, image.filename)
            tmp_paths.append(tmp_path)

            person_tmp_path = None
            if has_uploaded_person_image:
                person_tmp_path = _save_temp_image(person_contents, person_image.filename)
                tmp_paths.append(person_tmp_path)
            elif mannequin_path is not None:
                # Not added to tmp_paths: this is a persistent bundled asset,
                # not a per-request temp file — it must not be deleted.
                person_tmp_path = str(mannequin_path)

            logger.info(
                "generate request received: mode=edit filename=%s size=%d prompt_len=%d person_ref=%s",
                image.filename,
                len(contents),
                len(prompt_value),
                has_person_image,
            )

            result, intermediate_paths = await _generate_edit_result(
                tmp_path,
                person_tmp_path,
                product_name,
                product_description,
                prompt_value,
                aspect_ratio,
                keep_background,
                appearance_source,
            )
            tmp_paths.extend(intermediate_paths)
        else:
            logger.info(
                "generate request received: mode=text-to-image prompt_len=%d",
                len(prompt_value),
            )

            enhanced_prompt = await asyncio.to_thread(
                build_text_to_image_prompt, product_name, product_description, prompt_value
            )
            logger.info("Enhanced text-to-image prompt built from product info + prompt")

            result = await _timed(
                generate_image_from_text(enhanced_prompt, aspect_ratio),
                "Muse Image text-to-image call succeeded in %.2fs",
            )

        return GenerateResponse(image_url=result["image_url"], description=result["description"])

    except PromptGenerationError:
        logger.warning("Prompt generation failed — returning 502", exc_info=True)
        return _error(
            502,
            "prompt_generation_error",
            "Impossible de générer le prompt à partir des informations produit. Réessayez.",
        )
    except MetaImageTimeoutError:
        return _error(
            504,
            "meta_timeout",
            "Le service de génération met trop de temps à répondre. Réessayez.",
        )
    except MetaImageContentPolicyError:
        return _error(
            422,
            "content_policy_violation",
            "Cette combinaison de photos a été bloquée par le filtre de contenu du service "
            "de génération. Essayez avec d'autres photos.",
        )
    except MetaImageApiError:
        return _error(
            502,
            "meta_api_error",
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
        for path in tmp_paths:
            if path and os.path.exists(path):
                os.remove(path)
