---
name: intake
description: "Turns an incoming ask into a work item before anyone builds: names its work type (greenfield, brownfield entry, feature, bug fix, triage, investigation, refactor, SOP, data engineering, data analysis), restates the intent, and writes the record's SPEC.md with that type's proof contract. Use when a new request, ticket, bug report or question arrives: 'take this', 'new task', 'triage this', 'what kind of work is this', 'start a record for', 'open a slice for'. Not for sharpening a record that already has its intent and contract (vd:shape)."
license: MIT
argument-hint: "<the ask, a ticket, or a bug report>"
metadata:
  author: vanducng
  version: "0.1.0"
---

# intake

The first gate. It decides what kind of work this is and what will prove it done, before anyone designs or builds. It does not plan, design or code.

`C=<this skill's directory>/scripts/contract.cjs`

## Steps

1. **Find the record.**
   - In an OpenRig rig, the record is the slice folder from `rig scope slice create`, created by the lead.
   - Elsewhere, the bench record the workbench skill resolves (`records.cjs resolve --id <id>`), where `<id>` is a short kebab name for the task.
2. **Already shaped?** If its `SPEC.md` already has an authored intent and a proof contract, change nothing. Say it is shaped and stop.
3. **Classify:** pick one work type from `node "$C" --list`.
   - If two types fit, choose by what would prove the work done.
   - If the ask is too thin to tell, ask one question with your best guess, and write nothing.
4. **Write `SPEC.md`:**
   - frontmatter: `id`, `type` (the work type), and `intent` (the ask restated in one or two plain sentences);
   - `## Mini-requirements`: numbered, observable outcomes taken from the ask, nothing invented;
   - `## Proof contract`: the lines from `node "$C" <type>`, made concrete for this ask (name the test, surface or number);
   - one more contract line: door type (one-way or two-way), blast radius, and the undo step.
   No `TODO` lines are left behind.
5. **Rig kind** (only in an OpenRig workspace): feature, bug fix or SOP maps to a rig template through the workspace skill's `rig-kind.cjs`. Name it; the lead launches.
6. **Report:** the work type, the record path, and the open question if there is one. The next gate is `vd:shape`.

## Rules

- The proof comes from the work type. A bug fix is proved by a check that fails on the old code and passes on the new. An investigation is proved by cited claims, each labelled measured, inferred or guess.
- Restate the intent in your own words; never paste the ask.
- One record per ask. Never create a second record for work that already has one.
