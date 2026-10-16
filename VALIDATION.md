# Verification record — 16 October 2026

## Verified locally

- Backend: **32 tests passed**, covering health/readiness, CRUD, validation, expiry filters, metrics, restock/consume/waste, ledger retention, capacity limits and concurrent consumption.
- Alembic: existing inventory upgrade from 0001 to 0002, downgrade and re-upgrade passed on isolated SQLite.
- Frontend: **6 date-boundary tests passed** and Vite 8 production build passed with Node 22.
- npm audit: **0 known vulnerabilities** after upgrading Vite and its React plugin.
- pip-audit of runtime requirements: **no known vulnerabilities found**.
- Bandit application scan: no medium/high findings.
- actionlint: workflow syntax passed.
- Helm: lint and template rendering passed, including a custom namespace and GitOps values.
- Terraform 1.9.8: fmt check, init with backend disabled, and validate passed. No AWS plan/apply was executed.
- Headless Chrome: create → restock → consume → activity flow passed against the local API; no JavaScript page errors and no document overflow at 390px. Screenshots captured at 1440px and 390px. The browser check exposed an ambiguous select label; explicit accessible labels were added and the check then passed.

These checks do not prove PostgreSQL concurrency, Docker execution or an AWS deployment. There is a Starlette test-client deprecation warning concerning httpx; tests still pass.

## CI evidence

[Actions history](https://github.com/mayank-0789/pantryplus-capstone/actions).

The initial baseline run 38946147648 succeeded before the adaptation was pushed, including image publication and an ephemeral kind smoke test. It validates the starting scaffold only. The revised workflow requires fresh results for the final revision and uses stricter image scan gating. Do not treat that earlier green run as evidence for the final code.

## Remaining acceptance work

- Final-revision image builds and strict Trivy results; resolve any findings before release.
- PostgreSQL integration/concurrency and migration-lock checks.
- Compose execution in an environment with a running Docker daemon.
- Update and validate AWS EKS/storage configuration, then actual plan/apply/destroy evidence.
- Live Kubernetes replicas, ingress, storage, HPA, Prometheus UP targets, Grafana and GitOps sync evidence.
- Commit-to-CI-to-deployment demonstration and final screenshots.

The inherited Terraform EKS default and Grafana demo authentication require review before deployment. No AWS resources were created by this task. Original source screenshots are not substituted for missing evidence.

## History

The source commit is retained. New commits contain real changes and actual creation times; no dates or work intervals were fabricated. The published repository is standalone, with an adapted application baseline.
