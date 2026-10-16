# Pantry Plus — DevOps capstone

**Mayank Gupta · 24BCS10220**

Submission repository: https://github.com/mayank-0789/pantryplus-capstone

Pantry Plus adapts an existing Pantry application and infrastructure scaffold. The changes made here are listed below; [VALIDATION.md](VALIDATION.md) records verification and remaining deployment work.

The published branch is `main`. Cloud deployment and submission evidence are not yet complete. Source screenshots are reference material, not evidence from my environment.

## Upstream guide: Pantry

[![ci-cd](https://github.com/mayank-0789/pantryplus-capstone/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/mayank-0789/pantryplus-capstone/actions/workflows/ci-cd.yml)

Pantry keeps track of what is in the kitchen: how much of each thing is left, where it lives,
and when it goes off. It flags items running low and items to use within the week. React
front end, FastAPI back end, PostgreSQL, and the delivery pipeline around them: Docker
Compose for local runs, GitHub Actions for build, test, scan and publish, Helm for Kubernetes,
Terraform for the AWS network and EKS cluster, Prometheus and Grafana for monitoring, Argo CD
for GitOps.

```
git push ──> GitHub Actions ──> pytest, vite build
                               docker build backend + frontend
                               trivy (fail on HIGH/CRITICAL)
                               push ghcr.io/<owner>/pantry/{backend,frontend}:<sha>
                               helm upgrade --install on kind, smoke test

browser ──> Ingress ──┬── /      frontend (nginx, React bundle)
                      └── /api   backend  (FastAPI) ──> postgres (StatefulSet + PVC)
                                    │
                             Prometheus ──> Grafana
```

## Layout

```
backend/          FastAPI app, SQLAlchemy model, Alembic migration, pytest suite, Dockerfile
frontend/         React + Vite source, nginx config, Dockerfile
docker-compose.yml
helm/pantry/      chart: postgres, backend, frontend, ingress, hpa, configmap, secret
k8s/              namespace and the Argo CD Application
terraform/        VPC + EKS (terraform-aws-modules)
monitoring/       Prometheus and Grafana manifests with a provisioned dashboard
troubleshooting/  two planted faults for the troubleshooting drill
scripts/          load generator
docs/             screenshots
```

## Run it locally

```bash
cp .env.example .env
docker compose up -d --build
open http://localhost:3000
curl localhost:8000/api/items/stats
```

If 3000, 8000 or 5432 are busy on your machine, set `FRONTEND_PORT` and `BACKEND_PORT` in
`.env`. Postgres is not published to the host.

Without Docker, for development:

```bash
docker run -d --name pg -e POSTGRES_DB=pantry -e POSTGRES_USER=pantry -e POSTGRES_PASSWORD=pantry -p 5432:5432 postgres:16-alpine
cd backend && python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
cd ../frontend && npm ci && npm run dev
```

## Data model

One table, `items`: name, category (`produce`, `dairy`, `grains`, `protein`, `spices`,
`frozen`, `other`), quantity and unit (`pcs`, `g`, `kg`, `ml`, `l`, `pack`), a minimum
quantity that marks the item as running low, an optional best-before date, a location and
notes. "Use soon" means a best-before date within seven days.

## API

| Method | Path | |
|---|---|---|
| GET | `/health` | process is up |
| GET | `/ready` | database answers |
| GET | `/metrics` | Prometheus exposition |
| GET | `/api/items` | list; filters `?category=`, `?low_stock=true`, `?expiring=true` |
| POST | `/api/items` | add an item, 201 |
| GET | `/api/items/{id}` | |
| PUT | `/api/items/{id}` | partial update |
| POST | `/api/items/{id}/consume` | subtract an amount; 409 if more than is left |
| DELETE | `/api/items/{id}` | 204 |
| GET | `/api/items/stats` | totals, by category, low stock, expiring soon, expired |
| GET | `/docs` | OpenAPI UI |

Unknown categories or units and negative quantities are rejected with 422.

## Tests

```bash
cd backend && python -m pytest -v
```

Nine tests covering health and readiness, validation, every endpoint, the list filters, the
consume rule, the stats maths and the metrics endpoint. They use a throwaway SQLite file
through a dependency override, so no database is needed. CI runs the same command.

## Images

Both Dockerfiles are multi-stage and run as a fixed non-root UID. The backend installs its
dependencies in one stage and copies the result into a slim runtime; `entrypoint.sh` runs
`alembic upgrade head` and then uvicorn, so an empty database is migrated on first start.
The frontend builds the Vite bundle with Node and serves it from `nginx-unprivileged`; nginx
proxies `/api`, `/health`, `/ready`, `/docs` and `/metrics` to the backend so the browser only
talks to one origin.

Both final stages apply the base image's security updates. Earlier builds of this stack failed
Trivy on exactly that: the stock Alpine base carried fixable OpenSSL CVEs, and an older
FastAPI pin held back a Starlette with three HIGH findings. Base-image updates and a
FastAPI/Starlette bump cleared them, and the images scan clean for fixable HIGH and CRITICAL.

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push to `main` and on pull requests.

1. `test` and `frontend` in parallel: pytest with a JUnit artifact, `vite build` with the bundle as an artifact.
2. `images`, a matrix over backend and frontend: build, Trivy with `severity: HIGH,CRITICAL`,
   `ignore-unfixed: true`, `exit-code: 1`, a JSON report artifact, then push to GHCR tagged with
   the 7-character commit SHA. Pull requests stop before the push.
3. `deploy`: a kind cluster in the runner, a pull secret from `GITHUB_TOKEN`, `helm upgrade
   --install` with the tag just pushed, then a curl from inside the cluster through the frontend
   Service: `/ready`, add an item, `/stats`, and `/metrics` must show the counter.

Only `GITHUB_TOKEN` is used. Nothing long-lived is stored in the repository or its secrets.

## Kubernetes and Helm

```bash
kubectl apply -f k8s/namespace.yaml
helm upgrade --install pantry helm/pantry \
  --set image.backend=ghcr.io/<owner>/pantry/backend \
  --set image.frontend=ghcr.io/<owner>/pantry/frontend \
  --set image.tag=<sha> --set image.pullPolicy=IfNotPresent --set image.pullSecret=ghcr
kubectl -n pantry get pods,svc,ingress,hpa,pvc
helm list -n pantry
```

The chart's defaults assume Minikube with images built into the node (`minikube image
build`, `pullPolicy: Never`). `values-dev.yaml` drops to single replicas with no HPA;
`values-prod.yaml` raises replicas, uses `IfNotPresent`, and expects the database Secret to
exist already (`postgres.existingSecret`) instead of rendering one.

In the chart: a postgres StatefulSet with a `volumeClaimTemplate` and `pg_isready` probes; a
backend Deployment with startup, readiness and liveness probes, `runAsNonRoot`, dropped
capabilities, resource limits, Prometheus scrape annotations and a config checksum so
ConfigMap changes roll the Pods; a frontend Deployment with its nginx config from a ConfigMap;
an Ingress sending `/api` to the backend and `/` to the frontend; an HPA on backend CPU.

Add `<ingress ip> pantry.local` to `/etc/hosts` to open it in a browser. On Minikube with the
Docker driver, use `minikube service ingress-nginx-controller -n ingress-nginx --url` and send
`Host: pantry.local`.

## Terraform

`terraform/` creates a VPC with two public and two private subnets across two availability
zones, one NAT gateway, and an EKS cluster with a managed node group in the private subnets,
using `terraform-aws-modules/vpc` and `terraform-aws-modules/eks`.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
aws eks update-kubeconfig --region ap-south-1 --name pantry-dev
terraform destroy
```

Credentials come from the environment or an AWS CLI profile, never from a file in this repo.
The cluster and the NAT gateway cost money by the hour; destroy when done. On EKS, install
ingress-nginx and metrics-server first, then run the same `helm upgrade --install` as above.

## Monitoring

`monitoring/prometheus.yaml` runs Prometheus in the app namespace with RBAC to list Pods and a
`kubernetes_sd_configs` job that keeps Pods annotated `prometheus.io/scrape: "true"`. The chart
puts those annotations on the backend, so Pods added by the HPA are scraped automatically. Two
rules: `BackendHighErrorRate` and `BackendDown`.

`monitoring/grafana.yaml` provisions the datasource and a Pantry dashboard: requests per
second by route, p95 latency, items added, error rate, backend Pods scraped.

```bash
kubectl apply -f monitoring/
kubectl -n pantry port-forward svc/prometheus 9090:9090
kubectl -n pantry port-forward svc/grafana 3000:3000
./scripts/load-test.sh http://<ingress> pantry.local 120
```

The backend's `/metrics` comes from `prometheus_client`: a request counter by method, route
template and status, a latency histogram, an in-flight gauge, an items-added counter and a
consumed counter by unit.

## GitOps

`k8s/argocd-application.yaml` points Argo CD at `helm/pantry` on `main` with automated sync,
prune and self-heal. Replica drift on the backend Deployment is ignored because the HPA owns
that number. Change `values.yaml`, push, and the cluster follows.

## Troubleshooting drill

`troubleshooting/` holds two faults to apply against a running release and a README with the
diagnosis for each: a values override that points the backend at a database host that does
not exist, and an Ingress whose `/api` path names a Service that does not exist. Both are
found with status, events, logs, then the path between components, before anything is changed.

## Screenshots

See [docs/](docs/).
