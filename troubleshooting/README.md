# Troubleshooting drill

Apply one fault at a time against a running release, diagnose it with kubectl before
changing anything, then fix it.

## Fault 1: wrong database host

```bash
helm upgrade pantry helm/pantry -f troubleshooting/fault-1-wrong-db-host.yaml --wait --timeout 90s
kubectl -n pantry get pods -l app.kubernetes.io/name=backend
kubectl -n pantry logs <new pod>
kubectl -n pantry get configmap pantry-config -o jsonpath='{.data.POSTGRES_HOST}'
kubectl -n pantry get svc | grep postgres
helm rollback pantry
```

Expected: the upgrade times out, one new Pod stays `0/1` with a readiness 503, the two old Pods
keep serving. The log says `failed to resolve host 'pantry-postgres-typo'`. The Service is
called `pantry-postgres`. Rollback restores revision 1.

## Fault 2: Ingress to a missing Service

```bash
kubectl apply -f troubleshooting/fault-2-ingress-wrong-service.yaml
curl -H 'Host: pantry.local' http://<ingress>/api/items/stats
kubectl -n pantry describe ingress pantry
kubectl -n pantry run tmp --rm -i --restart=Never --image=curlimages/curl -- curl -s http://pantry-backend/api/items/stats
helm template pantry helm/pantry --show-only templates/ingress.yaml | kubectl apply -f -
```

Expected: 503 from the Ingress, `describe` shows `services "pantry-backend-v2" not found`,
the backend Service answers from inside the cluster. Re-rendering the Ingress fixes it.
