# Role profiles

A profile is the role-specific scorecard. The skill, the engine (`../scorecard.md`), the fact-check rules, and the Excel shape stay shared.

## Index

Add one row when you add a profile. `SKILL.md` defaults to the row marked `yes`.

| id | file | title | default |
|---|---|---|---|
| `data-platform-engineer` | [`data-platform-engineer.md`](data-platform-engineer.md) | Data Platform Engineer | yes |

## How to add a profile

1. Copy [`_template.md`](_template.md) to `references/profiles/<kebab-id>.md`.
2. Fill every section: who the role is, Layer 1 wording, the seven factor rubrics, band, location/hours reading, startup-fit signals, and screen-question themes.
3. Keep the **seven slots** and a 100-point `Total`. You may relabel a slot (e.g. `Pipelines_25` → `Systems_25` for a backend profile) if you say so in the profile and pass a `factors` array into `write-scorecard.py`. Weights must still sum to 100.
4. Add a row to the index table above.
5. Do **not** copy `SKILL.md`, `scorecard.md`, `fact-check.md`, or the writer script. Do **not** put a company name, a real JD, or real candidate data in the profile.

That is the whole change. "Backend Engineer" and "Product Manager" are new files plus a line here.

## What belongs in a profile vs the engine

| Lives in the profile | Lives in the shared engine |
|---|---|
| What "relevant years" means for this role | The ~3 year knockout *structure* and the waiver flag |
| What a 25 / 12 / 0 looks like on each factor | The seven slots and `=SUM(H:N)` |
| Band sweet spot (e.g. mid-level 3–7) | `Band_10` as a factor that does not rewrite `Total` |
| Startup / small-company fit signals for this work | Overlay values and the P1 → P2 cap rule |
| Technical screen themes | The ban on HR logistics in `Screen_questions` |
| Warehouse / language must-haves for this role | Knockout #1–#5 *slots* |

If two roles need different *columns* (not just labels), that is an output-spec change, not a second skill.
