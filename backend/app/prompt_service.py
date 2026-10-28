import base64
import logging
import os
from io import BytesIO

from openai import OpenAI, OpenAIError
from PIL import Image

from app.config import settings

logger = logging.getLogger("reskin.prompt_service")

# Muse Wonder est le modèle de langage Meta accessible via la Meta Model API
# (https://api.meta.ai/v1, compatible OpenAI) : analyse multimodale texte +
# image et génération de texte pour l'enrichissement des prompts.
_client = OpenAI(base_url=settings.meta_base_url, api_key=settings.meta_api_key)

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

_MEDIA_TYPES_BY_PIL_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

_EDIT_SYSTEM_PROMPT = (
    "You write image-editing prompts for an e-commerce product photo generator. "
    "You will be given a product's name, its description, a photo of the product, and "
    "optionally the transformation the seller wants applied (new background, setting, "
    "lighting, or model/mannequin). If no transformation is given, propose one yourself: "
    "a tasteful, professional e-commerce setting that fits the product's name and "
    "description. Write a single, concrete, visually descriptive prompt for an "
    "image-editing model that clearly states what to change, while explicitly instructing "
    "that the product itself (shape, colors, logo, proportions) must stay unchanged. "
    "Also keep the photo's composition and framing unchanged, and any person exactly "
    "as posed and engaged in the same action, unless the requested transformation "
    "explicitly requires otherwise. "
    "If the product appears small in the frame, first enumerate its visible "
    "micro-details (markings, text, logos, positions of hands or needles, materials, "
    "textures) and incorporate them as binding preservation constraints in the prompt, "
    "so the model reproduces them exactly instead of redrawing or simplifying them. "
    "Output only the prompt text — no preamble, no quotes, no explanation."
)

