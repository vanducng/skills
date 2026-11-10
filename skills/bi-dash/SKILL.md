---
name: bi-dash
description: "Builds a BI dashboard the way it gets trusted: a question sheet before any chart, an HTML mockup on synthetic data signed off by the asker, a field map that flags missing fields and columns with two candidates, every KPI reconciled to a reference within a stated tolerance, then the build in the repo's BI tool skill, UAT and a metric glossary. Tool-neutral. Use when the user says 'build a dashboard', 'new dashboard for', 'BI dashboard', 'KPI dashboard', 'reporting dashboard', 'mock up the dashboard', 'do we have the data for this dashboard', 'check the dashboard numbers' or 'is the dashboard ready to publish'. Not for a one-off number (answer it with a query), the tool's own chart syntax (the repo's BI tool skill) or modeling pipelines (data engineering)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# bi-dash

A dashboard fails quietly: it answers a question nobody asked, reads the wrong column, or disagrees with the number people already trust. Each stage has a gate and a file that proves it. Never pass a gate on a guess.

## When not to use it

A one-off number ("how many orders last week?") is a query: answer with the number, its definition and the period. No question sheet, no mockup, no dashboard talk.

## The gates

| # | Stage | Seat | Proof (file) | Gate |
|---|---|---|---|---|
| 1 | Information needs | lead with the asker | `question-sheet.md` ([template](references/question-sheet.md)) | Every row has an audience, a decision and a metric definition from the asker |
| 2 | Mockup | `dev.design` | HTML mockup on synthetic data; each chart names its sheet row | No chart without a row |
| 3 | Sign-off | human | The asker's yes, recorded in the slice record | Stakeholder messages are drafts for the operator to approve, never sent |
| 4 | Data availability | `dev.build` | `field-map.md` ([template](references/field-map.md)) | No `missing` row and no unchosen `variant` |
| 5 | Data validation | `dev.build` | `reconciliation.md` (below) | Every KPI inside its tolerance |
| 6 | Data engineering | `dev.build` | Models built in dev, tested, then published; each metric defined once in the semantic layer | Model tests pass |
| 7 | Build | `dev.build` | Dashboard as code, in the repo's BI tool skill; every metric carries its description | Follows [chart rules](references/chart-rules.md) |
| 8 | UAT | `dev.qa` | [UAT checklist](references/uat-checklist.md) with a real-data screenshot per sheet row | Design fidelity 9 or more against the mockup |
| 9 | Document | `dev.build` | Metric glossary: definition, source, logic, owner, refresh | Docs move with the change |

## Rules

1. **Start with the question sheet, not a chart.** On "build a dashboard for X", write `question-sheet.md` from the template, fill what the data shows, put `?` in every cell only the asker can answer, and ask for the audience and the decision each question supports. Build nothing else until they answer.
2. **Mock up on synthetic data, in HTML.** No real rows in a mockup, no generated images. Each chart's caption names its sheet row.
3. **Map every field before building.** Write `field-map.md` from the template, even when the ask is only "do we have the data?": the file is the answer and the proof. For each field the mockup shows, the `model.column`, marked `exists`, `variant` (two or more candidate columns, for example a UTC timestamp and a local date, or two geography columns) or `missing`. Profile each column you map: nulls, outliers, and duplicate spellings of one value. A `variant` needs a recorded choice and its reason; a `missing` field goes back to the asker (drop the chart or source the data). Flag both in the reply too.
4. **Reconcile before anyone sees a number.** Compare each KPI with a reference people already trust: a source-system count or a prior report. Write `reconciliation.md`:

   | KPI | Ours | Reference (source) | Gap % | Tolerance | Result |
   |---|---|---|---|---|---|

   Gap % is (ours - reference) / reference. Agree the tolerance with the metric owner; when none is set, use 1% for counts and sums and say it is a default. A gap outside the tolerance is a fail: the dashboard is not ready, whatever the other tiles say. Report the gap, the tolerance and the causes to check (filters, time zone, test or cancelled rows, late data). Send the asker a sample.
5. **Build in the repo's own tool,** as code, with the repo's BI tool skill. Define each metric once in the semantic layer, with a description.
6. **UAT on real data,** against the time-to-read budget in the sheet. A real-data screenshot answers each sheet row, and the numbers match `reconciliation.md`.
7. **Done includes the glossary:** every metric's definition, source, logic, owner and refresh cadence.

## Seats and board

On a workshop rig, `dev.build` writes the field map, reconciliation, models and dashboard; `dev.qa` runs UAT; `dev.review` reads the diff. The mockup is `dev.design`'s: the workshop has no design seat, so add one with `rig add` or let `dev.build` draw it. For the sign-off, put the question sheet and the mockup on the slice card of the tracking board (`sheet` and `mockup` links), so the asker approves both from one place.
