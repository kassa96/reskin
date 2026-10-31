"""Retouche par lot des photos du dossier manoquin.

Pour chaque image : conserve exactement la même personne (traits, coiffure,
carnation, tenue) et la même posture/cadrage, mais remplace le fond par un
studio photo professionnel et monte la qualité au maximum via Muse Image.

Usage :
    cd backend
    .venv/bin/python scripts/retouch_mannequins.py [--out manoquin_studio] [--limit 2] [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reskin.retouch_mannequins")

_ALLOWED_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}

_STUDIO_PROMPT = (
    "Transform this photo into a premium professional e-commerce studio portrait. "
    "The person must be the exact same individual — identical face, facial "
    "features, hairstyle, hair color and skin tone — with a clear, well-lit, "
    "fully visible face turned toward the camera, sharp and in focus. "
    "Pose the person standing perfectly upright in an elegant, confident, "
    "well-composed posture, full body framing from head to feet, both feet "
    "visible on the ground. "
    "Keep the person's original outfit exactly as it is — same garments, style "
    "and colors. "
    "The person wears elegant shoes that fit their feet well and match the "
    "outfit — clean, studio-appropriate footwear, never barefoot. "
    "Replace the background with a clean, high-end light-gray seamless studio "
    "backdrop with a soft vertical gradient and a gentle floor shadow under the "
    "subject, even flattering studio softbox lighting, no props, no scenery, no text. "
    "Render in ultra high resolution with tack-sharp fine details, clean edges, "
    "accurate skin tones and colors, and a flawless professional studio finish."
)


async def _retouch_one(src: Path, dst: Path, aspect_ratio: str) -> None:
    from app.meta_image_service import download_image, generate_image

    result = await generate_image([str(src)], _STUDIO_PROMPT, aspect_ratio)
    tmp_path = await asyncio.to_thread(download_image, result["image_url"])
    try:
        shutil.move(tmp_path, dst)
        dst.chmod(0o644)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _run(src_dir: Path, out_dir: Path, limit: int | None, force: bool) -> dict:
    from app.meta_image_service import (
        MetaImageApiError,
        MetaImageContentPolicyError,
        MetaImageTimeoutError,
    )

    images = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in _ALLOWED_EXTENSIONS)
    if limit is not None:
        images = images[:limit]
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = {"ok": 0, "skipped": 0, "failed": 0}
    for index, src in enumerate(images, start=1):
        dst = out_dir / f"{src.stem}_studio.png"
        if dst.exists() and not force:
            logger.info("[%d/%d] %s déjà traité — ignoré", index, len(images), src.name)
            stats["skipped"] += 1
            continue
        try:
            logger.info("[%d/%d] Retouche de %s ...", index, len(images), src.name)
            await _retouch_one(src, dst, "auto")
            logger.info("[%d/%d] OK -> %s", index, len(images), dst.name)
            stats["ok"] += 1
        except MetaImageContentPolicyError as exc:
            logger.warning("[%d/%d] %s bloqué par le filtre de contenu : %s", index, len(images), src.name, exc)
            stats["failed"] += 1
        except MetaImageTimeoutError:
            logger.warning("[%d/%d] %s : délai dépassé, relancez avec --force", index, len(images), src.name)
            stats["failed"] += 1
        except MetaImageApiError as exc:
            logger.warning("[%d/%d] %s : erreur API (%s)", index, len(images), src.name, exc)
            stats["failed"] += 1
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retouche studio par lot du dossier manoquin.")
    parser.add_argument("--src", default=None, help="Dossier source (défaut : backend/manoquin).")
    parser.add_argument("--out", default=None, help="Dossier de sortie (défaut : backend/manoquin_studio).")
    parser.add_argument("--limit", type=int, default=None, help="Ne traiter que les N premières images.")
    parser.add_argument("--force", action="store_true", help="Retraiter même les images déjà sorties.")
    args = parser.parse_args(argv)

    backend_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(backend_dir))
    # Les réglages (app/config.py) lisent backend/.env relatif au dossier
    # courant : on s'y place pour que le script marche depuis n'importe où.
    os.chdir(backend_dir)
    from app.mannequins import MANNEQUIN_DIR

    src_dir = Path(args.src) if args.src else MANNEQUIN_DIR
    out_dir = Path(args.out) if args.out else backend_dir / "manoquin_studio"
    if not src_dir.is_dir():
        logger.error("Dossier source introuvable : %s", src_dir)
        return 1

    stats = asyncio.run(_run(src_dir, out_dir, args.limit, args.force))
    logger.info(
        "Terminé : %d réussies, %d ignorées (déjà faites), %d en échec. Sortie : %s",
        stats["ok"], stats["skipped"], stats["failed"], out_dir,
    )
    return 0 if stats["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
