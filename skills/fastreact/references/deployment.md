# Deployment: AWS reference architecture (Option A)

The canonical cost-effective + secure path for this stack. Single EC2 runs docker compose behind an ALB; RDS for Postgres; deliver via GitHub Actions + Ansible-over-SSM. No SSH, no static keys, encryption everywhere.

## Topology

```
GitHub main ──OIDC──> ECR (by SHA) ──Ansible/SSM──> EC2 (private) ──> RDS (private)
                                                       ▲
                                          ALB (public, TLS) ──> users
```

## Images → ECR

- Two images: backend (FastAPI) + frontend (nginx). Build both in CI.
- ECR repos: `scan_on_push = true`, `image_tag_mutability = IMMUTABLE`.
- Tag and deploy by **git SHA**. Never `:latest` / `:prod` (immutable repo rejects re-push; mutable tags make rollback ambiguous).

## Compute: single EC2

- Amazon Linux 2023, `t3.medium`, in a **PRIVATE** subnet (no public IP).
- **Instance profile** (IAM role), no static AWS keys on the box. App reads creds via boto3 default chain.
- IMDSv2 required (`http_tokens = required`). Encrypted gp3 root volume.
- Runs docker compose (compose file + `.env` rendered by Ansible from Secrets Manager).
- Access via SSM Session Manager only. **No port 22, no SSH key pair.**

## Edge: ALB

- Internet-facing, in **>= 2 public subnets** (ALB requires 2+ AZs).
- ACM cert for TLS; HTTPS listener; HTTP listener redirects 80 → 443.
- Target group → EC2 backend/frontend ports; health check path (e.g. `/api/health`).
- Optional: WAFv2 with AWS managed rule groups.

## Data: RDS Postgres

- Private subnet group (>= 2 AZs), `publicly_accessible = false`.
- `storage_encrypted = true`; `force_ssl` via parameter group (app connects with `sslmode=require`).
- Automated backups + PITR; `deletion_protection = true`.
- SG: ingress 5432 only from the EC2 SG.

## Delivery: GitHub Actions → Ansible/SSM

1. On push to `main`: assume an AWS role via **OIDC** (no long-lived CI keys).
2. Build + push both images to ECR tagged with the commit SHA.
3. Run Ansible with `ansible_connection: aws_ssm` (no SSH, no VPN, no bastion).
4. Playbook: Secrets Manager lookup → render `.env` → `docker compose pull` (the SHA tags) → `docker compose up -d` → `alembic upgrade head`.
5. Verify ALB health check / target group healthy before declaring success.

## Runtime credentials & secrets

- App → AWS via the **instance role**. boto3 picks it up through the default credential chain when no env keys are set.
- **Keep the env-key fallback for local dev** (boto3 reads `AWS_*` env vars when present). Do not hard-fail when env keys are absent; that is the production path.
- All runtime secrets (DB URL, JWT secret, OAuth, etc.) live in **Secrets Manager**, fetched at deploy time. Never bake secrets into images or commit them.

## Terraform state

- S3 backend, `encrypt = true`, `use_lockfile = true` (S3-native lock; no DynamoDB table needed).
- **Reuse an existing org state bucket** with a per-app `key` namespace. Do not provision a new bucket per app.
- Isolated state key per app (e.g. `key = "<app>/terraform.tfstate"`).

## Pre-apply checklist

- [ ] **RDS engine version** verified against the available/supported list (a stale pinned version fails the apply).
- [ ] **route53 + DB diff** read in the plan: confirm the DNS record and any DB changes are intended (DB param/version changes can force replace).
- [ ] **>= 2 AZs** for both the ALB public subnets and the RDS subnet group.
- [ ] **Secrets populated** in Secrets Manager before deploy (empty secrets render an empty `.env` and the app boots broken).
- [ ] State backend points at the **existing** bucket + correct per-app key; `use_lockfile = true`.
- [ ] ECR repos exist with `IMMUTABLE` + `scan_on_push`; CI tags by SHA.

## Security floor (non-negotiable, even for PoC)

Private subnets · encryption everywhere (EBS, RDS, S3 state) · secrets only in Secrets Manager · instance role (no static keys) · SSM-only access (no port 22, no SSH key) · OIDC for CI · IMDSv2 required.

---

Per-bug deploy/runtime footguns live in `references/gotchas.md` (this file is the architecture and HOW; gotchas.md owns the bug list).
