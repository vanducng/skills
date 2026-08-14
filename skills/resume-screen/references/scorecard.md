# Shared scoring engine

This file is the engine. A role profile fills in *what each factor means* and may tighten a knockout; it does not fork the layers, the 100-point `Total`, or the tier math.

`Total` is always the sum of the seven Layer 2 cells. Overlays never change that number.

Default factor ids and weights (Data Platform Engineer; other profiles may relabel the same seven slots as long as weights still sum to 100):

| Slot | Id | Max |
|---|---|---|
| 1 | `Pipelines_25` | 25 |
| 2 | `CoreStack_20` | 20 |
| 3 | `Cloud_15` | 15 |
| 4 | `Extras_10` | 10 |
| 5 | `Band_10` | 10 |
| 6 | `Location_10` | 10 |
| 7 | `FactIntegrity_10` | 10 |

Excel: after `Rank, Name, File, Tier, Decision, Total, Knockouts` those seven land in `H`–`N`, so `Total` is `=SUM(H{row}:N{row})`.

## Layer 1 — knockouts

Any one knockout sets `Tier=Out` and a short reason in `Knockouts`. **Still fill every Layer 2 score and every overlay.**

Apply the profile's wording. The default (DPE) knockouts:

| # | Knockout | When it fires | When it does not |
|---|---|---|---|
| 1 | Missing Python or SQL | Resume shows neither as a used skill (course-only mention with no work evidence counts as missing) | One is thin but both appear in real work |
| 2 | Under ~3 years relevant | Fewer than ~3 years of *data / platform / cloud engineering*. Analyst-only, QA-only, or Tableau-only time does not count | Adjacent engineering that clearly owned pipelines, warehouses, or platform |
| 3 | No cloud warehouse | No Snowflake, BigQuery, Redshift, Databricks, or Synapse in actual work | Warehouse named only as a future interest |
| 4 | Cannot meet hours/location | Resume **clearly states** they cannot work the JD's hours or location | Unknown, silent, or "open to discuss". Do not infer from a current city alone |
| 5 | Material fact-check fail | Employer, title, dates, or stack on LinkedIn/GitHub **contradicts** the resume | Missing LinkedIn, missing Licenses tab, or unverified certs (those hit `Fact_check` / `FactIntegrity_10`, not this knockout, unless the public page contradicts) |

Multiple knockouts: list them all, semicolon-separated.

**Waiver exception (flag only):** knockout #2 alone **and** `Startup_fit=High` → set `Waiver` to `Yes — years knockout only; High small-company fit. Do not promote Out → P1`. Tier stays `Out`. `Decision` is `Waiver candidate`.

## Layer 2 — 100 points

Score each factor 0–max using the profile rubric. Use the full range; a 25 that is always 20 or 0 is a broken rubric.

| Id | What it rewards (DPE default; profile may specialize) |
|---|---|
| `Pipelines_25` | ELT/ETL, dbt, Airflow or similar, data quality, models actually in use |
| `CoreStack_20` | Python + SQL, Snowflake or equivalent warehouse depth |
| `Cloud_15` | AWS (or the JD cloud), Lambda, Terraform/IaC, Git + CI/CD |
| `Extras_10` | Streamlit or internal tools, APIs, Docker/K8s, warehouse AI/LLMs |
| `Band_10` | Sweet spot mid-level ~3–7 relevant years. Too junior **or** clearly priced / leveled above a mid-level product-company band loses points |
| `Location_10` | Evidence they can meet the JD hours/location. Unknown → mid-band (typically 6–8), not zero. Clear "cannot" → 0 and knockout #4 |
| `FactIntegrity_10` | `Verified` 9–10; `Partial` 6–8; `Unverified` 3–5; `Contradicted` 0 (and knockout #5) |

`Band_10` is about **level fit**, not a second years knockout. A 12-year principal who looks above a mid-level product-company band scores low here and may also get `Startup_fit=Low`; they are not Out on years.

## Overlays

Overlays are recorded columns. They must not be added into `Total`.

| Overlay | Values | Rule |
|---|---|---|
| `Claim_feasibility` | `Credible` \| `Stretched` \| `Implausible` | Implausible usually pairs with `Contradicted` or a mill rewrite. Stretched = ambitious but possible (title inflation, mill-ish bullets, stacked certs with no proof) |
| `Company_type` | `startup` \| `scaleup` \| `mid-market` \| `enterprise` \| `IT-services` \| `staffing/vendor` | Dominant recent employer type, not the oldest logo |
| `Startup_fit` | `High` \| `Medium` \| `Low` | Speed, learning, multiple hats, small/fast product-company fit. Enterprise specialist / mill resume / staff-aug vendor path → Low |
| `Fit_decision` | short prose | If `Startup_fit=Low` **and** the raw tier would be P1, write `Cap P1 → P2` and set `Tier=P2`. Do not change factor cells or `Total` |
| `Timeline_gaps` | free text | Name gaps >6 months or overlapping jobs; `None noted` if clean |
| `Timeline_consistency` | `Holds` \| `Soft mismatch` \| `Breaks` | Resume vs LinkedIn/GitHub dates. `Breaks` with a material employer/title/date clash → knockout #5 |
| `Years_relevant` | number | Counted per the profile (DPE: data/platform/cloud engineering only) |
| `Fact_check` | `Verified` \| `Partial` \| `Unverified` \| `Contradicted` | See `fact-check.md` |
| `Waiver` | `No` or `Yes — …` | Only the years-knockout + High fit case above |
| Cert columns | see `output-spec.md` | Claimed / verified-with-URL / unverified / notes |
| `Screen_questions` | 3–5 questions | **P1, P2, and waiver only.** Technical. No hybrid, timezone, salary, or "does this band work" |

## Tiers

Compute a *raw* tier from `Total` + `Fact_check`, then apply overlay caps. `Total` here means the arithmetic sum of the seven factors (the same value the Excel formula will show).

| Tier | `Decision` | When |
|---|---|---|
| `P1` | `Advance` | `Total >= 75` **and** `Fact_check` is `Verified` or `Partial`, and no Low-fit cap |
| `P2` | `Maybe` | `Total` in 55–74, **or** `Total >= 75` but `Fact_check=Unverified`, **or** P1 capped by `Startup_fit=Low` |
| `P3` | `Hold` | `Total` in 40–54 and no knockout / not `Contradicted` |
| `Out` | `Out` or `Waiver candidate` | Any knockout, or `Fact_check=Contradicted`, or `Total < 40` |

Boundaries: 75 and 55 and 40 are inclusive on the higher tier (`75` is P1, `55` is P2, `40` is P3).

Sort the sheet: P1, P2, P3, waiver-Out, other Out. Within a group, higher `Total` first, then name.
