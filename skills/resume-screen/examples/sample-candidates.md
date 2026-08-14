# Sample candidates (fictional archetypes)

Four rows that exercise the engine. Names, employers, and URLs are invented. Use them to check scoring — not as a real slate.

Operator-supplied resume files for this packet are the fictional markdown files under `resumes/`. The `File` column hyperlinks to those paths — not an extracted dump name.

---

## 1. P1 — Jordan Hale

**File:** `resumes/jordan-hale.md`  
**Archetype:** 4–5 years data engineering, warehouse + dbt + Airflow, LinkedIn matches, High/Medium small-company fit.

**Resume claims (fake):** Data Engineer at a 80-person product company (2022–present) and a smaller startup before that. Python, SQL, Snowflake, dbt, Airflow, AWS Lambda, Terraform. LinkedIn `https://example.com/in/jordan-hale` matches titles and dates. GitHub `https://github.com/example/jordan-hale` has dbt project + DAG snippets. Credly badge URL for SnowPro Core loads.

**Score (illustrative):**

| Factor | Pts | Why |
|---|---|---|
| Pipelines_25 | 22 | Production dbt + Airflow, quality checks named |
| CoreStack_20 | 18 | Daily Python/SQL, Snowflake depth |
| Cloud_15 | 13 | AWS + Lambda + Terraform + GitHub Actions |
| Extras_10 | 7 | Small Streamlit ops app |
| Band_10 | 9 | ~4.5y relevant, mid-level IC |
| Location_10 | 8 | Resume silent on hybrid; not a cannot |
| FactIntegrity_10 | 9 | Verified — LI + badge + GitHub align |
| **Total** | **86** | `=SUM(H:N)` |

- Knockouts: none
- Claim_feasibility: Credible · Company_type: scaleup · Startup_fit: High · Fit_decision: Holds
- Fact_check: Verified · Waiver: No
- Tier / Decision: **P1 / Advance**
- Screen_questions: pipeline failure/backfill; dbt promotion + Snowflake grants; Airflow idempotency

---

## 2. P1 → P2 cap — Morgan Ellis

**File:** `resumes/morgan-ellis.md`  
**Archetype:** High skill score, enterprise specialist, Low small-company fit, likely above a mid-level product-company band.

**Resume claims (fake):** 11 years, current title "Lead Data Architect" at a global bank. Deep Snowflake, dbt Cloud, Control-M (not Airflow), Ab Initio heritage, large platform PMO. LinkedIn `https://example.com/in/morgan-ellis` matches. No GitHub. SnowPro Advanced badge URL verifies.

**Score (illustrative):**

| Factor | Pts | Why |
|---|---|---|
| Pipelines_25 | 24 | Heavy production platform, strong quality/governance |
| CoreStack_20 | 19 | Expert SQL/Python/Snowflake |
| Cloud_15 | 14 | AWS + Terraform at bank scale |
| Extras_10 | 6 | Internal portals; no small-app hats |
| Band_10 | 4 | Clearly above mid-level product-company band |
| Location_10 | 8 | Silent; not a cannot |
| FactIntegrity_10 | 9 | Verified |
| **Total** | **84** | Unchanged by the cap |

- Knockouts: none
- Claim_feasibility: Credible · Company_type: enterprise · Startup_fit: **Low**
- Fit_decision: **Cap P1 → P2** (enterprise specialist / band mismatch)
- Fact_check: Verified · Waiver: No
- Tier / Decision: **P2 / Maybe** — raw math is P1; overlay caps the tier only
- Screen_questions: how they would own ingest+dbt+on-call without a PMO; what they would drop from bank process; a concrete backfill they ran themselves

---

## 3. Out — contradiction — Riley Chen

**File:** `resumes/riley-chen.md`  
**Archetype:** LinkedIn title/employer contradicts a resume rewritten as data engineering (SWE → DE).

**Resume claims (fake):** "Senior Data Engineer" at Northwind Apps 2021–2026; Python, SQL, Snowflake, dbt, Airflow. LinkedIn `https://example.com/in/riley-chen` lists **Software Engineer** at a different employer (Globex Retail) for those same dates; no warehouse, no dbt. GitHub is a Java Spring monorepo.

**Score (illustrative):**

| Factor | Pts | Why |
|---|---|---|
| Pipelines_25 | 10 | Resume claims DE; public work does not |
| CoreStack_20 | 12 | SWE Python/SQL; no warehouse evidence on LI |
| Cloud_15 | 8 | Generic AWS on resume only |
| Extras_10 | 4 | Unrelated Java services |
| Band_10 | 6 | Years exist but not in this role |
| Location_10 | 8 | Silent |
| FactIntegrity_10 | 0 | Contradicted |
| **Total** | **48** | Still filled |

- Knockouts: **Material fact-check fail** (LinkedIn title/employer contradict the resume)
- Claim_feasibility: Implausible · Company_type: IT-services · Startup_fit: Low
- Timeline_consistency: Breaks · Fact_check: **Contradicted**
- Tier / Decision: **Out / Out**
- Screen_questions: *(empty — not P1/P2/waiver)*

---

## 4. Waiver — Avery Kim

**File:** `resumes/avery-kim.md`  
**Archetype:** ~1 year relevant, but real GitHub and end-to-end hats. Out on years only. High small-company fit.

**Resume claims (fake):** 14 months as the only data hire at a 12-person startup. Built ingest → Snowflake → dbt → a Dagster schedule → a Streamlit ops page. Python + SQL throughout. LinkedIn `https://example.com/in/avery-kim` is thin (no Licenses tab — **not** a contradiction). GitHub `https://github.com/example/avery-kim` shows the repo. No certs.

**Score (illustrative):**

| Factor | Pts | Why |
|---|---|---|
| Pipelines_25 | 16 | Real end-to-end, short production history |
| CoreStack_20 | 15 | Python+SQL+Snowflake in one owned path |
| Cloud_15 | 11 | AWS + some Terraform, CI on GitHub |
| Extras_10 | 8 | Streamlit + API the team actually uses |
| Band_10 | 3 | Well under mid-level years |
| Location_10 | 9 | Resume states hybrid HQ overlap |
| FactIntegrity_10 | 9 | Partial/strong GitHub; LI thin but consistent |
| **Total** | **71** | |

- Knockouts: **Under ~3 years of actual data/platform/cloud engineering**
- Claim_feasibility: Credible · Company_type: startup · Startup_fit: **High**
- Fact_check: Partial · Waiver: **Yes — years knockout only; High small-company fit. Do not promote Out → P1**
- Tier / Decision: **Out / Waiver candidate**
- Screen_questions: how they backfilled a bad load alone; dbt + Snowflake clone for review; what they would add at month 18 for quality/on-call
