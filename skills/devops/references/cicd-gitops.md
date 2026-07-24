# CI/CD & GitOps

## GitHub Actions

Structure a pipeline as stages: build/test → lint → security scan → build image → deploy. Pin actions to a major version (or SHA), scope `permissions` per job to least privilege, and never echo secrets.

```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version-file: go.mod }
      - run: go test -race -shuffle=on ./...

  docker:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write          # push to GHCR
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - uses: docker/metadata-action@v5
        id: meta
        with: { images: ghcr.io/${{ github.repository }} }
      - uses: docker/build-push-action@v6
        with:
          push: ${{ github.event_name != 'pull_request' }}   # never push from untrusted PRs
          tags: ${{ steps.meta.outputs.tags }}
          platforms: linux/amd64,linux/arm64
          provenance: mode=max
          sbom: true
```

**Rules:** `push: false` on PRs (don't publish untrusted code); use OIDC (`id-token: write`) for cloud auth instead of long-lived keys; store secrets in repo/environment secrets, gate prod deploys behind an Environment with required reviewers; add Trivy image scanning (`security-events: write` only on the scan job). Cache dependencies via `setup-*` actions. Reusable workflows (`workflow_call`) for shared logic across repos.

## GitOps

Git is the single source of truth for cluster state; a controller continuously reconciles the cluster to match the repo. You `git push`; the controller deploys - no `kubectl apply` from laptops or CI.

**Argo CD** - pull-based, app-centric:
```bash
argocd app create myapp \
  --repo https://github.com/org/manifests.git --path apps/myapp \
  --dest-server https://kubernetes.default.svc --dest-namespace prod
argocd app sync myapp
argocd app get myapp          # health + sync status; shows drift vs git
```
Prefer an `Application` (or `ApplicationSet` for many envs/clusters) manifest checked into git over imperative `argocd app create`. Enable auto-sync + self-heal so out-of-band `kubectl` changes get reverted; use sync waves/hooks for ordering.

**Flux** - controller-driven, `GitRepository` + `Kustomization`/`HelmRelease` CRDs reconcile on an interval. `flux bootstrap` installs the controllers and commits their own config to the repo.

**Structure:** separate the app-source repo from the config/manifests repo; environments as directories or branches; render with Kustomize overlays or Helm values per env; keep secrets out of git (sealed-secrets, external-secrets, SOPS).

## Deployment strategies

| Strategy | Use when |
| --- | --- |
| Rolling update (K8s default) | Standard stateless services - gradual pod replacement |
| Blue/green | Instant cutover + instant rollback; needs double capacity briefly |
| Canary | Shift a small traffic % to the new version, watch metrics, then ramp |

Always gate promotion on health/metrics; keep the previous version ready for `kubectl rollout undo` / a blue/green swap. Multi-region: deploy per region behind a global load balancer / DNS, roll out region-by-region.
