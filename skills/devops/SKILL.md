---
name: devops
description: "Deployment and infrastructure operations. Use when writing or debugging a Dockerfile, docker build/run, docker compose; running terraform plan/apply/destroy or editing .tf files and modules; using kubectl, debugging pods (CrashLoopBackOff, ImagePullBackOff, OOMKilled), applying manifests, or writing Helm charts; deploying to GKE/EKS/AKS, Cloud Run, or App Engine; GitOps with Argo CD or Flux; writing GitHub Actions CI/CD workflows; or deploying Cloudflare Workers/Pages/R2/D1. Triggers on: dockerfile, docker compose, terraform, tofu, kubectl, k8s, helm, gcloud, eksctl, argocd, wrangler, github actions, ci/cd pipeline, container, cluster, rollout, image scan."
license: MIT
argument-hint: "[platform] [task]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# DevOps

Deployment and infrastructure operations across containers, orchestration, IaC, cloud platforms, and CI/CD. SKILL.md dispatches; open the reference that matches the task. Distilled operational guidance — verify exact flags against the current tool docs, and never run a destructive command (`terraform apply`, `kubectl delete`, `docker system prune`) without confirming scope.

## When to open which reference

| Task | Open |
| --- | --- |
| Dockerfile, multi-stage build, `docker build/run`, `docker compose`, image size/security, `.dockerignore` | [references/docker.md](references/docker.md) |
| `kubectl` commands, pod debugging (CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending), manifests, rollouts, Helm charts, RBAC/secrets | [references/kubernetes.md](references/kubernetes.md) |
| `terraform`/`tofu` plan/apply/destroy, state, modules, workspaces, remote backends, drift | [references/terraform.md](references/terraform.md) |
| GKE/EKS/AKS clusters, Cloud Run, App Engine, `gcloud`, `eksctl`, Cloudflare Workers/Pages/R2/D1 | [references/cloud-platforms.md](references/cloud-platforms.md) |
| GitHub Actions workflows, GitOps (Argo CD, Flux), deployment strategies, multi-region | [references/cicd-gitops.md](references/cicd-gitops.md) |

## Operating principles (apply everywhere)

1. **Plan before apply.** Always `terraform plan` / `kubectl apply --dry-run=client` / `docker build` before the mutating step. Read the diff.
2. **Least privilege.** Non-root containers, scoped RBAC, per-job CI `permissions`, per-environment secrets. Never bake credentials into images or commit them.
3. **Everything is code and versioned.** Dockerfiles, manifests, `.tf`, Helm values, workflows — all in git, reviewed, applied through CI/GitOps rather than by hand.
4. **Pin versions.** No `latest` image tags, no `@master` actions — pin digests/major versions for reproducibility.
5. **Right-size resources.** Set CPU/memory requests and limits; unbounded workloads get OOM-killed or evicted.
6. **Debug top-down.** Overview (`get`/`ps`) → details (`describe`/`inspect`/events) → logs. Read the error before changing anything.
7. **Scan and observe.** Image scanning (Trivy, `docker scout`), health checks/probes, and metrics/logs are part of "done," not extras.

## Quick start

```bash
# Docker
docker build -t myapp:1.0 . && docker run -d -p 8080:3000 myapp:1.0

# Kubernetes
kubectl apply -f manifests/ --dry-run=client && kubectl apply -f manifests/ && kubectl rollout status deploy/myapp

# Terraform
terraform init && terraform plan -out=tfplan && terraform apply tfplan

# GCP Cloud Run
gcloud run deploy my-service --image gcr.io/PROJECT/img:tag --region us-central1

# Cloudflare Worker
wrangler deploy
```
