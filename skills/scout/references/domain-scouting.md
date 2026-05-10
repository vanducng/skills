# Domain Scouting Playbooks

Concrete search-target recipes for non-software disciplines. Use these as the **prompt body** for Explore / Gemini agents.

The general loop (analyze → divide → spawn → aggregate) is in `SKILL.md`. This file is just *what to look for* per domain.

---

## Data engineering

### Trace a source through the lakehouse

When the user says *"what depends on `payments_raw`?"*:

| Layer | Where to look | Grep targets |
|---|---|---|
| Sources | `**/schema.yml`, `**/sources.yml` | `name: payments_raw`, `source('...payments_raw')` |
| Staging | `models/staging/` | `from {{ source(` referencing payments |
| Intermediate / marts | `models/intermediate/`, `models/marts/` | `ref('stg_payments')`, downstream `ref()` chain |
| Tests | `models/**/schema.yml`, `tests/` | `tests:` blocks, `tests/*.sql` mentioning the model |
| Macros | `macros/` | macros invoked by payments models |
| Snapshots / seeds | `snapshots/`, `seeds/` | `unique_key`, seed CSVs |
| Orchestration | `dags/`, `workflows/`, `pipelines/`, `prefect*/` | DAG that runs `dbt run --select +payments` |
| BI exposures | `models/**/schema.yml` (`exposures:`), `lightdash/`, `lookml/` | `exposures:` block, dashboard YAML |

### Trace a freshness or schema-drift incident

| Search | Why |
|---|---|
| `dbt source freshness` configs in `schema.yml` | What freshness SLA was set |
| Recent edits to `schema.yml` for that source | Schema change candidates |
| `on_schema_change:` in model configs | Whether the model auto-evolves |
| Latest run logs in `target/run_results.json`, `target/manifest.json` | Last successful run, last failure |
| DAG schedule (Airflow / Dagster / Prefect) | Expected cadence |

### Pipeline tooling — common surfaces

| Tool | Search hints |
|---|---|
| **Airflow** | `dags/*.py`, `from airflow`, `DAG(`, `@task`, `airflow.cfg`, `*.airflowignore` |
| **Dagster** | `@asset`, `@op`, `@job`, `Definitions(`, `dagster.yaml`, `workspace.yaml` |
| **Prefect** | `@flow`, `@task`, `prefect.yaml`, `deployments/` |
| **dbt** | `dbt_project.yml`, `profiles.yml`, `models/`, `macros/`, `target/manifest.json` |
| **Spark / PySpark** | `SparkSession`, `pyspark.sql`, `*.scala`, `*.py` jobs, `spark-defaults.conf` |
| **Kafka / Pub/Sub** | `bootstrap.servers`, `topic`, `subscription`, schema registry refs |
| **dlt / Meltano / Singer** | `dlt.pipeline`, `meltano.yml`, `tap-*`, `target-*`, `state.json` |

---

## DevOps / infrastructure

### Map an environment variable across the stack

When the user says *"where is `DATABASE_URL` set in staging?"*:

| Layer | Where | Search target |
|---|---|---|
| App config | `config/`, `src/config/`, `.env*` | `DATABASE_URL` literal |
| Container | `Dockerfile*`, `docker-compose*.yml` | `ENV DATABASE_URL`, `environment:` blocks |
| Orchestration | `k8s/`, `helm/`, `kustomize/` | `env:`, `valueFrom: secretKeyRef`, ConfigMap entries |
| Helm values | `values*.yaml` | `database.url`, env-specific overrides (`values-staging.yaml`) |
| IaC | `terraform/`, `pulumi/`, `cdk/` | secret-manager outputs, RDS/Cloud SQL connection strings |
| Secret store | `.sops.yaml`, `vault/`, `secrets/`, `*.enc.yaml` | encrypted entries (decrypt only when authorized) |
| CI/CD | `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile` | `env:` injection, secrets refs |
| Runtime | platform-specific (Cloud Run env, ECS task def, K8s Deployment spec) | the *actual* runtime override |

Don't stop at "found it in `.env.example`" — that's the template, not the truth.

### Common surfaces — multi-env

| Layout | Convention |
|---|---|
| Helm | `values.yaml` + `values-<env>.yaml`, sometimes `charts/<svc>/values/<env>.yaml` |
| Kustomize | `base/` + `overlays/{dev,staging,prod}/` |
| Terraform | per-env `tfvars` or per-env workspaces, `environments/<env>/main.tf` |
| Cloud-native | `cloudrun.yaml` per-env, ECS task defs per-env, App Runner configs |

### CI/CD scout

| Goal | Where |
|---|---|
| List all workflows | `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, `azure-pipelines.yml` |
| Find a failing job | `gh run list`, then `gh run view <id> --log-failed` |
| Reusable workflow / actions | `.github/workflows/*-reusable.yml`, `.github/actions/*/action.yml` |
| Deploy step | grep `deploy`, `kubectl apply`, `helm upgrade`, `terraform apply`, `gcloud run deploy`, `aws ecs`, `flyctl deploy`, `wrangler deploy` |
| Secret refs | `${{ secrets.* }}`, `secrets.NAME`, `vault read`, `op://` |

