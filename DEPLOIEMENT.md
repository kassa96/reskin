# Déploiement — Reskin (sans nom de domaine)

Site accessible via `http://IP_DU_VPS:8081`, sans toucher aux autres sites du VPS.

## Architecture

```text
Navigateur → http://IP:8081 → web (nginx + Angular)
                                   ├─ /api/*    → api:8000 (FastAPI)
                                   └─ /static/* → api:8000 (visuels)
```

- `api` : backend FastAPI, **non exposé** publiquement (réseau Docker interne).
- `web` : seul port ouvert (`8081`), sert le frontend et proxie l'API.
  Le frontend appelle l'API en relatif, donc pas de CORS à contourner
  et aucun nom de domaine requis.

## Prérequis (sur le VPS)

- Docker + plugin compose : `docker --version` et `docker compose version`
- Port `8081/tcp` ouvert dans le firewall Hostinger
- Ta clé `META_API_KEY` (Meta Model API)

## 1. Récupérer le projet

```bash
git clone <URL_DU_REPO> reskin
cd reskin
```

## 2. Configurer l'environnement

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Contenu requis :

```env
META_API_KEY=<ta_clé_meta_model_api>
CORS_ORIGINS=["http://IP_DU_VPS:8081"]
```

> Remplace `IP_DU_VPS` par l'IP publique du VPS.
> `CORS_ORIGINS` doit contenir l'URL publique **exacte** (format JSON),
> sinon le navigateur bloquera les appels à l'API.

## 3. Lancer

```bash
docker compose up -d --build
```

## 4. Vérifier

```bash
curl http://localhost:8081/api/health   # attendu : {"status":"ok"}
docker compose ps                        # api: healthy, web: running
```

Puis ouvre `http://IP_DU_VPS:8081` dans un navigateur :
teste un upload + génération, et l'affichage des exemples/mannequins
(ce sont les routes `/static/*` du backend).

## Maintenance

```bash
docker compose logs -f            # voir les logs (api + web)
docker compose logs -f api        # backend seul

# Mise à jour après un git pull
git pull
docker compose up -d --build

# Redémarrage simple
docker compose restart

# Arrêt complet (le volume api-cache est conservé)
docker compose down
```

## Dépannage

| Symptôme | Cause probable | Action |
|---|---|---|
| `{"status":"ok"}` OK mais page blanche | Build frontend | `docker compose logs web`, rebuild |
| Erreurs CORS dans la console navigateur | `CORS_ORIGINS` incorrect | Corriger `backend/.env`, puis `docker compose up -d api` |
| `api` en `unhealthy` | Clé manquante/invalide | Vérifier `META_API_KEY`, `docker compose logs api` |
| Timeout à la génération | Normal si > 120 s | Les timeouts sont à 120 s (backend 90 s) ; relancer |
| Port 8081 injoignable de l'extérieur | Firewall | Ouvrir `8081/tcp` côté Hostinger |

## Optionnel : passer par le nginx du VPS

Par défaut inutile. À faire uniquement pour centraliser logs/HTTPS :

1. Dans `docker-compose.yml`, remplace `"8081:80"` par `"127.0.0.1:8081:80"`.
2. `sudo cp deploy/nginx-vps-reskin.conf /etc/nginx/conf.d/`
3. Remplace `IP_DU_VPS` si besoin, puis `sudo nginx -t && sudo systemctl reload nginx`.
4. `docker compose up -d` puis accès toujours via `http://IP_DU_VPS:8081`.
