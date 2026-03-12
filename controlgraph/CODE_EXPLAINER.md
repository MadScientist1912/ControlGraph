
# ControlGraph Code Explainer

## What this system does
ControlGraph is an API-first regulatory data control platform. It lets a tenant register datasets, define controls, run those controls against real data sources, create exceptions on failure, route approvals, map datasets into reports and obligations, store lineage, generate evidence packs, and surface dashboard metrics.

## How the code is organised

### `app/core/config.py`
This reads runtime settings such as `DATABASE_URL`, `SECRET_KEY`, and where evidence files should be stored.

### `app/core/database.py`
This creates the SQLAlchemy engine, session factory, and base model. The same code works with SQLite for Colab demos and PostgreSQL for real deployment.

### `app/core/security.py`
This handles password hashing, JWT token creation, JWT decoding, and API key generation.

### `app/models.py`
This is the database schema. It contains tenants, users, memberships, API keys, data sources, datasets, dataset fields, lineage edges, reports, obligations, controls, control runs, exceptions, approvals, evidence packs, webhooks, and audit logs.

### `app/schemas.py`
These are request models used by FastAPI to validate incoming JSON payloads.

### `app/deps.py`
This is the authentication and authorisation layer. It reads either a JWT bearer token or a tenant-bound API key and produces a context object that tells the app who is calling, which tenant they belong to, and what role they have.

### `app/services/auth_service.py`
This creates tenants and admin users, verifies login credentials, and issues API keys.

### `app/services/connector_service.py`
This is where data is actually loaded from real sources. In this v1 implementation the system supports CSV and SQL-based sources. SQL sources are read through SQLAlchemy connection URLs.

### `app/services/control_service.py`
This is the engine of the product. It loads the dataset through the connector layer and executes control logic such as completeness, threshold, duplicate, freshness, schema drift, and reconciliation. When a control fails it automatically creates an exception and triggers webhook alerts.

### `app/services/impact_service.py`
This walks dataset-to-report relationships and lineage edges to determine which reports and obligations are impacted by a data issue.

### `app/services/evidence_service.py`
This generates evidence files on disk as JSON bundles for exception or dataset scopes.

### `app/services/alert_service.py`
This posts webhook alerts and stores delivery logs.

### Routers
Routers expose the product as an HTTP API:
- `auth.py`: register tenant, login, who-am-I, create API keys
- `data_assets.py`: data sources, datasets, fields, report-dataset links
- `governance.py`: reports, obligations, report impact
- `lineage.py`: create lineage edges and retrieve graph slices
- `controls.py`: create controls and launch asynchronous control runs
- `exceptions.py`: review, comment, override, resolve, inspect event history
- `approvals.py`: approval workflow endpoints
- `evidence.py`: evidence pack creation and retrieval
- `webhooks.py`: alert endpoints and delivery history
- `dashboard.py`: operational summary metrics

### `app/main.py`
This wires everything together, creates tables, and mounts all API routers.

## End-to-end flow
1. Register a tenant and login.
2. Create a data source and a dataset.
3. Add dataset fields.
4. Create a report and obligation, then link the dataset and obligation.
5. Optionally add lineage edges.
6. Create a control definition for the dataset.
7. Trigger a control run.
8. If the control fails, an exception is created automatically.
9. Request and approve an override or fix the data and rerun the control.
10. Generate an evidence pack.
11. Use the dashboard endpoint to monitor overall control health.

## Why the architecture looks like this
The design is intentionally practical:
- It is multi-tenant.
- It supports both human auth and machine auth.
- It uses real connectors instead of fake control logic.
- It can run in Colab with SQLite but is structured so the same app can be moved to PostgreSQL.
- It keeps the core primitives generic, so the same platform can later serve banking, insurance, fintech, AML, DORA, or AI governance use cases.
