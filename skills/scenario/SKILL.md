---
name: scenario
description: "Generate comprehensive edge cases and test scenarios by decomposing a feature or file across 12 risk dimensions. Use for pre-implementation risk discovery, QA planning, regression design, and exhaustive edge-case enumeration. Triggers: 'edge cases for X', 'what could break', 'test scenarios', 'QA plan', 'risk discovery', 'enumerate failure modes'."
license: MIT
argument-hint: "<file path or feature description> [--iterations N] [--saturation]"
metadata:
  author: vanducng
  attribution: "Scenario-decomposition pattern from autoresearch by Udit Goenka (MIT)"
  version: "0.1.0"
---

# scenario

> Decompose a feature across 12 risk dimensions → exhaustive, severity-tagged edge cases.

## What this is - and isn't

| Skill | Does |
|---|---|
| `vd:test` | **Runs** tests, reports pass/fail |
| `vd:brainstorm` | Explores *solution* options |
| **`scenario`** | **Enumerates** edge cases & failure modes to test - does not run or fix them |

Output is an input to test-writing / QA / `vd:plan` risk sections - not executable tests.

## Modes

| Mode | Behaviour |
|---|---|
| _(default)_ | One pass over all 12 dimensions → scenario list. |
| `--saturation` | Iterative rounds until coverage is exhausted (2 consecutive zero-new rounds) or `--iterations` cap (default 5). |

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

## Limitations (honest)

- Enumeration quality depends on understanding the target - read it, don't guess.
- Not a fuzzer or property tester - it proposes cases, it doesn't execute them.
- `--saturation` is bounded - it will stop at the iteration cap even if more cases theoretically exist (logs that it stopped).
