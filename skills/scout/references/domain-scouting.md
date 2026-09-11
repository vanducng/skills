# Domain Scouting Playbooks

Concrete search-target recipes for non-software disciplines. Use these as the **prompt body** for Explore / Gemini agents. The general loop (analyze → divide → spawn → aggregate) is in `SKILL.md`.

## Data engineering - trace a source through the lakehouse

When the user says *"what depends on `payments_raw`?"*, walk the lineage in this order - each layer feeds the next:

| Layer | Where to look | Grep targets |
|---|---|---|
| Sources | `**/schema.yml`, `**/sources.yml` | `name: payments_raw`, `source('...payments_raw')` |
| Staging | `models/staging/` | `from {{ source(` referencing payments |
| Intermediate / marts | `models/intermediate/`, `models/marts/` | `ref('stg_payments')`, downstream `ref()` chain |
| Tests | `models/**/schema.yml`, `tests/` | `tests:` blocks, `tests/*.sql` mentioning the model |
| Macros / snapshots / seeds | `macros/`, `snapshots/`, `seeds/` | macros invoked by payments models, `unique_key`, seed CSVs |
| Orchestration | `dags/`, `workflows/`, `pipelines/` | DAG that runs `dbt run --select +payments` |
| BI exposures | `schema.yml` (`exposures:`), `lightdash/`, `lookml/` | `exposures:` block, dashboard YAML |

## DevOps - map an environment variable across the stack

When the user says *"where is `DATABASE_URL` set in staging?"*, walk layers until you hit the runtime override: app config (`.env*`, `config/`) → container (`Dockerfile*`, `docker-compose*.yml` `environment:` blocks) → orchestration (`k8s/`, `helm/`, `kustomize/` `env:` / `valueFrom: secretKeyRef` / ConfigMaps) → IaC (`terraform/`, `pulumi/` secret-manager outputs) → secret store (`.sops.yaml`, `vault/`, `secrets/`) → CI injection (`.github/workflows/` `env:` + `secrets.*`) → the actual runtime (Cloud Run env, ECS task def, Deployment spec).

Don't stop at "found it in `.env.example`" - that's the template, not the truth.

## Multi-env override precedence

Which file wins decides where the fix lands:

| Layout | Convention |
|---|---|
| Helm | `values.yaml` + `values-<env>.yaml`, sometimes `charts/<svc>/values/<env>.yaml` |
| Kustomize | `base/` + `overlays/{dev,staging,prod}/` |
| Terraform | per-env `tfvars` or per-env workspaces, `environments/<env>/main.tf` |
| Cloud-native | `cloudrun.yaml` per-env, ECS task defs per-env, App Runner configs |

## Analytics - trace a metric to its source

When the user says *"where does `monthly_active_users` come from?"*: metric definition (`models/marts/*.sql`, `metrics/`) → semantic layer (`schema.yml` `metrics:`, `lightdash/`, `lookml/`, `cube.js`) → exposures → dashboard YAML (`lightdash/dashboards/`, `metabase/`) → scheduled exports (`dags/`, `cron/`) → notebooks. Report each hop as path + one-liner.
