# Profile: Data Platform Engineer

Generic mid-level data/platform engineer at a small or fast product company. Not tied to a real employer.

## Identity

| Field | Value |
|---|---|
| id | `data-platform-engineer` |
| title | Data Platform Engineer |
| level | Mid-level (~3–7 years relevant) |
| company_shape | Small / fast product company: few platform owners, production models, visible on-call |

They own ELT into a cloud warehouse, transformation (usually dbt), scheduling, quality, and enough AWS/IaC/CI to keep the path out of a ticket queue. They are not a BI-only analyst, not a Java platform specialist who has never shipped a table, and not a staff-aug mill resume that lists the same stack on every client.

## Factor slots

Default engine ids. Weights sum to 100.

| Id | Max | High | Mid | Low |
|---|---|---|---|---|
| `Pipelines_25` | 25 | Shipped ELT/ETL; dbt models in production; Airflow/Dagster/Prefect or equivalent; tests/freshness/quality that someone else relies on | Built jobs or models but thin on orchestration or quality | Dashboarding, one-off SQL, or "exposed to" Airflow |
| `CoreStack_20` | 20 | Daily Python **and** SQL; warehouse depth (Snowflake or BigQuery/Redshift/Databricks/Synapse) — warehouses, roles, incremental models, not "used the UI" | One of Python/SQL is strong, warehouse is real but shallow | SQL-only analyst, Python scripts with no warehouse, or warehouse name-drop |
| `Cloud_15` | 15 | AWS (or the JD cloud) plus at least two of: Lambda/functions, Terraform/IaC, Git-hosted CI/CD that deploys data jobs | Cloud console + some Git; IaC or CI mentioned once | No cloud, or "EC2" with no data path |
| `Extras_10` | 10 | Internal apps (Streamlit/Flask), APIs, Docker/K8s, or warehouse AI/LLM features actually shipped | One extra, thin | None, or cert-study only |
| `Band_10` | 10 | ~3–7 years relevant; scope matches a mid-level IC (owns a domain, not a 40-person platform org) | Slightly under/over (2.5–3y with real hats, or 8–10y still hands-on) | <2y relevant, or clearly a principal / enterprise architect / above a mid-level product-company band |
| `Location_10` | 10 | Resume supports the JD hours/location (or prior hybrid/remote in that pattern) | Silent or city-only — use 6–8, not a knockout | Resume says they cannot meet the JD (also knockout #4) |
| `FactIntegrity_10` | 10 | Shared mapping: Verified 9–10, Partial 6–8, Unverified 3–5, Contradicted 0 | | |

## Layer 1 — role wording

| # | Fires when |
|---|---|
| 1 | Missing **Python** or **SQL** as a skill used in work (not a single course line) |
| 2 | Under ~3 years of **data / platform / cloud engineering**. Analyst-only, QA-only, and Tableau/Looker-only years do not count. Software engineering counts only when the work was data platform, pipelines, or warehouse |
| 3 | No cloud warehouse in actual work: Snowflake **or** BigQuery / Redshift / Databricks / Synapse |
| 4 | Resume clearly says they cannot work the JD's hours or location. Unknown is not a knockout |
| 5 | LinkedIn/GitHub contradicts employer, title, dates, or stack (see `../fact-check.md`) |

Waiver: knockout #2 only + `Startup_fit=High` → `Waiver=Yes — years knockout only; High small-company fit. Do not promote Out → P1`.

## Band

Sweet spot: mid-level, about 3–7 years relevant, compensation and scope in line with a product-company IC (the sample JD uses a mid-level ~$80–100k band as an *example*, not a rule).

Lose `Band_10` when:

- Relevant years are well under 3 (the years knockout will also fire)
- Recent titles are Staff/Principal/Architect in a large platform org, or the resume signals they will not take a mid-level product-company seat

Do **not** ask "does this band work?" in `Screen_questions`. Encode the doubt in `Band_10`, `Startup_fit`, and `Fit_decision`.

## Location and hours

Read the JD first. Unknown city or no hours line → 6–8 on `Location_10`. Knockout #4 only on an explicit cannot (wrong country with "cannot relocate", "evenings only" vs a daytime hybrid JD, etc.).

## Startup / small-company fit

| `Startup_fit` | Signals |
|---|---|
| High | Small teams, multiple hats (ingest + model + a bit of app/infra), shipped without a dedicated platform org, evidence of learning speed (public GitHub, side systems, short cycles) |
| Medium | Mix of product-company and larger orgs; some ownership; not a specialist silo |
| Low | Long enterprise specialist path, vendor/staffing mill, identical stack paragraph on every client, or a mill rewrite of the JD |

`Company_type` is the *recent* employer shape. A Low `Startup_fit` on a raw P1 row → `Fit_decision=Cap P1 → P2`, `Tier=P2`, `Total` unchanged.

## Screen-question themes

P1 / P2 / waiver only. Pick 3–5 that poke *this* resume's claims:

1. A pipeline they owned: failure modes, backfills, SLAs
2. dbt (or equivalent) promotion: envs, grants, what a clone/zero-copy pattern is for
3. Warehouse operations: warehouses vs roles, cost, concurrency
4. Orchestration: idempotency, sensor vs schedule, poison messages
5. If certs are unverified — a technical Snowflake / Databricks / AWS probe from `../fact-check.md`, never "show the badge"
6. If extras claim Streamlit/APIs/K8s — ask for the production path, not the tutorial

No hybrid, timezone, salary, visa, or band-acceptance questions.