### Container / K8s surfaces

| Need | Search |
|---|---|
| Image build | `Dockerfile*`, `docker-bake.hcl`, `nixpacks.toml`, `Containerfile` |
| Compose stack | `docker-compose*.yml`, `compose.yaml` |
| K8s objects | `kind: Deployment`, `kind: StatefulSet`, `kind: CronJob`, `kind: ConfigMap`, `kind: Secret`, `kind: Ingress`, `kind: Service` |
| Helm charts | `Chart.yaml`, `templates/` |
| Kustomize | `kustomization.yaml`, `overlays/`, `patches/` |
| Service mesh / gateway | `VirtualService`, `Gateway`, `Ingress`, `HTTPRoute` |

### Cloud provider hints

| Provider | Surfaces |
|---|---|
| **AWS** | `terraform/`, `cdk/`, `serverless.yml`, `template.yaml` (SAM), `task-definition.json` (ECS), `appspec.yml` (CodeDeploy) |
| **GCP** | `cloudrun.yaml`, `cloudbuild.yaml`, `app.yaml` (App Engine), `*.tf` with `google_*` resources |
| **Cloudflare** | `wrangler.toml`, `wrangler.jsonc`, `worker-configuration.d.ts`, `_routes.json` |
| **Fly.io** | `fly.toml`, `Dockerfile` |
| **Vercel / Netlify** | `vercel.json`, `netlify.toml`, framework configs |

---

## Data analytics / BI

### Trace a metric to its source

When the user says *"where does `monthly_active_users` come from?"*:

| Layer | Where | Search target |
|---|---|---|
| Metric definition | `models/marts/*.sql`, `metrics/` | the SQL or YAML defining the metric |
| Semantic layer | `models/**/schema.yml` (dbt metrics), `lightdash/`, `lookml/`, `cube.js` | `metrics:`, `measure:`, `dimension:` |
| Exposures | `models/**/schema.yml` (`exposures:`) | dashboards/reports declared as consumers |
| Dashboard YAML | `lightdash/dashboards/`, `looker/`, `metabase/` | chart definitions referencing the metric |
| Scheduled exports | `dags/`, `cron/`, scheduled deliveries config | jobs that send/refresh the metric |
| Notebooks | `notebooks/`, `analyses/`, `*.ipynb` | exploratory references |

### BI tool surfaces

| Tool | Key files |
|---|---|
| **Lightdash** | `*.lightdash.yml`, dbt model `meta:` blocks, `lightdash.yml`, `lightdash/dashboards/` |
| **Looker** | `*.lkml`, `*.view.lkml`, `*.model.lkml`, `*.dashboard.lkml` |
| **Metabase** | exported `*.json` collections, embedded SQL question definitions |
| **Cube.js** | `cube.js`, `model/cubes/*.yml`, `model/views/*.yml` |
| **Superset** | exported `*.yaml` chart/dashboard definitions |
| **Mode / Hex / Hightouch** | API exports, repo-managed YAML if synced |

### Reporting / charting code

| Style | Search |
|---|---|
| Python (matplotlib, plotly, altair) | `import matplotlib`, `plotly.express`, `import altair`, `*.ipynb` |
| JS (Recharts, Chart.js, Apache ECharts, Tremor) | `recharts`, `chart.js`, `echarts`, `@tremor` |
| Streamlit / Gradio / Dash | `streamlit run`, `gradio.Interface`, `dash.Dash(` |

### Data modeling artifacts

| Artifact | Hint |
|---|---|
| ER / lineage diagrams | `docs/`, `*.drawio`, `*.excalidraw`, `mermaid` blocks in markdown |
| Conformed dimensions | `dim_*` tables, `dim_date`, `dim_customer` recurrence |
| Slowly-changing dim | `snapshots/`, `*_history`, `effective_from`/`effective_to` columns |
| Fact tables | `fct_*`, `f_*`, `*_events`, `*_facts` |

---

## Cross-cutting search targets (any domain)

| Need | Quick grep |
|---|---|
| Secrets accidentally committed | `BEGIN RSA PRIVATE KEY`, `aws_access_key_id`, `AKIA[0-9A-Z]{16}`, `xoxb-`, `ghp_`, hardcoded URLs with creds |
| TODO / FIXME / HACK with owners | `TODO\(\w+\):`, `FIXME`, `HACK` |
| Feature flags | `feature_flag`, `growthbook`, `LaunchDarkly`, `Unleash`, `flagsmith` |
| Deprecation markers | `@deprecated`, `# DEPRECATED`, `// DEPRECATED` |
| Pinned versions / lockfiles | `package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, `go.sum`, `Cargo.lock`, `uv.lock` |
