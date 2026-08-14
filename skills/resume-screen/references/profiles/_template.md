# Profile: \<Role title\>

Blank skeleton. Copy to `references/profiles/<kebab-id>.md`, fill every section, then add a row to [`README.md`](README.md).

## Identity

| Field | Value |
|---|---|
| id | `<kebab-id>` |
| title | `<Role title>` |
| level | `<e.g. mid-level>` |
| company_shape | `<e.g. small/fast product company — not a specific employer>` |

One paragraph: what this person owns in the first year. No company names.

## Factor slots

Keep seven slots that sum to 100. Relabel only if this role cannot honestly use the DPE names; if you relabel, pass the same list as JSON `factors` to `write-scorecard.py`.

| Id | Max | Meaning for this role |  high / mid / low signals |
|---|---|---|---|
| `Pipelines_25` | 25 | | |
| `CoreStack_20` | 20 | | |
| `Cloud_15` | 15 | | |
| `Extras_10` | 10 | | |
| `Band_10` | 10 | | |
| `Location_10` | 10 | | |
| `FactIntegrity_10` | 10 | Use the shared fact-check mapping unless this role has an extra integrity signal | |

## Layer 1 — role wording

Rewrite the five knockout *tests* for this role. Do not add a sixth knockout without updating `references/scorecard.md` and the Scorecard sheet.

| # | Shared slot | Fires when (this role) |
|---|---|---|
| 1 | Missing required languages / core tools | |
| 2 | Under ~3 years *relevant* | Define "relevant" |
| 3 | Missing required platform / domain system | |
| 4 | Cannot meet hours/location (resume must say so) | Usually unchanged |
| 5 | Material fact-check fail | Usually unchanged |

Waiver: High `Startup_fit` + knockout #2 only → flag, do not promote to P1.

## Band

Sweet spot: `<years and level>`. What "clearly above band" looks like for a mid-level product-company seat (signals only — no compensation questions in `Screen_questions`).

## Location and hours

How to read the JD into `Location_10`. Unknown stays mid-band. Knockout only on an explicit cannot.

## Startup / small-company fit

| `Startup_fit` | Signals |
|---|---|
| High | |
| Medium | |
| Low | |

Low + raw P1 → `Fit_decision=Cap P1 → P2`. Leave `Total` alone.

## Screen-question themes

3–5 technical themes for P1/P2/waiver. No hybrid, timezone, salary, visa, or "show me the cert."
