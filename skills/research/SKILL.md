---
name: research
description: "Deep technical research with multi-option evaluation. Use for technology selection, architecture decisions, library/framework comparison, security and performance analysis. Default mode is thorough; pass `--deep` for exhaustive coverage with expanded comparison matrices and edge-case analysis."
license: MIT
argument-hint: "[topic] [--deep]"
metadata:
  author: vanducng
  version: "2.0.0"
---

# Research

## Operating principles (override YAGNI/KISS/DRY for this skill)

Research is a deliverable, not a code change. The general "ship the smallest thing" rules **do not apply here**. For this skill:

- **Be deep, not shallow.** Surface findings are useless — dig until you understand *why*, not just *what*.
- **Evaluate multiple options.** Never recommend one approach without comparing at least 2–3 viable alternatives on the same criteria. A single-option report is a failure.
- **Brutal honesty.** Call out tradeoffs, deprecation, weak maintainership, security holes, vendor lock-in, hidden costs. No marketing language. No hedging.
- **Straight to the demand.** The user asked a specific question — answer *that* question completely before adding context. No filler, no padding, no recap of what they already know.
- **Cover every angle the user implied.** If they ask "what's the best message queue", they implicitly want: throughput, durability, ops burden, language support, cost, lock-in. Address all of them.
- **No premature simplification.** Long is fine if every section earns its place. Trim filler, never trim depth.

## Modes

| Mode | When | Queries | Report scope |
|---|---|---|---|
| **default** | Standard technical research | up to 5 search calls | Full template below |
| **`--deep`** | High-stakes decisions, multi-component architectures, security-critical choices | up to 12 search calls | Expanded comparison matrix, edge-case analysis, migration paths, failure modes, post-mortem references |

Detect `--deep` from the user's invocation (argument or in-prompt mention like "do a deep dive"). Announce mode at the start.

## Phase 1 — Scope

Before searching, write down:
- The exact question being answered (1 sentence)
- The decision the user is trying to make
- Evaluation criteria — list them explicitly. For tech selection at minimum: performance, security, maturity/maintainership, ops burden, ecosystem, cost, lock-in
- Recency bar (last 12 months unless historical context is needed)
- The 2–3+ candidate options to compare (if the user named one, find competitors)

If the user gave only one option to research, **expand to alternatives anyway** — saying "X is good" without "vs Y, Z" is a single-option failure.

## Phase 2 — Gather

### Search

Use the `WebSearch` tool. Run multiple queries in parallel.

**Query craft:**
- Each option × each criterion is one query (e.g. `"NATS vs Kafka throughput benchmark 2026"`, `"BullMQ production failure modes"`)
- Include current year, `"vs"`, `"benchmark"`, `"production"`, `"CVE"`, `"deprecated"`, `"migration from"`
- Prioritize: official docs, GitHub repos (issues + release notes), engineering blogs from companies actually running it, conference talks, post-mortems
- Skip: SEO listicles, vendor comparison pages, content-farm tutorials

**Query budget:**
- Default mode: **5 calls max**
- `--deep` mode: **12 calls max**
- User may request fewer — respect it
- Plan all queries before firing — don't iterate one-at-a-time

**For GitHub repos found:** fetch READMEs, recent release notes, open issue counts, last-commit dates directly. Maintainer health is part of the evaluation.

### Validation

- Cross-reference every non-trivial claim across ≥2 independent sources
- Check publication dates — discard anything >18 months old unless the topic is stable (RFCs, standards) or you flag it as historical
- Note where consensus exists and where the community is split — both are signal

## Phase 3 — Synthesize

Build the comparison **before** writing the report:

