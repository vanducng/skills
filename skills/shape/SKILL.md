---
name: shape
description: "Shapes a work item's record before it is built: the intent in plain words, numbered mini-requirements anyone can check, and a checkbox proof contract, in the record's SPEC.md. A thin router: --grill walks an existing plan one question at a time; --options lays out two or three approaches and picks one. Use when asked to 'shape this', 'spec this', 'write the requirements', 'what is the proof contract', 'grill me', 'stress-test this plan', 'what are our options', 'how should we approach this', or 'plan the build'. Long multi-session decision maps stay with vd:interview --wayfinder."
license: MIT
argument-hint: "[--grill | --options] [record dir]"
metadata:
  author: vanducng
  version: "0.2.0"
---

# shape

The second gate. A record leaves it with an intent, mini-requirements and a proof contract a reviewer can check without asking you. It does not build.

**The record:** in an OpenRig rig, the slice folder. Elsewhere, the bench record the workbench skill resolves (`records.cjs resolve`).

## Modes

| Mode | When | Reads | Writes |
|---|---|---|---|
| default | the record exists, and its requirements or contract are thin or missing | `references/sequencing.md` when the build takes more than one sitting | `SPEC.md`, plus `PROGRESS.md` `## Plan` if sequenced |
| `--grill` | a plan or idea exists and has to be stress-tested | `references/grill.md` | nothing until the answers are in, then `SPEC.md` |
| `--options` | the approach is not obvious | `references/options.md` | `reports/options.md` |

## Default steps

1. **Read the record.** If `SPEC.md` already meets steps 2 to 6, change nothing: say it is ready and name the next gate (build, then `vd:code-review` and `vd:verify`).
2. **Intent:** one or two sentences in plain words: who gets what, and why.
3. **Mini-requirements:** numbered, observable, testable outcomes ("`total()` counts a repeated coupon once"), not tasks ("refactor cart"). Each one maps to a contract line, its success check.
4. **Proof contract:**
   - keep what intake wrote; none there, build the lines from the single source: `node <intake>/scripts/contract.cjs <type>`;
   - make every line concrete: name the test, the surface or the number;
   - add the door type (one-way: hard to undo, such as data or a public API; two-way: a revert undoes it), the blast radius and the undo step if missing.
5. **States,** only when the frontmatter names the `statechart` lens. With `vd:statechart`:
   - for work on existing code, two charts: **today**, modeled from the code, in `reports/statechart/today/`, and **intended**, from the rules, in `reports/statechart/intended/`; new work gets the intended chart only;
   - each rule is a numbered mini-requirement ending `(invariant)` and an `INVARIANT` of the intended model. A rule the ask states is approved; ask the reader before adding any other;
   - one contract line per invariant and per bug path the today chart marks, each a test that fails on today's code and passes after the change;
   - the charts' paths in `SPEC.md`, under `## States`.
6. **Out of scope:** one line, so the reviewer knows what not to ask for.
7. **Frontmatter, when intake left none:** `id`, `type`, `intent`, `depends_on` (the slices this waits on).
8. **Territories:** when the build spans repos, one worktree per repo and one PR by default. Name them here.
9. **Check:** no `TODO` is left. The record must pass `rig scope audit` in a rig, or the workbench `check` elsewhere.

## Rules

- **Never invent a requirement the ask does not support.** If one is needed, ask one question and give your best guess with it.
- **One question at a time,** in every mode.
- **Shape writes the record only.** Code, plans in new files and prototypes are out of scope; the statechart model and charts under `reports/statechart/` are part of the record.
