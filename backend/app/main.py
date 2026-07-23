import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.logging_conf import setup_logging

setup_logging()
logger = logging.getLogger("reskin.main")

try:
    from app.config import settings
except ValidationError:
    logger.error(
        "FAL_KEY is not set — create backend/.env from backend/.env.example "
        "and set your Fal.ai API key."
    )
    raise

from app.routers.generate import router as generate_router  # noqa: E402

app = FastAPI(title="Reskin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(generate_router)