1. Matrix: rows = options, columns = criteria. Fill every cell. "Unknown" is a valid entry but flag what would close the gap.
2. Identify dealbreakers per option (one item that disqualifies it for this user's context).
3. Identify the boring, load-bearing facts: failure modes, ops burden, hiring market, total cost of ownership.
4. Form a recommendation with the runner-up named — and the conditions under which the runner-up wins.

In `--deep` mode, additionally produce:
- Migration cost / lock-in analysis per option
- Failure-mode catalog with mitigation per option
- Performance characteristics under realistic load (not vendor-published numbers)
- Operational war stories from production users

## Phase 4 — Report

### Where to save

Default: `./plans/reports/research-{topic-slug}-{YYYYMMDD}.md` from the current
working directory. Create `plans/reports/` before writing the report. If the
user provided an output path, use that instead.

### Template (default mode)

```markdown
# Research: {Topic}

_Date: {YYYY-MM-DD} · Mode: default · Queries: {n}_

## TL;DR
- **Recommendation:** {Option X}, because {one sentence}.
- **Runner-up:** {Option Y} — wins when {condition}.
- **Avoid:** {Option Z} — {dealbreaker}.

## The Question
What the user asked, restated precisely. The decision being made.

## Evaluation Criteria
Bulleted list. Why each matters for this decision.

## Options Considered
- {Option A} — {one-line summary}
- {Option B} — {one-line summary}
- {Option C} — {one-line summary}

## Comparison Matrix

| Criterion | Option A | Option B | Option C |
|---|---|---|---|
| Performance | … | … | … |
| Maturity | … | … | … |
| Ops burden | … | … | … |
| Ecosystem | … | … | … |
| Cost | … | … | … |
| Lock-in | … | … | … |
| {others} | … | … | … |

## Per-Option Deep Dive
### {Option A}
- **Strengths:** …
- **Weaknesses:** …
- **Dealbreakers:** …
- **Real-world users:** …
- **Recent CVEs / advisories:** …

(repeat for B, C)

## Recommendation
The full case for the recommended option, including conditions under which it loses.

## Implementation Notes
- Quick start
- Config gotchas
- Common pitfalls

## References
Official docs · GitHub repos · production case studies · benchmarks. Every reference is a link.

## Open Questions
What couldn't be answered with public information. What additional data would change the recommendation.
```

### Template additions for `--deep` mode

Add these sections after **Per-Option Deep Dive**:

```markdown
## Failure Modes
| Option | Mode | Symptom | Mitigation | Recovery cost |
|---|---|---|---|---|
| … | … | … | … | … |

## Migration Paths
- From {commonly-used predecessor} → Option A: cost, breaking changes, tooling
- Same for B, C
- Reverse migration cost (lock-in proxy)

## Operational War Stories
Linked post-mortems and engineering blog posts. Per option: one paragraph each, what broke and how it was fixed.

## Performance Under Realistic Load
Independent benchmarks only — not vendor numbers. Note hardware, workload shape, version. Flag where data is missing.

## Decision Reversibility
How much pain to switch off Option X 12 months in. This is the lock-in cost.
```

## Quality bar

- **Multi-option** — single-option reports are a failure
- **Cited** — every claim links to its source
- **Current** — last 12 months unless flagged historical
- **Brutal** — name the weaknesses, the failures, the deprecations
- **Decisive** — end with a recommendation and the conditions for the runner-up
- **Self-contained** — reader makes the decision from the report alone

## Specials

- **Security topics** — pull recent CVEs, check the maintainer's response cadence on past CVEs, note unpatched advisories
- **Performance topics** — demand independent benchmarks under realistic load; reject vendor-published numbers without a methodology link
- **New tech** — assess maintainer count, issue backlog, last-commit recency, sponsor/funding status, hiring market signal
- **APIs** — verify endpoints + auth still match docs by reading the source if needed
- **Older tech** — note deprecation timelines and concrete migration paths

## Output rules

1. Save to the path described in "Where to save"; do not write research reports
   into the repository root unless the user explicitly asks for that path
2. Open with TL;DR — recommendation, runner-up, avoid — before anything else
3. Comparison matrix is non-optional in any mode
4. Code blocks get language tags
5. Diagrams in Mermaid or ASCII when they clarify
6. End with open questions — what couldn't be answered, what would close the gap
7. No marketing language. No hedging without specifics. If you say "it depends", spell out what it depends on.

You are providing strategic technical intelligence for a decision that will outlast the report. Anticipate the follow-up questions and answer them in advance.
