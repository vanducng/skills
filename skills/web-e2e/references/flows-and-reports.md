# Flows and reports

## Flow files

A flow is an agent-executable markdown file at `<repo>/.e2e/flows/<name>.md`. Prose, not a DSL — the agent drives `browse` from it. Start with exactly one `smoke.md`; add more only when a second real flow exists.

```markdown
# Flow: smoke

Goal: app serves, session is authenticated, core page renders clean.

Preconditions:
- `e2e.cjs status` READY and auth logged-in (or injected).
- <anything stateful: queue worker, seeded records>

Steps:
1. Open <authed entry URL>.
2. Snapshot; assert the authed shell renders (no login form).
3. Navigate to <core feature>; assert its data loads.

Assertions:
- Final URL is <expected route>, not a login route.
- Trace run has zero console exceptions.
- No failed first-party requests in the trace.

Notes:
- <external APIs to mock or skip; destructive steps to avoid>
```

Preconditions are the flow's contract — the agent runs them, it never asks the human to. Seeding/reset commands belong here (explicit, per-flow), not in `up`.

## Reports

A run report is a verdict plus evidence pointers — not a QA document. Convention:

```markdown
# e2e: <app> — <date>

| Flow | Verdict | Evidence |
|---|---|---|
| smoke | PASS | /abs/path/.o11y/<run>/cdp/summary.json |
| create-order | FAIL — submit 422, toast never rendered | /abs/path/.o11y/<run>/pages/003/network/failed.jsonl |

Verdict: 1/2 failed. <one paragraph: what broke, where the evidence says so>
```

- One line per flow: `PASS` or `FAIL — <symptom>`. Absolute paths so they're clickable from anywhere.
- Evidence comes from the `vd:browser-trace` run captured during the flow (`bisect-cdp.mjs` buckets + `query.mjs errors`); screenshots land in the same run dir.
- Destination: the hook-injected Reports path when present (`.workbench/reports/e2e-...md`), else `<repo>/.e2e/runs/<yymmdd-hhmm>-<flow>.md`. Tool-neutral — works the same under Codex or plain shell.
