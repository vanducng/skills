---
name: create-skill
description: "Writes, tests and fixes agent skills with evals first: a skill is evals/ (3+ scenarios with deterministic pass checks, one clean case) plus a short SKILL.md plus scripts for fragile steps, and a repeated failure is fixed at the highest layer (architecture, types, script, lint, test, then prose). Use when the user says 'create a skill', 'write a skill for X', 'make this a skill', 'my skill never triggers', 'this skill keeps failing', 'fix this skill' or 'does this deserve a skill'. Not for scaffolding, vendoring or releases (vd:skill-management) or usage stats (vd:skill-audit)."
license: MIT
argument-hint: "[capability | fix <skill>] [--dir <skills-root>]"
metadata:
  author: vanducng
  version: "0.1.0"
---

# create-skill

A skill is a conditional prompt fragment: it costs context on every load and earns its place only by beating the base model. Proof is a pass rate.

## The bar

Say yes to all four or stop, and say so. Not writing a skill is a valid, common answer.

1. It recurs. 2. The base model gets it wrong unaided. 3. You can quote the phrases a user types for it. 4. It is narrow enough for firm rules.

## Rules

1. **Evals first.** Write `evals/` before `SKILL.md`: 3 or more scenarios, each with `prompt.md`, an optional `fixture/` and a deterministic `checks.sh` (exit 0 = pass, no judge model), and at least one clean case the skill must leave alone (`scenario.json`: `{"clean": true}`). Format: `references/eval-format.md`.
2. **Prove it fails.** Run each scenario without the skill. A non-clean scenario the base model already passes tests nothing: harden or drop it.
3. **Short body.** About 500 words, never past 800; depth goes in `references/`. The description is the router: what it does, the literal trigger phrases, up to 1024 characters.
4. **Fragile steps are scripts,** and the skill says when to run them.
5. **Fix at the highest layer.** Architecture, then types, then a script or lint, then a test, then prose last. Prose rules are the first thing dropped under load.
6. **Twice, not once.** Promote a failure to a rule or check after two evidence rows of the same class. One failure is a note: change nothing.
7. **A promoted check ships with the case it would have caught,** as an eval.
8. **An edit stays only if it scores better:** `run_evals.py --before OLD --after NEW` (blind labels), a win by the margin and no new clean-case failure.
9. **Portable.** No personal paths, usernames, hosts, org or person names in any skill file.

## Workflow

1. **Apply the bar first.** If any answer is no, reply `No skill: <which answer, why>` in a sentence or two, create no files, and stop. Do not interrogate or write evals for a request that fails it.
2. **Interrogate.** Get 4 to 8 trigger phrases, one real task end to end, what goes wrong without the skill, what is out of scope. No answer to "what goes wrong without it?" fails the bar: go back to step 1.
3. **Find the root:** `--dir`, else the repo's declared skills root, else `./skills`. Read that repo's `AGENTS.md` and match its validator and naming.
4. **Write the evals and run the baseline** (rule 2).
5. **Write the skill** until the failing scenarios pass: description first, then rules each with a reason, then scripts.
6. **Run the evals:** `python3 $HOME/skills/skills/create-skill/scripts/run_evals.py <skill-dir> --model <provider/model> --runs 3`. Cheapest model first, one family per round. With no agent runtime to run, say the evals were written and not run; never fake a result.
7. **Validate** with the repo's validator. It lints frontmatter only; the evals are the test.
8. **Report** scenarios, models, runs, passes, the baseline, and what was not tried.

## Fixing a failing skill

Read the outcome rows or transcript, name the failure class, pick the layer:

| Failure | Fix at |
|---|---|
| The wrong thing is possible at all | Remove the option (architecture, types) |
| A step is skipped or mangled | A script or lint that does or checks it |
| The same bug returns | A test or an eval for it |
| It loads at the wrong time | The description |
| None of these | One sentence of prose, then re-measure |

A check that blocks merges needs a lead or operator yes. A check with no catches in its window is a retirement candidate. Writing principles: `references/writing-principles.md`.
