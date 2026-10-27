import base64
import logging
import os

import anthropic

from app.config import settings

logger = logging.getLogger("reskin.prompt_service")

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

_EDIT_SYSTEM_PROMPT = (
    "You write image-editing prompts for an e-commerce product photo generator. "
    "You will be given a product's name, its description, a photo of the product, and "
    "optionally the transformation the seller wants applied (new background, setting, "
    "lighting, or model/mannequin). If no transformation is given, propose one yourself: "
    "a tasteful, professional e-commerce setting that fits the product's name and "
    "description. Write a single, concrete, visually descriptive prompt for an "
    "image-editing model that clearly states what to change, while explicitly instructing "
    "that the product itself (shape, colors, logo, proportions) must stay unchanged. "
    "Output only the prompt text — no preamble, no quotes, no explanation."
)

_CLEAN_PERSON_REFERENCE_PROMPT = (
    "This photo shows a person, possibly in an unusual pose, tightly cropped, poorly lit, "
    "or with a cluttered background. Produce a clean, high-quality, full-body studio photo "
    "of this exact same person: standing in a natural, straight, relaxed pose, facing "
    "forward, fully visible from head to toe, not cropped at any edge, on a plain, clean "
    "white studio background (no props, no scenery, only a soft natural shadow beneath the "
    "subject). Reproduce the person faithfully: same face, hair, skin tone, build, outfit "
    "and clothing exactly as in the original photo — do not invent a different look. If the "
    "original photo is cropped above the feet and their footwear is not visible, complete "
    "the lower body with simple, plain shoes that match the outfit — never leave the "
    "person barefoot."
)

_REMOVE_PRESENTER_PROMPT = (
    "This photo shows a product, possibly presented by a person or mannequin, on some "
    "background. Produce a clean product-only photo on a plain, clean white studio "
    "background (no props, no scenery, only a soft natural shadow beneath the subject): "
    "remove any person, mannequin and the original background entirely. Keep the product "
    "itself exactly as it is (shape, colors, logo, material, proportions) — only the "
    "presenter and background are removed."
)

_PERSON_REPLACEMENT_PROMPT = (
    "Image 1 shows a product alone on a plain white studio background. Image 2 shows a "
    "person, shown in full. Compose a new e-commerce studio product photo, on a plain "
    "white background by default, keeping the product from Image 1 exactly as it is "
    "(shape, colors, logo, material, proportions): show the person from Image 2 "
    "presenting or wearing the product, in a natural pose suited to the product. "
    "Reproduce the person from Image 2 faithfully and completely: same face, hair, skin "
    "tone, build, outfit and clothing exactly as shown in Image 2 — do not invent a "
    "different look or change what they are wearing beyond what the product requires. "
    "Frame the photo so the person is fully visible from head to toe, not cropped at the "
    "top, bottom or sides. If their footwear is not clearly visible in Image 2, complete "
    "the lower body with simple, plain shoes that match the outfit — never leave the "
    "person barefoot."
)

_TEXT_TO_IMAGE_SYSTEM_PROMPT = (
    "You write prompts for a text-to-image model that generates photorealistic "
    "e-commerce product photography from scratch — no reference photo is available. "
    "You will be given a product's name, its description, and the scene or style the "
    "seller wants. Write a single, concrete, visually descriptive prompt that fully "
    "describes the product's appearance (inferred from its name and description) and "
    "the requested setting, lighting and composition, suitable for professional product "
    "photography. Output only the prompt text — no preamble, no quotes, no explanation."
)


class PromptGenerationError(Exception):
    """The LLM call to build an enhanced image-generation prompt failed."""


def _encode_image(image_path: str) -> tuple[str, str]:
    media_type = _MEDIA_TYPES.get(os.path.splitext(image_path)[1].lower(), "image/jpeg")
    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
    return media_type, image_b64


def _extract_text(response: anthropic.types.Message) -> str:
    text = next((block.text for block in response.content if block.type == "text"), "")
    return text.strip()


def build_person_cleanup_prompt() -> str:
    """Fixed prompt standardizing the reference person photo before compositing.

    An unusual pose, tight crop or cluttered background in the raw reference
    photo gives the person-replacement step (build_person_replacement_prompt)
    an ambiguous basis to work from, which can produce an incoherent
    combination with the product. Standardizing it first (full body, neutral
    pose, plain background) gives that step a much clearer single-face
    reference — same "smaller, localized edit" rationale as the other fixed
    prompts here.
    """
    return _CLEAN_PERSON_REFERENCE_PROMPT


def build_remove_presenter_prompt() -> str:
    """Fixed prompt isolating the product on a clean background.

    Not LLM-generated, for the same reason as the replacement prompt below.
    This is also step 1 of the person-swap pipeline: it leaves zero face
    sources in the image, so step 2's composite only ever introduces a single
    new face — see build_person_replacement_prompt for why that matters.
    """
    return _REMOVE_PRESENTER_PROMPT


def build_person_replacement_prompt() -> str:
    """Fixed, pre-optimized prompt guaranteeing the presenter swap happens.

    Not LLM-generated: the replacement is a well-defined mechanical edit, so a
    dynamically written prompt risks diluting the instruction. This step must
    always perform the person replacement, so the wording is fixed.

    Must run against a presenter-free product photo (see
    build_remove_presenter_prompt), not the original photo: Gemini 2.5 Flash
    Image (the model behind nano-banana) has documented identity-drift issues
    when a composite mixes more than one distinct face — running this against
    the original photo would mix the old presenter's face with the new one.
    """
    return _PERSON_REPLACEMENT_PROMPT


def build_enhanced_prompt(
    image_path: str,
    product_name: str,
    product_description: str,
    transformation: str,
) -> str:
    media_type, image_b64 = _encode_image(image_path)
    content: list[dict] = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": image_b64},
        }
    ]

    user_text = (
        f"Product name: {product_name}\n"
        f"Product description: {product_description}\n"
        f"Requested transformation: {transformation or '(none specified — propose one)'}\n"
        f"Image 1 = product photo (file path: {os.path.abspath(image_path)})."
    )

    content.append({"type": "text", "text": user_text})

    try:
        response = _client.messages.create(
            model=settings.prompt_model,
            max_tokens=500,
            system=_EDIT_SYSTEM_PROMPT,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.APIError as exc:
        logger.exception("Edit prompt enhancement LLM call failed")
        raise PromptGenerationError(str(exc)) from exc

    enhanced = _extract_text(response)
    if not enhanced:
        raise PromptGenerationError("Le modèle n'a renvoyé aucun prompt.")

    logger.info("Enhanced edit prompt generated (%d chars)", len(enhanced))
    return enhanced


def build_text_to_image_prompt(
    product_name: str,
    product_description: str,
    scene: str,
) -> str:
    user_text = (
        f"Product name: {product_name}\n"
        f"Product description: {product_description}\n"
        f"Requested scene: {scene}"
    )

    try:
        response = _client.messages.create(
            model=settings.prompt_model,
            max_tokens=500,
            system=_TEXT_TO_IMAGE_SYSTEM_PROMPT,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": user_text}],
        )
    except anthropic.APIError as exc:
        logger.exception("Text-to-image prompt enhancement LLM call failed")
        raise PromptGenerationError(str(exc)) from exc

    enhanced = _extract_text(response)
    if not enhanced:
        raise PromptGenerationError("Le modèle n'a renvoyé aucun prompt.")

    logger.info("Enhanced text-to-image prompt generated (%d chars)", len(enhanced))
    return enhanced
