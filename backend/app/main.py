import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.logging_conf import setup_logging
from app.examples import CACHE_DIR, EXAMPLES_DIR
from app.mannequins import active_mannequin_dir

setup_logging()
logger = logging.getLogger("reskin.main")

try:
    from app.config import settings
except ValidationError:
    logger.error(
        "META_API_KEY is not set — create backend/.env from "
        "backend/.env.example and set your Meta Model API key."
    )
    raise

from app.routers.examples import router as examples_router  # noqa: E402
from app.routers.generate import router as generate_router  # noqa: E402
from app.routers.mannequins import router as mannequins_router  # noqa: E402

app = FastAPI(title="Reskin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_mannequin_static_dir = active_mannequin_dir()
if _mannequin_static_dir.is_dir():
    app.mount(
        "/static/mannequins",
        StaticFiles(directory=_mannequin_static_dir),
        name="mannequins",
    )

if EXAMPLES_DIR.is_dir():
    app.mount(
        "/static/exemples-src",
        StaticFiles(directory=EXAMPLES_DIR),
        name="exemples-src",
    )
CACHE_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/static/exemples",
    StaticFiles(directory=CACHE_DIR),
    name="exemples",
)

app.include_router(examples_router)
app.include_router(generate_router)
app.include_router(mannequins_router)
