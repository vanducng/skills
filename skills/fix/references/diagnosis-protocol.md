# Diagnosis protocol

Use this when the root cause is not already proven. The goal is to replace guesswork with a short evidence chain.

## Baseline first

Capture the broken state before investigating:

1. Exact error message, failing assertion, wrong value, or observed behavior.
2. Full command, input, environment, URL, DAG run, workflow run, or request that reproduces it.
3. Relevant stack trace, logs, run-results, events, or query output with timestamps.
4. Recent changes touching the affected files/resources: `git log --oneline -10 -- <path>`.

This baseline is required for the verification rerun.

## Diagnosis chain

### 1. Observe

Read the evidence before forming a theory:

- Where does the symptom surface: file, line, model, task, pod, workflow, or dashboard?
- What is the smallest reproduction?
- What changed recently in code, data, environment, dependencies, or schedule?
- What should happen instead?

### 2. Hypothesize

For each hypothesis, state:

1. The suspected cause.
2. Evidence that would confirm it.
3. Evidence that would refute it.
4. The quickest safe test.

Common categories: recent regression, bad data/state, env/config mismatch, race/timing, missing validation, contract drift, stale cache, dependency upgrade, or incorrect assumption about ordering/shape.

### 3. Test

Test hypotheses against code and runtime evidence. Prefer parallel `Explore` agents or parallel shell reads when there are multiple independent suspects. Mark each hypothesis:

- **Confirmed**: evidence supports it as the root cause.
- **Refuted**: evidence contradicts it; discard and record why.
- **Inconclusive**: gather more evidence or sharpen the hypothesis.

If 2+ plausible hypotheses are refuted, broaden the context and re-scout. The boundary is probably wrong.

### 4. Trace

Trace backward from symptom to source:

```
Symptom
  <- immediate cause
  <- contributing condition
  <- root cause to fix
```

Do not fix where the error appears unless that location is also the source.

## Required diagnosis output

```markdown
Root cause:
[specific source defect, with file/resource evidence]

Evidence chain:
1. [Observation]
2. [Hypothesis tested and result]
3. [Trace to root cause]

Why now:
[recent change, data shape, env condition, timing, or load factor]

Blast radius:
- [callers/downstream models/user flows/jobs/resources/contracts to verify]

Recommended fix:
[minimal change that addresses the source]
```
