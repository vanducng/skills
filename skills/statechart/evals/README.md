# statechart evals

| Scenario | Proves |
|---|---|
| `01-mark-broken-rule` | A described flow is modeled and checked; the broken rule is marked on the chart. |
| `02-chart-from-code` | Today's behavior is charted from code, in the reader's words; the code is left alone. |
| `03-no-states` (clean) | A pure function is declined: no model, no diagram. |

The checks accept only a chart and report written by `scripts/statechart` (a TLC run), not a hand-drawn diagram.

The runs need Node 22.18 or later and TLC: export `TLA2TOOLS` and `JAVA`, or have the pinned mise installs (see SKILL.md, Toolchain).

Baseline cap: a run without the skill has no TLC command and spends its time searching the disk for one. Cap each no-skill run at 5 minutes in the agent wrapper and count a timeout as a fail; it gives the same result for less quota. `run_evals.py` has one timeout per scenario, so the cap lives in the wrapper, not in `scenario.json`.
