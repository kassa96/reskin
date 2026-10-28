# Plan d'action MVP — Personnalisation d'image produit (Meta Muse)

## Contexte du projet
SaaS permettant aux e-commerçants (marchés africain et occidental) de personnaliser
les images produit génériques issues d'Alibaba/AliExpress. L'utilisateur upload une
image produit + un prompt texte, l'application génère une nouvelle image adaptée
(décor, mannequin, ambiance) tout en préservant le produit.

## Objectif du MVP
Une application web simple avec :
1. Upload d'une image produit
2. Champ de saisie de prompt texte (ex: "remplace le fond par un décor de marché africain, lumière chaude")
3. Appel à la Meta Model API (Muse Image - edit) avec l'image + le prompt
4. Affichage de l'image générée
5. Bouton de téléchargement du résultat

Pas de gestion de compte, pas de crédits, pas de base de données à ce stade —
juste le workflow technique de bout en bout pour valider la qualité du résultat.

---

## Stack technique imposée

- **Backend** : Python, **FastAPI** (version récente)
- **Frontend** : **Angular** (version récente)
- **CSS** : **Tailwind CSS** (version récente), intégré à Angular
- **API de génération et retouche d'image** : Meta **Muse Image** (`muse-image-1.0`) — `POST /v1/images/edits` pour la retouche, `POST /v1/images/generations` pour la création depuis zéro
- **LLM d'analyse et d'enrichissement des prompts** : Meta **Muse Wonder** (`muse-wonder-1.0`) via la Meta Model API (`https://api.meta.ai/v1`, compatible OpenAI)
- **Variables d'environnement** : `META_API_KEY` (clé Meta Model API, alias accepté : `MODEL_API_KEY`) — côté backend uniquement
- **Communication frontend/backend** : API REST (JSON), le frontend Angular
  consomme les endpoints exposés par FastAPI

Note pour Claude Code : vérifier les dernières versions stables de FastAPI,
Angular et Tailwind au moment de l'exécution (ne pas se fier à une version figée
dans ce document).

---

## Exigences fonctionnelles du MVP (le détail d'exécution/étapes est laissé à Claude Code)

1. **Upload d'image** : l'utilisateur sélectionne/dépose une image produit
   (formats courants : jpg, png, webp), avec aperçu avant génération
2. **Saisie du prompt** : un champ texte permettant de décrire la transformation
   souhaitée (ex: changement de décor, ambiance, mannequin)  et optimisation du prompt
3. **Frontend Angular** : affichage de l'image générée à côté de l'originale
   (comparaison avant/après), bouton de téléchargement, indicateur de
   chargement pendant l'appel API
4. **Gestion des erreurs** : image trop volumineuse, format non supporté, échec
   ou timeout de l'appel API, clé API manquante — messages clairs côté
   utilisateur
5. **Sécurité** : la clé `META_API_KEY` ne doit jamais être exposée côté frontend
   Angular — tous les appels à la Meta Model API transitent uniquement par le backend
   FastAPI
   les cles met les le fichier .env
Claude Code est libre de définir la structure de dossiers, l'ordre des tâches,
la configuration Tailwind pour Angular, et l'architecture des composants —
seules les exigences ci-dessus sont contraignantes.

---

## Points d'attention à signaler à Claude Code

1. **Ne jamais exposer la clé API côté client** — tout appel à la Meta Model API doit passer
   par une route API backend (jamais directement depuis le navigateur)
2. **Limiter la taille des images uploadées** (ex: max 10 Mo) pour éviter des
   temps de traitement trop longs
3. **Prévoir un système de logs simple** (console suffit pour le MVP) pour suivre
   les appels API et diagnostiquer les échecs
4. **Ne pas encore implémenter** : gestion des comptes utilisateurs, système de
   crédits, base de données, multi-marché — ce sera pour l'itération suivante

---

## Comment lancer l'application

Prérequis : [uv](https://docs.astral.sh/uv/) (gestion des dépendances Python) et Node.js/npm avec Angular CLI installés.

### 1. Backend (FastAPI)

```bash
cd backend
cp .env.example .env   # puis renseigner META_API_KEY=<votre_clé_meta_model_api>
uv run uvicorn app.main:app --reload --port 8000
```

Le backend refuse de démarrer si `META_API_KEY` est absente ou vide (message d'erreur clair en console).
Vérifier que ça fonctionne : [http://localhost:8000/api/health](http://localhost:8000/api/health) doit répondre `{"status":"ok"}`.

### 2. Frontend (Angular)

Dans un second terminal :

```bash
cd frontend
npm install   # uniquement la première fois
ng serve --port 4200
```

Ouvrir [http://localhost:4200](http://localhost:4200) dans le navigateur.

### Notes

- Les deux serveurs doivent tourner simultanément (backend sur `:8000`, frontend sur `:4200`).
- `META_API_KEY` reste toujours côté backend (fichier `backend/.env`, jamais commité — voir `.gitignore`) ; le frontend ne la voit jamais.
- Pas de Docker ni de configuration de déploiement pour ce MVP.

