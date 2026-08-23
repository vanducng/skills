---
name: scenario
description: "Generate comprehensive edge cases and test scenarios by decomposing a feature or file across 12 risk dimensions, or blast-radius review a change with --diff: what breaks beyond the diff, proven by running real code. Use for pre-implementation risk discovery, QA planning, regression design, exhaustive edge-case enumeration, and change-safety review. Triggers: 'edge cases for X', 'what could break', 'blast radius', 'what could this break beyond the diff', 'test scenarios', 'QA plan', 'risk discovery', 'enumerate failure modes'."
license: MIT
argument-hint: "<file path or feature description> [--iterations N] [--saturation] [--diff [ref]]"
metadata:
  author: vanducng
  attribution: "Scenario-decomposition pattern from autoresearch by Udit Goenka (MIT); blast-radius mode adapted from cursor/plugins pstack blast-radius (MIT)"
  version: "0.2.0"
---

# scenario

> Decompose a feature across 12 risk dimensions → exhaustive, severity-tagged edge cases.

## What this is - and isn't

| Skill | Does |
|---|---|
| `vd:cook --tdd` | **Runs** the tests (tests-first), reports pass/fail |
| `vd:brainstorm` | Explores *solution* options |
| **`scenario`** | **Enumerates** edge cases & failure modes (default), or **proves** a change's safety fact by running code (`--diff`) - never fixes |

Default-mode output is an input to test-writing / QA / `vd:plan` risk sections - not executable tests. `--diff` is the exception: it writes and runs a small proof script, because a blast-radius verdict without executed evidence is just a persuasive paragraph.

## Modes

| Mode | Behaviour |
|---|---|
| _(default)_ | One pass over all 12 dimensions → scenario list. |
| `--saturation` | Iterative rounds until coverage is exhausted (2 consecutive zero-new rounds) or `--iterations` cap (default 5). |
| `--diff [ref]` | Blast-radius review of a *change*: what breaks beyond the diff, with the one safety fact proven by running real code. Default ref: merge-base with the default branch (uncommitted changes included). |

`--iterations` only applies with `--saturation` (default mode is a single pass).

## Workflow

1. **Read the target** - the file/function or feature description. Identify inputs, outputs, state, external calls.
2. **Walk the 12 dimensions** - see [`references/dimensions.md`](references/dimensions.md). For each, ask "what input/condition in this category breaks the target?"
3. **Emit scenarios** - group by dimension; each: a one-line condition, **severity** (Critical/High/Med/Low), why it breaks, suggested test/assertion.
4. **(saturation)** - repeat with a completeness critic ("which dimension or angle is still thin?"); dedupe against the seen-set; stop per the rules in [`references/saturation-loop.md`](references/saturation-loop.md).
5. **Save** the report - write to the injected `Reports:` path. Filename: `scenario-{date}-{slug}.md`.
   Final handoff must include an openable report location, such as
   `[scenario-report.md](/absolute/path/to/scenario-report.md)` or
   `file:///absolute/path/to/scenario-report.md`, not just the basename.

## Output shape

```markdown
## <dimension>
- **[High]** <condition> - breaks because <reason>. Test: <assertion>.
- **[Low]**  <condition> - ...
```

End with a coverage line: `Dimensions covered: 12/12 · scenarios: N · saturation rounds: R`.

## Blast-radius mode (`--diff`)

Default mode enumerates what *could* break in a design. `--diff` answers a sharper question about a concrete change: what does this break somewhere else, and what is the one fact it is safe because of. Listing callers is not the job - grep finds those in a second. The job is the breakage grep does not show.

1. **Read the change** - the diff, the symbols it adds/changes/deletes, and what it now does differently, including the part the diff does not spell out.
2. **Find the one safety fact.** Most scary-looking changes are safe because of a single fact ("this call only drops already-dead cache entries"). Find it; if it holds, most risks die at once. Spend time here, not on a long list of maybes.
3. **Look where grep stops** - the pinned library's own source, execution timing (teardown, microtasks, retries), and what symbol search misses: API response shapes, DB columns, wire formats, feature flags, consumers three hops downstream, other languages reading the same bytes.
4. **Rate each risk honestly** - real likelihood, real cost. Keep confirmed risks; list checked-and-cleared separately. Cite real `file:line`; a search that finds nothing is still an answer; never invent a caller.
5. **Prove the one fact by running code** - a small script or test that calls the real code and fails loud if the fact is false. Paste the output. A writeup that merely sounds right is the trap.

**Certainty ladder** - get every safety fact as far down as is cheap, and say where it stopped:

| Level | Evidence |
|---|---|
| 1 | You said so - worthless alone |
| 2 | You pointed at a real `file:line` (or the library's own source) |
| 3 | You walked the failure path and it cannot reach |
| 4 | You ran a script/test against the real code |
| 5 | You reproduced it in the running app |

A fact stuck below 4 is reported as **unproven**, never rounded up to settled.

**Output shape (`--diff`):** What it does (incl. the non-obvious part) · The one safety fact + its ladder level + proof output · Risks (each: how it breaks, `file:line`, likelihood, cost, how to check) · Cleared · Before you merge (the cheapest test that catches the real bug).

**Save it like the default mode:** write the report to the injected `Reports:` path as `scenario-diff-{date}-{slug}.md` and hand back an openable location (`file:///absolute/path`), not just the basename.

**Boundaries:** landing verdicts stay with `vd:code-review`; codebase-fit stays with `vd:code-review --refactor`; this mode owns beyond-the-diff breakage with runnable proof.

## Limitations (honest)

- Enumeration quality depends on understanding the target - read it, don't guess.
- Not a fuzzer or property tester - default mode proposes cases without executing them; only `--diff` runs code, and only to prove the named safety fact.
- `--saturation` is bounded - it will stop at the iteration cap even if more cases theoretically exist (logs that it stopped).
