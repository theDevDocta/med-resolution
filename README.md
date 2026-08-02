# BDPM Drug Resolver

Résolveur local de noms de médicaments français : détecte, recherche et
corrige des noms de médicaments dans des transcriptions médicales bruitées, à
partir d'une base construite depuis la Base de Données Publique des
Médicaments (BDPM). Fonctionne entièrement en local (SQLite + RapidFuzz),
sans dépendance à une API externe au runtime.

Ce service ne pose pas de diagnostic et ne valide pas une prescription : il
propose des correspondances lexicales avec un score de confiance.

## Architecture

```
app/
├── main.py            # FastAPI app
├── api/               # routes HTTP (health, search, resolve)
├── core/              # normalisation, scoring, DrugResolver (logique métier)
├── db/                # schéma SQLite, connexion, requêtes
├── importers/         # téléchargement + parsing + construction de la base
└── schemas/           # modèles Pydantic (requêtes/réponses)
scripts/
├── init_db.py         # crée une base vide (schéma seul)
└── update_bdpm.py      # télécharge la BDPM et reconstruit la base
```

## Démarrage local

```bash
uv sync
uv run python -m scripts.update_bdpm   # télécharge la BDPM, construit data/bdpm.sqlite
uv run uvicorn app.main:app --host 0.0.0.0 --port 8090
```

Sans accès réseau (ex: environnement isolé), on peut construire la base à
partir de fichiers BDPM déjà présents dans `data/raw/` :

```bash
uv run python -m scripts.update_bdpm --skip-download
```

## Tests

```bash
uv run pytest
```

Les tests d'intégration utilisent un petit jeu de fichiers BDPM factices
(`tests/fixtures/`) pour construire une base de test, sans dépendre du réseau.

## Docker

```bash
docker compose up --build bdpm-resolver
```

Au premier démarrage, si `data/bdpm.sqlite` est absent, le conteneur
télécharge automatiquement la BDPM et construit la base (volume `bdpm-data`
persistant, donc une seule fois).

## API

### `GET /health`

```bash
curl http://localhost:8090/health
```

### `GET /search`

```bash
curl "http://localhost:8090/search?q=amoxiciline&limit=5"
curl "http://localhost:8090/search?q=doliprane&commercialized_only=false"
```

### `POST /resolve`

```bash
curl -X POST http://localhost:8090/resolve \
  -H "Content-Type: application/json" \
  -d '{
        "verbatim": "le patient prend de l amoxiciline cinq cents",
        "llm_version": "le patient prend de l'\''amoxicilline 500 mg",
        "suspected_term": "amoxiciline",
        "context": "infection ORL, trois prises par jour",
        "limit": 5
      }'
```

### `POST /admin/update-database`

Reconstruit la base à chaud (télécharge la BDPM + reconstruit + remplace
atomiquement), sans redémarrer le service — équivalent de
`scripts/update_bdpm.py`, déclenchable via l'API. Une seule mise à jour à la
fois (`409` si déjà en cours) ; `422` si l'import échoue (fichiers manquants,
trop de lignes rejetées, médicaments de contrôle introuvables...).

Si `ADMIN_API_KEY` est définie, l'appel doit inclure le header
`X-Admin-Key` (sinon `401`). En dev local, sans cette variable, l'endpoint
reste ouvert.

```bash
curl -X POST http://localhost:8090/admin/update-database \
  -H "X-Admin-Key: $ADMIN_API_KEY"
curl -X POST "http://localhost:8090/admin/update-database?skip_download=true" \
  -H "X-Admin-Key: $ADMIN_API_KEY"  # réutilise data/raw/
```

## Variables d'environnement

Voir `.env.example`. Les plus utiles :

- `BDPM_BASE_URL` : URL de téléchargement des fichiers BDPM.
- `BDPM_DATA_DIR` : répertoire contenant `raw/` et `bdpm.sqlite`.
- `PORT` : port d'écoute de l'API.

## Déploiement & CI/CD

Le service est pensé comme un microservice autonome, déployé sur une
instance [Coolify](https://coolify.io) auto-hébergée, avec le pipeline
suivant :

```
push sur main ──► CI (tests) ──► déploiement (webhook Coolify)
                                        │
                    ┌───────────────────┴───────────────────┐
                cron hebdomadaire                    cron toutes les 15 min
           .github/workflows/update-bdpm.yml   .github/workflows/healthcheck.yml
           POST /admin/update-database          GET /health → issue GitHub si down
```

- `.github/workflows/ci-cd.yml` : lance `uv run pytest` sur chaque push/PR ;
  sur push vers `main`, déclenche le webhook de déploiement Coolify.
- `.github/workflows/update-bdpm.yml` : appelle
  `POST /admin/update-database` chaque dimanche à 3h UTC (et manuellement via
  `workflow_dispatch`) pour garder la base BDPM à jour sans intervention.
- `.github/workflows/healthcheck.yml` : ping `GET /health` toutes les 15
  minutes ; ouvre une issue GitHub taguée `health-alert` si le service ne
  répond pas ou renvoie un statut dégradé, et la referme automatiquement
  une fois le service redevenu sain.

### Secrets GitHub à configurer (Settings → Secrets and variables → Actions)

| Secret                 | Usage                                                        |
| ----------------------- | ------------------------------------------------------------ |
| `COOLIFY_WEBHOOK_URL`   | URL du webhook de déploiement du projet Coolify              |
| `COOLIFY_WEBHOOK_TOKEN` | Token d'authentification du webhook Coolify                  |
| `BDPM_SERVICE_URL`      | URL publique du service déployé (ex: `https://bdpm.example.com`) |
| `ADMIN_API_KEY`         | Même valeur que la variable d'environnement `ADMIN_API_KEY` du service |

Ces trois derniers secrets ne peuvent être renseignés qu'une fois le service
déployé une première fois (manuellement) sur Coolify.

## Limites (version 1)

- Correspondance lexicale uniquement (RapidFuzz + SQLite), pas d'embeddings
  ni de LLM dans le moteur de recherche.
- Extraction de dosage limitée à un jeu restreint de nombres français
  fréquents (pas de parseur universel des nombres en toutes lettres).
- Pas de règles phonétiques françaises dédiées (prévu en phase 2).
