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

See [DEPLOIEMENT.md](/home/diallo/github/reskin/DEPLOIEMENT.md) (in French):
access via `http://VPS_IP:8081`, port to open in the firewall, `CORS_ORIGINS`
to adjust.

## Security

`META_API_KEY` always stays on the backend side (`backend/.env`, never
committed — see `.gitignore`). The frontend never calls it directly: every AI
call goes through the backend `/api/*` routes.
