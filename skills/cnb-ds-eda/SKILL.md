---
name: cnb-ds-eda
description: Build evidence-backed exploratory analysis and GitHub-renderable notebook reports in `/Users/vanducng/git/work/cnb/cnb-ds-eda`. Use when the user asks for CNB EDA notebooks, Snowflake-backed analysis, Retell or Transfer AI investigations, data-contract-derived report logic, notebook refreshes, or report artifacts under `notebooks/`.
---

# CNB DS EDA

Use this skill to produce analysis that a stakeholder can read directly in GitHub and that another analyst can refresh from the warehouse.

## Workflow

1. Start in `/Users/vanducng/git/work/cnb/cnb-ds-eda` unless the user gives another checkout.
2. Inspect existing notebook patterns before editing. Prefer `notebooks/rnd_disconnection_status/`, `notebooks/lead_age_performance/`, and related topic folders over inventing a new structure.
3. Translate relative date requests into exact `America/New_York` report boundaries. State `start_date`, `end_exclusive`, and the inclusive last data date in the notebook.
4. Put runnable SQL in `notebooks/<topic>/queries/`. Put committed offline snapshot tables in `notebooks/<topic>/snapshots/` when GitHub rendering or offline review matters.
5. Use `src/connectors/snowflake.py::query_snowflake()` for live refresh paths. Use `vd:miudb` only when the user explicitly asks for that workflow or when the connector is insufficient.
6. When the user mentions data contracts, inspect the source YAML under `/Users/vanducng/git/work/cnb/cnb-data-contract/contracts/constraints/snowflake/` and mirror the business predicates in the analysis SQL.
7. Keep notebook code cells compact. Do not embed large TSV/CSV payloads inside code cells; load snapshot files instead.
8. Execute the notebook in-place before sharing or pushing when the user wants GitHub preview. Commit rendered outputs and PNG-backed Plotly figures.
9. Validate before handoff: `jq empty <notebook>`, `jupyter nbconvert --execute`, `jupyter nbconvert --to html`, and the repo test/lint commands that apply.

## Report Shape

Start the notebook with:

- objective and exact snapshot/report window
- table of contents
- definitions and detection rules
- data sources and contract references
- a compact data-loading cell

Then present the analysis from broad to specific:

- total population and ratios
- trend over time
- company and agent concentration
- lead/app/status/worklist distribution
- bounded redacted samples
- conclusion, root cause, and fix/monitor recommendation

## References

- Read `references/repo-map.md` for repo paths, validation commands, and file placement.
- Read `references/notebook-report.md` before creating or reshaping a notebook report.
- Read `references/snowflake-contract-analysis.md` before writing SQL from Retell, Transfer AI, Tenstreet, or data-contract logic.
