# WorldView control-plane Helm chart

Deploys the five control-plane services (identity, catalog, streaming, ai-guide,
gateway) onto a Kubernetes cluster (EKS via `infra/terraform`) with services,
HPA, PodDisruptionBudgets, an ingress for the gateway, and a pre-install
migration Job that runs `alembic upgrade head`.

## Install

```bash
helm repo update
helm install worldview infra/helm-charts/worldview \
  --namespace prod --create-namespace \
  --set jwtSecret="$(openssl rand -base64 48)" \
  -f infra/helm-charts/worldview/values/region-us-east-1.yaml
```

`jwtSecret` is required; the app refuses to boot without a >= 32-char secret in
non-dev environments (matches the codebase secret policy). Never commit it.

## Region overlays

The same chart is deployed to every region; only the overlay differs
(`values/region-<name>.yaml`). Argo CD (or `helm upgrade`) applies the overlay
on top of `values.yaml`, so promotion = promoting one manifest set.

## Key values

| Value            | Meaning                                        |
| ---------------- | ---------------------------------------------- |
| `env`            | `prod` by default (enforces secret policy)     |
| `region`         | `REGION_KEY` injected into every pod           |
| `image.*`        | GHCR image registry/repo/tag                   |
| `database.url`   | DSN for the service Postgres (Aurora)          |
| `redis.url`      | DSN for shared Redis (rate limiting, idempotency) |
| `services.*`     | per-service replicas / env / HPA tuning        |
| `ingress.*`      | gateway ingress host / TLS / annotations       |
| `migration.enabled` | runs `alembic upgrade head` as a Helm hook  |

## Render for inspection

```bash
helm template worldview infra/helm-charts/worldview \
  --set jwtSecret=replace-me-1234567890abcdefghijklmnop
```

## GitOps (Argo CD)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: worldview
spec:
  source:
    repoURL: https://github.com/ghanendrasahu/worldview-monorepo
    path: infra/helm-charts/worldview
    targetRevision: main
    helm:
      valueFiles:
        - values/region-us-east-1.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