_FALLBACK_EDIT_PROMPT = (
    "Enhance this product photo for professional e-commerce: clean, bright, "
    "neutral studio presentation with soft natural lighting. Keep the product "
    "itself (shape, colors, logo, proportions) perfectly unchanged."
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

_IDENTITY_SWAP_PROMPT = (
    "Image 1 shows the original photo: a product presented by a person in a scene. "
    "Image 2 shows a different person (reference photo, neutral pose). "
    "Produce a photo IDENTICAL to Image 1 in every respect — same framing and crop, "
    "same camera angle, same composition, same pose and position of the person, same "
    "background, same lighting — with ONE single change: the person becomes the "
    "person from Image 2. "
    "Transfer from Image 2 the full appearance: face, hair, skin tone AND outfit and "
    "clothing, adapted to the exact pose, head position, angle and size in Image 1. "
    "Exception with absolute priority: the product itself stays exactly as in Image 1 "
    "in all cases — if the product is a garment worn by the person, keep that garment "
    "exactly as worn and transfer only face, hair and skin tone. "
    "Keep everything else from Image 1: the same body and posture, the same hand "
    "positions, the same action, the same background. "
    "Do not blend facial features from both images: the result must show ONE coherent "
    "person — Image 2's appearance performing Image 1's exact pose in Image 1's exact "
    "scene. "
    "Render in high resolution with sharp fine details, clean edges and a professional "
    "studio finish."
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
    with open(image_path, "rb") as f:
        raw = f.read()
    # Sniff the true format: uploads are sometimes mislabeled (e.g. a WEBP
    # served as .jpg) and the data-URL MIME must match the actual bytes.
    try:
        with Image.open(BytesIO(raw)) as img:
            img.load()
            media_type = _MEDIA_TYPES_BY_PIL_FORMAT.get((img.format or "").upper())
    except Exception:
        media_type = None
    if media_type is None:
        media_type = _MEDIA_TYPES.get(os.path.splitext(image_path)[1].lower(), "image/jpeg")
    return media_type, base64.standard_b64encode(raw).decode("utf-8")


def _data_url(media_type: str, image_b64: str) -> str:
    return f"data:{media_type};base64,{image_b64}"


def _call_once(system_prompt: str, user_content: list[dict]):
    return _client.chat.completions.create(
        model=settings.prompt_model,
        max_completion_tokens=500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )


def _log_empty_answer(response) -> None:
    try:
        first = response.choices[0]
        logger.warning(
            "Muse Wonder returned an empty answer: finish_reason=%s refusal=%r",
            getattr(first, "finish_reason", None),
            getattr(first.message, "refusal", None),
        )
    except Exception:
        logger.warning("Muse Wonder returned an empty answer (unreadable response)")


def _chat_completion(system_prompt: str, user_content: list[dict]) -> str:
    try:
        response = _call_once(system_prompt, user_content)
        text = _extract_text(response)
        if text:
            return text
        _log_empty_answer(response)
        # Retry once: transient empties do happen. A persistent empty answer
        # is handled by the caller.
        return _extract_text(_call_once(system_prompt, user_content))
    except OpenAIError as exc:
        logger.exception("Muse Wonder prompt-enhancement LLM call failed")
        raise PromptGenerationError(str(exc)) from exc


def _extract_text(response) -> str:
    message = response.choices[0].message if response.choices else None
    content = message.content if message is not None else None
    if not content:
        return ""
    if isinstance(content, str):
        return content.strip()
    parts = [item.text for item in content if getattr(item, "type", "") == "text"]
    return "".join(parts).strip()


def build_person_cleanup_prompt() -> str:
    """Fixed prompt standardizing the reference person photo before the swap.

    An unusual pose, tight crop or cluttered background in the raw reference
    photo gives the identity-swap step an ambiguous identity source, which can
    produce a blended or incoherent face. Standardizing it first (full body,
    neutral pose, plain background) gives that step one clear face to transfer.
    """
    return _CLEAN_PERSON_REFERENCE_PROMPT


def build_identity_swap_prompt() -> str:
    """Fixed prompt swapping the person directly on the original photo.

    Not LLM-generated: the swap is a well-defined mechanical edit. The single
    pass runs against the ORIGINAL photo (Image 1), so framing, crop, pose,
    action, background and lighting are preserved by construction — only the
    person changes, adopting the full appearance of the reference (Image 2):
    face, hair, skin tone and outfit. The product itself always stays exactly
    as in Image 1, which takes priority over the outfit transfer when the
    product is a worn garment.
    """
    return _IDENTITY_SWAP_PROMPT


def build_enhanced_prompt(
    image_path: str,
    product_name: str,
    product_description: str,
    transformation: str,
    keep_background: bool = False,
) -> str:
    media_type, image_b64 = _encode_image(image_path)

    user_text = (
        f"Product name: {product_name}\n"
        f"Product description: {product_description}\n"
        f"Requested transformation: {transformation or '(none specified — propose one)'}\n"
    )
    if keep_background:
        user_text += (
            "Hard constraint: keep the original background exactly as it is — "
            "same décor, colors and lighting. Do not change, restyle, recolor "
            "or add anything to it.\n"
        )

    enhanced = _chat_completion(
        _EDIT_SYSTEM_PROMPT,
        [
            {
                "type": "image_url",
                "image_url": {"url": _data_url(media_type, image_b64)},
            },
            {"type": "text", "text": user_text},
        ],
    )
    if not enhanced:
        if transformation.strip():
            # The user asked for something specific: a generic prompt would
            # silently ignore it, so fail loudly instead.
            raise PromptGenerationError("Le modèle n'a renvoyé aucun prompt.")
        logger.warning("Wonder returned no proposal — using static fallback prompt")
        enhanced = _FALLBACK_EDIT_PROMPT
        if keep_background:
            enhanced += (
                " Hard constraint: keep the original background exactly as it is — "
                "same décor, colors and lighting. Do not change, restyle, recolor "
                "or add anything to it."
            )

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

    enhanced = _chat_completion(
        _TEXT_TO_IMAGE_SYSTEM_PROMPT,
        [{"type": "text", "text": user_text}],
    )
    if not enhanced:
        raise PromptGenerationError("Le modèle n'a renvoyé aucun prompt.")

    logger.info("Enhanced text-to-image prompt generated (%d chars)", len(enhanced))
    return enhanced
