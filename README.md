# Pantry Plus

**Mayank Gupta · 24BCS10220 · DevOps final capstone**

Submission URL: **https://github.com/mayank-0789/pantryplus-capstone**

A kitchen inventory app for tracking ingredients, expiry dates and stock changes. React frontend, FastAPI API, PostgreSQL persistence, Alembic migrations and a Docker/Helm delivery scaffold.

## Changes in this adaptation

Pantry Plus adapts an existing Pantry application and infrastructure scaffold. The changes made here are listed below; [VALIDATION.md](VALIDATION.md) records verification and remaining deployment work.

- Pantry Plus branding, revised layout, labelled inputs and mobile table scrolling.
- Edit item details and low-stock thresholds from the UI.
- Choose the amount to consume, restock or record as waste, with an optional note.
- Persistent stock activity with before/after accounting; history survives item deletion.
- Atomic stock updates prevent concurrent consumers from spending the same stock twice.
- Explicit decimal bounds, null validation and consistent UTC expiry filters.
- Stock logic extracted into `backend/app/stock_service.py`; frontend renamed to `PantryDashboard.jsx` and `pantryClient.js`.
- Isolated regression tests, migration upgrade/downgrade checks, fail-closed startup, deterministic frontend installs and corrected GitOps source.

## Run with Docker Compose

```sh
cp .env.example .env
# Set a local PostgreSQL password in .env; do not commit it.
docker compose up --build -d
curl -f http://localhost:8000/ready
```

UI: http://localhost:3000 · API docs: http://localhost:8000/docs · metrics: http://localhost:8000/metrics

Containers run as non-root. PostgreSQL data persists in `pgdata`. `docker compose down` preserves that volume; `docker compose down -v` deletes it. Use a URL-safe database password with the current Compose connection-string template.

## Local development and tests

Python 3.12 and Node 22.12 or newer are required.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
python -m pytest -v
# PostgreSQL is the deployment database. SQLite is only a quick local preview.
export DATABASE_URL=sqlite:////tmp/pantryplus-local.sqlite3
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm test
npm run dev -- --host 127.0.0.1
# Production bundle:
npm run build
```

Tests create independent temporary SQLite databases. They do not reset your application database. PostgreSQL concurrency must also be verified in the deployed environment.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health`, `/ready`, `/metrics` | Liveness, schema readiness, Prometheus |
| GET | `/api/items` | Filter by category, low stock, expiring or expired |
| GET | `/api/items/stats` | Inventory totals |
| GET | `/api/items/{id}` | One item |
| POST | `/api/items` | Create item and opening stock entry |
| PUT | `/api/items/{id}` | Edit details; quantity and unit are immutable here |
| POST | `/api/items/{id}/consume` | Consume an explicit amount |
| POST | `/api/items/{id}/restock` | Add an explicit amount |
| POST | `/api/items/{id}/waste` | Remove an explicit amount as waste |
| DELETE | `/api/items/{id}` | Remove item while retaining activity snapshots |
| GET | `/api/activity` | Latest 50 movements; optional item_id and limit (1–200) |

Stock actions accept `{"amount":"0.50","note":"Dinner"}`. Invalid input returns 422, missing items 404 and insufficient stock/capacity 409. Each movement and quantity update shares one transaction. Quantities allow at most two decimal places. Expiry uses UTC dates, includes today through seven days ahead, and excludes empty stock.

## Delivery and infrastructure

The Actions workflow runs backend tests, Bandit, pip-audit, frontend tests/build/audit, Helm lint and Terraform validation. Both images must pass Trivy with HIGH/CRITICAL blocking, including unfixed findings. Scanned images use full commit SHA tags. Publication is disabled until repository variable `ENABLE_IMAGE_PUBLISH=true`; deployment is manual.

```sh
helm lint helm/pantry
helm template pantry helm/pantry --namespace pantry
# After publishing images, creating the DB secret and provisioning a cluster:
helm upgrade --install pantry helm/pantry --namespace pantry --create-namespace \
  -f helm/pantry/values-gitops.yaml \
  --set image.tag=YOUR_PUBLISHED_FULL_COMMIT_SHA --wait
```

GitOps application: `k8s/argocd-application.yaml`, pointed at this repository. Replace the placeholder image tag in `values-gitops.yaml`, create secret `pantry-db` with `POSTGRES_PASSWORD`, and verify storage/ingress before syncing. HPA needs metrics-server. Configure a registry pull secret if images are private. Argo automatic sync is intentionally not enabled before this setup is validated.

Terraform under `terraform/` is an inherited AWS VPC/EKS scaffold, **not proof of an AWS deployment**. Before applying, select a currently supported EKS version, restrict endpoint access, configure EBS CSI IAM/add-on and a working StorageClass for PostgreSQL, and review cost and credentials. The inherited default version 1.31 must not be used as a current recommendation. Keep state and tfvars out of Git; capture plan/apply/destroy evidence from your own account.

Monitoring and troubleshooting manifests remain under `monitoring/` and `troubleshooting/`. Replace Grafana's demo credentials and disable anonymous access before exposing it. Live scrape targets, dashboards and GitOps reconciliation still require cluster verification.

## Verification and evidence

Read [VALIDATION.md](VALIDATION.md) for checks actually performed and remaining rubric work. Screenshots under `docs/local/` are from this adaptation running locally. Upstream screenshots have been removed; only this adaptation’s local evidence is included. No AWS completion or full rubric score is claimed.
