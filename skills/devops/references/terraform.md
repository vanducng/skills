# Terraform / OpenTofu

Infrastructure as code. Commands below use `terraform`; `tofu` (OpenTofu) is a drop-in replacement.

## Core workflow

```bash
terraform init                    # download providers, configure backend
terraform fmt -recursive          # canonical formatting
terraform validate                # syntax + internal consistency
terraform plan -out=tfplan        # compute the diff - ALWAYS read it
terraform apply tfplan            # apply the exact reviewed plan
terraform destroy                 # tear down (confirm scope - irreversible)
```

**Never `apply` without reviewing a `plan` first**, and prefer `apply tfplan` (a saved plan) over `apply` (which re-plans and may pick up drift you didn't review). In CI, `plan` on PR and gate `apply` behind approval on merge.

## State

- **State is sensitive and authoritative** - it can contain secrets in plaintext. Never commit `terraform.tfstate` to git.
- Use a **remote backend with locking** (S3 + DynamoDB, GCS, Terraform Cloud) so concurrent runs don't corrupt state.
- Inspect/repair, don't hand-edit: `terraform state list`, `state show <addr>`, `state mv` (rename without destroy/recreate), `state rm` (drop from state without destroying the resource), `import` (adopt existing infra).
- Detect **drift** with `terraform plan` (or `plan -refresh-only`) - a non-empty plan on unchanged code means something changed out of band.

## Structure & modules

```
.
├── main.tf          # resources
├── variables.tf     # input variables (typed, with descriptions)
├── outputs.tf       # exported values
├── versions.tf      # required_version + provider version constraints
├── backend.tf       # remote state config
└── modules/         # reusable components
```

- **Pin provider and module versions** (`~> 5.0`), commit `.terraform.lock.hcl`.
- Extract reused infra into **modules**; keep them focused and parameterized. Pass config via variables, expose results via outputs - don't reach into a module's internals.
- Separate environments with **workspaces** or (better for real divergence) separate state/backends per env directory. `terraform workspace new staging` / `select`.
- Mark secret variables `sensitive = true`; source real secrets from a vault/secret manager or `TF_VAR_*` env, never hardcode.
- Use `for_each` (stable keys) over `count` (index-based) for collections so adding/removing one element doesn't churn the rest.

## Safe-change habits

- `-target=<addr>` to scope a plan/apply to one resource during incident response (not routine use - it skips dependency ordering).
- `lifecycle { prevent_destroy = true }` on stateful resources (databases, buckets).
- `create_before_destroy` for zero-downtime replacement.
- Run `tflint` and `tfsec`/`checkov` (or `trivy config`) in CI to catch misconfig and security issues before apply.
