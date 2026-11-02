FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# curl = nécessaire au HEALTHCHECK (docker compose)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances seules d'abord = meilleur cache de build
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.139.2" \
    "uvicorn[standard]>=0.51.0" \
    "httpx>=0.28.1" \
    "pillow>=11.0.0" \
    "pydantic-settings>=2.14.2" \
    "python-multipart>=0.0.32" \
    "openai>=1.0.0"

# Code + assets servis en /static (mannequins, exemples)
COPY app ./app
COPY exemple_transformation ./exemple_transformation
COPY manoquin ./manoquin
COPY manoquin_studio ./manoquin_studio

# Cache des visuels web redimensionnés (persisté via volume)
VOLUME ["/code/.cache"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
