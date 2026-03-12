# ControlGraph

ControlGraph is an API-first regulatory data control platform for regulated firms. It helps teams register critical datasets, run control checks against real sources, capture lineage, manage exceptions and approvals, map impact to reports and obligations, generate evidence packs, and trigger webhook alerts.

## What is included

- FastAPI backend
- Multi-tenant auth with JWTs and tenant-bound API keys
- Real CSV and SQL connector execution
- Controls engine for completeness, threshold, duplicate, freshness, schema drift, and reconciliation checks
- Exception workflow and approvals
- Reports, obligations, and lineage
- Evidence pack generation
- Webhook alerting
- Dashboard summary endpoint
- Demo CSV files for local testing

## Repo structure

```
controlgraph/
├── app/
│   ├── core/
│   ├── routers/
│   ├── services/
│   ├── deps.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── demo_data/
├── CODE_EXPLAINER.md
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

## Quick start

### 1) Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment

```bash
cp .env.example .env
```

By default the app will run on local SQLite. To use PostgreSQL, change `DATABASE_URL` in `.env`.

### 4) Run the API

```bash
uvicorn app.main:app --reload
```

Open the docs at `http://127.0.0.1:8000/docs`.

## Running with Docker

```bash
docker compose up --build
```

This starts PostgreSQL and the FastAPI app together.

## Minimal first demo flow

1. `POST /v1/tenants/register`
2. `POST /v1/auth/login`
3. `POST /v1/data-sources`
4. `POST /v1/datasets`
5. `POST /v1/datasets/{dataset_id}/fields`
6. `POST /v1/reports` and `POST /v1/obligations`
7. link the dataset to a report
8. `POST /v1/controls`
9. `POST /v1/control-runs`
10. inspect exceptions, approvals, evidence packs, and dashboard summary

## Example data source payloads

### CSV source

```json
{
  "name": "Primary CSV Source",
  "source_type": "csv",
  "environment": "production",
  "connection_metadata": {
    "path": "./demo_data/primary_positions.csv"
  }
}
```

### SQL source

```json
{
  "name": "Operations DB",
  "source_type": "sql",
  "environment": "production",
  "connection_metadata": {
    "url": "postgresql+psycopg://postgres:postgres@localhost:5432/controlgraph"
  }
}
```

## Important notes 

- This repo is a strong MVP, not a hardened production system.
- `Base.metadata.create_all()` is used for convenience. Replace it with Alembic migrations before production.
- BackgroundTasks are used for async execution. Replace them with Celery or a queue worker for reliability.
- Secrets must come from environment variables or a secret manager.
- Add stronger RBAC, rate limiting, structured logging, and test coverage before selling this to real clients.

## License

No license file is included yet. Choose a license before making the repository public.
