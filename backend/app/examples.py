"""Registre des exemples de transformations enregistrés sur disque.

Chaque sous-dossier de ``backend/exemple_transformation`` représente un exemple :
``person1*`` = photo du produit, ``person2*`` = personne de référence,
``resultat*`` = visuel final. Un fichier ``meta.json`` optionnel apporte
le titre, la catégorie, la description et le lien Alibaba.
"""

import json
import logging
import re
from pathlib import Path

from PIL import Image

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "exemple_transformation"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "exemples_web"
_META_FILENAME = "meta.json"
_ALLOWED_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_WEB_MAX_WIDTH = 1000
_WEB_QUALITY = 80

logger = logging.getLogger("reskin.examples")


def _first_with_prefix(files: list[Path], prefix: str) -> Path | None:
    matches = sorted((p for p in files if p.name.startswith(prefix)), key=lambda p: p.name)
    return matches[0] if matches else None


def _read_meta(folder: Path) -> dict:
    meta_file = folder / _META_FILENAME
    if not meta_file.is_file():
        return {}
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("meta.json illisible dans %s : %s", folder.name, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _web_version(source: Path, example_id: str) -> str:
    """Copie web allégée (JPEG) servie au lieu de l'original volumineux."""
    target_dir = CACHE_DIR / example_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{source.stem}.jpg"
    if not target.is_file() or source.stat().st_mtime > target.stat().st_mtime:
        with Image.open(source) as img:
            img = img.convert("RGB")
            if img.width > _WEB_MAX_WIDTH:
                img.thumbnail((_WEB_MAX_WIDTH, _WEB_MAX_WIDTH * 4))
            img.save(target, "JPEG", quality=_WEB_QUALITY, optimize=True)
    return f"{example_id}/{target.name}"


def list_examples() -> list[dict]:
    base = EXAMPLES_DIR
    if not base.is_dir():
        return []
    examples = []
    folders = sorted(
        (p for p in base.iterdir() if p.is_dir() and _SAFE_NAME.match(p.name)),
        key=lambda p: p.name,
    )
    for folder in folders:
        files = [
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in _ALLOWED_EXTENSIONS
        ]
        product = _first_with_prefix(files, "person1")
        reference = _first_with_prefix(files, "person2")
        result = _first_with_prefix(files, "resultat")
        if result is None:
            continue
        meta = _read_meta(folder)
        examples.append(
            {
                "id": folder.name,
                "titre": str(meta.get("titre") or folder.name),
                "categorie": str(meta.get("categorie") or ""),
                "description": str(meta.get("description") or ""),
                "lien_alibaba": str(meta.get("lien_alibaba") or ""),
                "produit": f"{folder.name}/{product.name}" if product else None,
                "produit_web": _web_version(product, folder.name) if product else None,
                "reference": f"{folder.name}/{reference.name}" if reference else None,
                "reference_web": _web_version(reference, folder.name) if reference else None,
                "resultat": f"{folder.name}/{result.name}",
                "resultat_web": _web_version(result, folder.name),
            }
        )
    return examples
