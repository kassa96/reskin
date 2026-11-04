# Reskin — AI product-image personalization for the African market

Reskin is an AI built to personalize product images coming from marketplace
platforms like Alibaba or AliExpress: these generic visuals, designed for other
markets, are regenerated with African features and realities — African models,
local decors, atmospheres and scenes of everyday life — while faithfully
preserving the product.

Designed for e-merchants selling in Africa: they import a generic product
image, add a text prompt, and the AI regenerates the visual in an African
setting — model, decor and atmosphere — without altering the product. Built-in
gallery of examples and models, with before/after comparison and result download.

## Stack

- **Backend**: Python 3.12, **FastAPI** (`backend/`)
- **Frontend**: **Angular 20**, Tailwind CSS 4 (`frontend/`)
- **AI**: Meta Muse Image `muse-image-1.0` (edit/generation) and
  Muse Wonder `muse-wonder-1.0` (prompt enrichment), via the Meta Model API
- **Deployment**: Docker + Docker Compose (nginx serves the frontend and proxies
  the API; the backend is not publicly exposed)

## Prerequisites

- `META_API_KEY` (Meta Model API key, accepted alias: `MODEL_API_KEY`)
- For the Docker run (recommended): Docker + compose plugin
- For the dev run: [uv](https://docs.astral.sh/uv/), Node.js + npm
  (Angular CLI via `npx ng`)

## Live site

Open [http://76.13.25.132:8081/](http://76.13.25.132:8081/).

## Run with Docker (recommended)

```bash
cp backend/.env.example backend/.env   # then set META_API_KEY
docker compose up -d --build
```

Open [http://localhost:8081](http://localhost:8081).
Check: `curl http://localhost:8081/api/health` should answer `{"status":"ok"}`.

Required `backend/.env`:

```env
META_API_KEY=<your_meta_model_api_key>
CORS_ORIGINS=["http://localhost:8081"]
```

The backend refuses to start if `META_API_KEY` is missing or empty.

## Run in dev (no Docker)

Backend (terminal 1):

```bash
cd backend
uv sync   # creates .venv and installs dependencies from uv.lock
cp .env.example .env   # then set META_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2):

```bash
cd frontend
npm install   # first time only
npm start
```

Open [http://localhost:4200](http://localhost:4200).
Check the backend: [http://localhost:8000/api/health](http://localhost:8000/api/health).

## API

| Method | Route | Description |
|---|---|---|
| GET | `/api/health` | Backend health (`{"status":"ok"}`) |
| POST | `/api/generate` | Generates an image (multipart: image + prompt + model) |
| GET | `/api/exemples` | Gallery of transformation examples |
| GET | `/api/mannequins` | List of available models |

Visuals served statically: `/static/mannequins/*`, `/static/exemples/*`.

## Project structure

```text
backend/          FastAPI (app/, tests, Dockerfile)
backend/exemple_transformation/  example visuals served by the API
backend/manoquin*  model visuals served by the API
frontend/         Angular (src/, nginx.conf, Dockerfile)
deploy/           optional nginx config for an already-busy VPS
docker-compose.yml  api (internal :8000) + web (public :8081)
DEPLOIEMENT.md    VPS deployment procedure (Hostinger, in French)
```

## Deploy on a VPS

See [DEPLOIEMENT.md](/home/diallo/github/reskin/DEPLOIEMENT.md):
access via `http://VPS_IP:8081`, port to open in the firewall, `CORS_ORIGINS`
to adjust.

## Security

`META_API_KEY` always stays on the backend side (`backend/.env`, never
committed — see `.gitignore`). The frontend never calls it directly: every AI
call goes through the backend `/api/*` routes.

## Image generation process

The generate endpoint runs two modes: full creation from text when no
product photo is provided, and retouch when a product photo is provided.

Text-to-image mode (no product photo): Muse Wonder builds a photorealistic
prompt from the product name, description and requested scene, then Muse
Image generates the PNG image from that prompt.

Edit mode (with a product photo): the photo is retouched step by step.

1. Validation: product name and description are required. Only JPG, PNG and
   WEBP files are accepted, up to 10 MB, and the image format is checked.
2. Person swap (only when a reference person or mannequin is provided with
   the new-person option): the reference photo is first standardized to a
   clean full-body studio portrait, then swapped directly onto the original
   photo. Framing, pose, background and lighting stay as in the original.
   Only face, hair, skin tone and outfit change. The product itself always
   stays unchanged. If no transformation text was given, this swapped image
   is the final result.
3. Prompt enrichment: Muse Wonder receives the source photo plus the product
   name, description, requested transformation and constraints (background
   kept as is, person identity preserved). It returns a single concrete edit
   prompt that locks the product (shape, colors, logo, proportions). If the
   model stays silent, the raw transformation or a static studio prompt is
   used instead.
4. Final edit: the source image and the enriched prompt are sent to Muse
   Image with fidelity hints (product unchanged, correct hand anatomy,
   high-resolution studio finish). The API returns an image URL sent back
   in the response.
5. Cleanup: every temporary file created for the request is deleted. The
   bundled mannequin visuals are never deleted.
