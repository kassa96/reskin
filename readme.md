# Reskin — Personnalisation d'image produit

SaaS pour e-commerçants : l'utilisateur upload une image produit + un prompt
texte, l'application génère une nouvelle image adaptée (décor, mannequin,
ambiance) tout en préservant le produit. Galerie d'exemples et de mannequins
incluse, avec affichage avant/après et téléchargement du résultat.

## Stack

- **Backend** : Python 3.12, **FastAPI** (`backend/`)
- **Frontend** : **Angular 20**, Tailwind CSS 4 (`frontend/`)
- **IA** : Meta Muse Image `muse-image-1.0` (retouche/génération) et
  Muse Wonder `muse-wonder-1.0` (enrichissement du prompt), via la Meta Model API
- **Déploiement** : Docker + Docker Compose (nginx sert le frontend et proxie
  l'API, le backend n'est pas exposé publiquement)

## Prérequis

- `META_API_KEY` (clé Meta Model API, alias accepté : `MODEL_API_KEY`)
- Pour le lancement Docker (recommandé) : Docker + plugin compose
- Pour le lancement dev : [uv](https://docs.astral.sh/uv/), Node.js + npm
  (Angular CLI via `npx ng`)

## Lancement avec Docker (recommandé)

```bash
cp backend/.env.example backend/.env   # puis renseigner META_API_KEY
docker compose up -d --build
```

Ouvrir [http://localhost:8081](http://localhost:8081).
Vérifier : `curl http://localhost:8081/api/health` doit répondre `{"status":"ok"}`.

`backend/.env` requis :

```env
META_API_KEY=<votre_clé_meta_model_api>
CORS_ORIGINS=["http://localhost:8081"]
```

Le backend refuse de démarrer si `META_API_KEY` est absente ou vide.

## Lancement en dev (sans Docker)

Backend (terminal 1) :

```bash
cd backend
cp .env.example .env   # puis renseigner META_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2) :

```bash
cd frontend
npm install   # uniquement la première fois
npm start
```

Ouvrir [http://localhost:4200](http://localhost:4200).
Vérifier le backend : [http://localhost:8000/api/health](http://localhost:8000/api/health).

## API

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/health` | Santé du backend (`{"status":"ok"}`) |
| POST | `/api/generate` | Génère une image (multipart : image + prompt + mannequin) |
| GET | `/api/exemples` | Galerie d'exemples de transformations |
| GET | `/api/mannequins` | Liste des mannequins disponibles |

Visuels servis en statique : `/static/mannequins/*`, `/static/exemples/*`.

## Structure du projet

```text
backend/          FastAPI (app/, tests, Dockerfile)
backend/exemple_transformation/  visuels d'exemples servis par l'API
backend/manoquin*  visuels de mannequins servis par l'API
frontend/         Angular (src/, nginx.conf, Dockerfile)
deploy/           config nginx optionnelle pour un VPS déjà occupé
docker-compose.yml  api (interne :8000) + web (public :8081)
DEPLOIEMENT.md    procédure de déploiement sur VPS (Hostinger)
```

## Déploiement sur VPS

Voir [DEPLOIEMENT.md](/home/diallo/github/reskin/DEPLOIEMENT.md) : accès via
`http://IP_DU_VPS:8081`, port à ouvrir dans le firewall, `CORS_ORIGINS` à ajuster.

## Sécurité

`META_API_KEY` reste toujours côté backend (`backend/.env`, jamais commité —
voir `.gitignore`). Le frontend ne l'appelle jamais directement : tous les
appels IA transitent par les routes `/api/*` du backend.
