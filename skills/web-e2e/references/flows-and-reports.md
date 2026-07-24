# Flows and reports

## Flow files

A flow is an agent-executable markdown file at `<repo>/.e2e/flows/<name>.md`. Prose, not a DSL - the agent drives `agent-browser` from it. Start with exactly one `smoke.md`; add more only when a second real flow exists.

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

Preconditions are the flow's contract - the agent runs them, it never asks the human to. Seeding/reset commands belong here (explicit, per-flow), not in `up`.

### Deterministic sibling: `<name>.batch`

A flow MAY add `<name>.batch` beside its `.md`: one agent-browser command per line (no `agent-browser` prefix), replayed without a model via `grep -v '^#' <name>.batch | grep -v '^$' | tr '\n' '\0' | xargs -0 agent-browser batch --bail` (batch takes quoted command args or JSON on stdin, not a file path). The `.md` stays the agent-executed form; the `.batch` is the CI/regression form. Stable locators only - CSS selectors or `find role|text|label|testid` - never `@e` refs (snapshot-order-dependent, non-deterministic across runs).

```text
open https://myapp.test/login
find label "Email" fill "admin@example.com"
find label "Password" fill "dev-seeded-only"
press Enter
wait --text "Dashboard"
open https://myapp.test/orders
wait --text "Orders"
```

Verdict = the `batch --bail` exit code plus mechanical post-batch checks: `agent-browser errors --json` is `[]`, `agent-browser get url` matches the terminal route (avoid `wait --url` - it can time out on SPA navigations that succeeded), and failed/first-party requests are clean per `network requests --json`. See "Deterministic replay and CI" in the web-e2e SKILL.

## Reports

A run report is a verdict plus evidence pointers - not a QA document. Convention:

```markdown
# e2e: <app> - <date>

| Flow | Verdict | Evidence |
|---|---|---|
| smoke | PASS | /abs/path/.o11y/<run>/cdp/summary.json |
| create-order | FAIL - submit 422, toast never rendered | /abs/path/.o11y/<run>/pages/003/network/failed.jsonl |

Verdict: 1/2 failed. <one paragraph: what broke, where the evidence says so>
```

- One line per flow: `PASS` or `FAIL - <symptom>`. Absolute paths so they're clickable from anywhere.
- Evidence comes from the `vd:browser-trace` run captured during the flow (`bisect-cdp.mjs` buckets + `query.mjs errors`); screenshots land in the same run dir.
- Destination: the injected `Reports:` path when present; else `<repo>/.e2e/runs/<yymmdd-hhmm>-<flow>.md`. Tool-neutral - works the same under Codex or plain shell.
