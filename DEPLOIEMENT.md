# Deployment — Reskin (no domain name)

Site available at `http://VPS_IP:8081`, without touching the other sites on the VPS.

## Architecture

```text
Browser → http://IP:8081 → web (nginx + Angular)
                                   ├─ /api/*    → api:8000 (FastAPI)
                                   └─ /static/* → api:8000 (visuals)
```

- `api`: FastAPI backend, **not** publicly exposed (internal Docker network).
- `web`: only open port (`8081`), serves the frontend and proxies the API.
  The frontend calls the API with relative paths, so no CORS to work around
  and no domain name required.

## Prerequisites (on the VPS)

- Docker + compose plugin: `docker --version` and `docker compose version`
- Port `8081/tcp` open in the Hostinger firewall
- Your `META_API_KEY` (Meta Model API)

## 1. Get the project

```bash
git clone <REPO_URL> reskin
cd reskin
```

## 2. Configure the environment

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Required content:

```env
META_API_KEY=<your_meta_model_api_key>
CORS_ORIGINS=["http://VPS_IP:8081"]
```

> Replace `VPS_IP` with the public IP of the VPS.
> `CORS_ORIGINS` must contain the **exact** public URL (JSON format),
> otherwise the browser will block API calls.

## 3. Launch

```bash
docker compose up -d --build
```

## 4. Verify

```bash
curl http://localhost:8081/api/health   # expected: {"status":"ok"}
docker compose ps                        # api: healthy, web: running
```

Then open `http://VPS_IP:8081` in a browser:
test an upload + generation, and the display of examples/mannequins
(these are the backend `/static/*` routes).

## Maintenance

```bash
docker compose logs -f            # see logs (api + web)
docker compose logs -f api        # backend only

# Update after a git pull
git pull
docker compose up -d --build

# Simple restart
docker compose restart

# Full stop (the api-cache volume is kept)
docker compose down
```

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `{"status":"ok"}` OK but blank page | Frontend build | `docker compose logs web`, rebuild |
| CORS errors in the browser console | Wrong `CORS_ORIGINS` | Fix `backend/.env`, then `docker compose up -d api` |
| `api` `unhealthy` | Missing/invalid key | Check `META_API_KEY`, `docker compose logs api` |
| Generation timeout | Normal if > 120 s | Timeouts are 120 s (backend 90 s); retry |
| Port 8081 unreachable from outside | Firewall | Open `8081/tcp` on the Hostinger side |

## Optional: go through the VPS nginx

Useless by default. Only do this to centralize logs/HTTPS:

1. In `docker-compose.yml`, replace `"8081:80"` with `"127.0.0.1:8081:80"`.
2. `sudo cp deploy/nginx-vps-reskin.conf /etc/nginx/conf.d/`
3. Replace `VPS_IP` if needed, then `sudo nginx -t && sudo systemctl reload nginx`.
4. `docker compose up -d`, then still access via `http://VPS_IP:8081`.
