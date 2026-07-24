# Cloud Platforms: GCP, AWS, Cloudflare

Platform selection: sub-50ms global edge → Cloudflare Workers; large egress-free storage → R2; containerized workload → Cloud Run (managed) or GKE/EKS (orchestration); enterprise Kubernetes → GKE/EKS/AKS.

## Google Cloud (gcloud)

```bash
gcloud auth login && gcloud config set project PROJECT_ID

# Cloud Run - serverless containers (default for stateless HTTP)
gcloud run deploy my-service \
  --image=gcr.io/PROJECT/img:tag --region=us-central1 --allow-unauthenticated
gcloud run services describe my-service --region=us-central1

# GKE - managed Kubernetes
gcloud container clusters create my-cluster --zone=us-central1-a \
  --num-nodes=3 --machine-type=e2-medium
gcloud container clusters get-credentials my-cluster --zone=us-central1-a  # wires kubectl
gcloud container clusters resize my-cluster --num-nodes=5 --zone=us-central1-a

# Build & push
gcloud builds submit --tag gcr.io/PROJECT/img:tag
```

After `get-credentials`, drive the cluster with `kubectl` (see kubernetes.md). Prefer Artifact Registry over the legacy `gcr.io`. Cloud SQL for managed Postgres/MySQL; App Engine for fully-managed PaaS.

## AWS (EKS)

```bash
aws sts get-caller-identity                      # confirm identity/account first

# EKS cluster (eksctl is the simplest path)
eksctl create cluster --name my-cluster --region us-east-1 \
  --nodes 3 --node-type t3.medium
aws eks update-kubeconfig --name my-cluster --region us-east-1   # wires kubectl

# ECR (container registry)
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/myapp:1.0
```

ECS/Fargate for serverless containers without K8s; provision clusters with Terraform (`terraform-aws-modules/eks`) for anything long-lived rather than ad-hoc `eksctl`.

## Cloudflare (Wrangler)

Workers = edge serverless (V8 isolates, sub-50ms globally). R2 = S3-compatible object storage, zero egress fees. D1 = edge SQLite. KV = eventually-consistent key-value.

```bash
npm i -g wrangler && wrangler login
wrangler init my-worker
wrangler dev            # local edge runtime
wrangler deploy         # ship to the edge
wrangler tail           # live logs

# Bindings (configured in wrangler.toml)
wrangler r2 bucket create my-bucket
wrangler d1 create my-db
wrangler d1 execute my-db --file=./schema.sql
wrangler secret put API_KEY     # encrypted secret, not in wrangler.toml
```

`wrangler.toml` declares routes, bindings (R2/D1/KV/queues), and vars; put secrets via `wrangler secret put`, never in the toml. Cloudflare Pages for static sites + Functions; use `--env production` to target an environment.

## Cross-platform habits

- Authenticate and confirm the active project/account/region **before** any deploy - wrong-account deploys are the classic footgun.
- Keep infra in Terraform where possible; use the CLI for inspection, one-off ops, and local dev (`run/dev`).
- Pin image tags to digests for production; scan before push.
- Right-size compute and set autoscaling bounds; watch egress and idle-resource cost.
