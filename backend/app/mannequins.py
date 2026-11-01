import re
from pathlib import Path

MANNEQUIN_DIR = Path(__file__).resolve().parent.parent / "manoquin"
STUDIO_DIR = Path(__file__).resolve().parent.parent / "manoquin_studio"
_ALLOWED_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}
_STUDIO_SUFFIX = "_studio"

_CATEGORY_LABELS = {
    "femme_noire": "Woman (dark skin)",
    "femme_blanche": "Woman (light skin)",
    "homme_noir": "Man (dark skin)",
    "homme_blanc": "Man (light skin)",
}


def _label_for(stem: str) -> str:
    match = re.match(r"^([a-z]+_[a-z]+)_(\d+)$", stem)
    if not match:
        return stem
    category, index = match.groups()
    return f"{_CATEGORY_LABELS.get(category, category.replace('_', ' ').capitalize())} {index}"


def active_mannequin_dir() -> Path:
    """Dossier servi : les visuels studio s'ils existent, sinon les originaux."""
    if STUDIO_DIR.is_dir() and any(
        p.suffix.lower() in _ALLOWED_EXTENSIONS for p in STUDIO_DIR.iterdir()
    ):
        return STUDIO_DIR
    return MANNEQUIN_DIR


def _base_id(stem: str) -> str:
    """Retire le suffixe _studio pour garder des ids stables (ex: femme1)."""
    if stem.endswith(_STUDIO_SUFFIX):
        return stem[: -len(_STUDIO_SUFFIX)]
    return stem


def list_mannequins() -> list[dict[str, str]]:
    base = active_mannequin_dir()
    if not base.is_dir():
        return []
    files = sorted(p for p in base.iterdir() if p.suffix.lower() in _ALLOWED_EXTENSIONS)
    return [
        {"id": _base_id(p.stem), "filename": p.name, "label": _label_for(_base_id(p.stem))}
        for p in files
    ]


def get_mannequin_path(mannequin_id: str) -> Path | None:
    base = active_mannequin_dir()
    for item in list_mannequins():
        if item["id"] == mannequin_id:
            return base / item["filename"]
    return None
