import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.logging_conf import setup_logging
from app.mannequins import MANNEQUIN_DIR

setup_logging()
logger = logging.getLogger("reskin.main")

try:
    from app.config import settings
except ValidationError:
    logger.error(
        "FAL_KEY or ANTHROPIC_API_KEY is not set — create backend/.env from "
        "backend/.env.example and set your Fal.ai and Anthropic API keys."
    )
    raise

from app.routers.generate import router as generate_router  # noqa: E402
from app.routers.mannequins import router as mannequins_router  # noqa: E402

app = FastAPI(title="Reskin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

if MANNEQUIN_DIR.is_dir():
    app.mount("/static/mannequins", StaticFiles(directory=MANNEQUIN_DIR), name="mannequins")

app.include_router(generate_router)
app.include_router(mannequins_router)
