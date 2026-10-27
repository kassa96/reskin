import re
from pathlib import Path

MANNEQUIN_DIR = Path(__file__).resolve().parent.parent / "manoquin"
_ALLOWED_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}

_CATEGORY_LABELS = {
    "femme_noire": "Femme (peau noire)",
    "femme_blanche": "Femme (peau claire)",
    "homme_noir": "Homme (peau noire)",
    "homme_blanc": "Homme (peau claire)",
}


def _label_for(stem: str) -> str:
    match = re.match(r"^([a-z]+_[a-z]+)_(\d+)$", stem)
    if not match:
        return stem
    category, index = match.groups()
    return f"{_CATEGORY_LABELS.get(category, category.replace('_', ' ').capitalize())} {index}"


def list_mannequins() -> list[dict[str, str]]:
    if not MANNEQUIN_DIR.is_dir():
        return []
    files = sorted(p for p in MANNEQUIN_DIR.iterdir() if p.suffix.lower() in _ALLOWED_EXTENSIONS)
    return [{"id": p.stem, "filename": p.name, "label": _label_for(p.stem)} for p in files]


def get_mannequin_path(mannequin_id: str) -> Path | None:
    for item in list_mannequins():
        if item["id"] == mannequin_id:
            return MANNEQUIN_DIR / item["filename"]
    return None
