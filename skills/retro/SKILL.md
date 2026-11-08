---
name: retro
description: "Learns from finished or failed work and fixes the cause at the highest layer that holds: architecture or types, then a script or lint, then a test, and prose last. Runs only on a trigger: slice close (one retro line), an escape after merge, a finding class seen twice, a review past round 3, or the weekly rollup. Counts review outcomes from the verdict files. Use when asked to 'retro', 'what did we learn', 'post-mortem', 'why did this escape', 'close the slice', 'weekly rollup' or 'journal this'. One finding seen once is a note, never a rule."
license: MIT
argument-hint: "[close | escape | weekly] [record dir...]"
metadata:
  author: vanducng
  version: "0.1.0"
---

# retro

Retro turns what went wrong into something that stops it recurring, and stays silent otherwise.

`O=<this skill's directory>/scripts/outcomes.cjs`

## Triggers

| Trigger | Output |
|---|---|
| Slice close | one line in `PROGRESS.md`: `- <UTC time, YYYY-MM-DDTHH:MMZ>: retro: <what escaped or cost a round, or none>` |
| An escape (a bug found after merge), a review past round 3, or a finding class in two places | the full retro below |
| Weekly rollup | `node "$O" <every record closed this week>`, the counts, and the full retro for each repeated class |

No trigger, no retro: write nothing and say why.

## Full retro

1. **Count:** `node "$O" <record dir>...` prints rounds, rounds to pass, findings by tag and status, and repeated finding texts. Judge near-duplicates yourself.
2. **Name the class** of failure in one line, not the instance: "an empty input is never tested", not "F1 in cart.js".
3. **Twice, not once.** One evidence row is a note: one line in the record's PROGRESS.md. Two or more rows make it a fix.
4. **Fix at the highest layer** that would have caught it:

| Layer | Example |
|---|---|
| Architecture or types | make the wrong state impossible |
| Script or lint | a check that fails the build |
| Test or eval | the past case, kept as a regression |
| Prose | one sentence in a skill or `AGENTS.md`, last resort |

5. **Ship the case with the fix:** a new check or eval includes the past case, proving it catches it.
6. **Propose; never land a merge-blocking check alone.** A check that blocks merges needs a lead or operator yes. From two rows up, write the proposed rule-table row (rule, enforced by) into `reports/retro.md`; the `AGENTS.md` owner applies it.
7. **Record:** the retro line and a link to `reports/retro.md` in `PROGRESS.md`.

## Journal

For a personal "what I learned" entry, write `reports/journal-<YYYYMMDD-HHMM>-<slug>.md` in the record: what happened, the decision, what to do next time. A journal, not a rule.

## Rules

- **Evidence rows only:** a verdict finding, a reverted commit, an escaped bug. A feeling is not a row.
- **Never edit an old verdict or record** to make the counts look better.
