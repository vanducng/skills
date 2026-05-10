---
name: brainstorm
description: "Explore the solution space when the path isn't obvious — invent options, stress-test them, pick one. Use for architecture decisions, design tradeoffs, ambiguous problems, and when the user asks 'how should I approach X?'. Default produces a decision brief; pass `--quick` for chat-only, `--deep` for multi-round adversarial debate with full design doc."
license: MIT
argument-hint: "[topic or problem] [--quick | --deep]"
metadata:
  author: vanducng
  version: "1.1.0"
---

# Brainstorm

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:research` | "Which of these known options should I pick?" | Comparison report with citations |
| **`vd:brainstorm`** | **"How should I approach this — what are the options?"** | **Decision brief with 3+ invented/curated approaches** |
| `vd:plan` | "Given the chosen approach, what are the steps?" | Phased implementation plan |

Brainstorm is **solution-space exploration**. You may end up recommending a known pattern, but the job is to surface paths the user hasn't considered, then converge.

## Hard rules

1. **No code, no scaffolding, no file edits to source.** Only the brief gets written. If the user pushes for implementation, point them at `vd:plan` or `vd:cook`.
2. **Minimum 3 genuinely divergent options.** If all your options share the same architectural assumption (e.g. all are "different ORMs"), you haven't diverged — invent one that violates the shared assumption (e.g. "no ORM, raw SQL").
3. **Steel-man before strawman.** For each option write the *strongest* case first. If you can't argue for it convincingly, you don't understand it yet.
4. **Brutal honesty.** Name dealbreakers, hidden costs, ops burden, lock-in, hiring market, debugging pain. No marketing language. No symmetric "it's all tradeoffs" hedging — pick one.
5. **Decomposition first, depth second.** If the request spans 3+ independent subsystems, stop and decompose before any deep-dive.

## Modes

| Mode | When | Output |
|---|---|---|
| `--quick` | Single decision, low stakes, user wants chat | Verbal recommendation only — no file written |
| **default** | Standard architecture/design decision | Decision brief saved to disk |
| `--deep` | High-stakes, multi-component, irreversible | Full design doc with red-team round, decomposition, migration paths |

Detect mode from the argument or the user's language ("just a quick take" → `--quick`, "this is going to production" / "we need to get this right" → `--deep`). Announce the mode in your first message.

## Phase 1 — Frame

Before generating options, write down (in your reply, briefly):

- **The decision** — one sentence, in the user's words, restated precisely
- **Constraints** — what's fixed (language, team, deadline, existing systems, cost ceiling)
- **Success criteria** — what makes a chosen option "good" for *this* user
- **Reversibility** — how expensive to switch later. High reversibility → bias toward speed. Low reversibility → bias toward depth.

If any of those are unclear or assumed, **ask before generating options**. Generating 3 wrong-shaped options because you assumed the constraints wastes the whole session.

### Scope check (mandatory)

If the request describes 3+ independent concerns ("build platform with auth + billing + analytics + chat") **stop**. Do not brainstorm. Reply:

> This spans N independent subsystems. Each deserves its own brainstorm. Suggested decomposition: [A, B, C]. Suggested order: [reason]. Pick one to start.

Do not deepen until the user picks one. This is the single most common failure mode of brainstorming sessions.

## Phase 2 — Diverge

Generate at least **3 genuinely different options**. Force divergence:

- **Option A** — the obvious one (what most engineers would reach for)
- **Option B** — a different architectural shape (different boundary, different layer, different paradigm)
- **Option C** — the one that violates a shared assumption of A and B (no DB, no service, build vs buy, manual vs automated, do nothing)

If you find yourself generating "X with Postgres / X with MySQL / X with SQLite" — that's one option, not three. Restart.

Where helpful, pull in proven patterns: search the web (`WebSearch`), read library docs, scan the codebase. Don't invent in a vacuum when the wheel exists. But also don't *only* surface known options — the user could have searched too.

## Phase 3 — Stress-test (red team)

For each option, fill in:

| Field | What goes here |
|---|---|
| **Pitch** | One sentence steel-man — the strongest case for this option |
| **How it works** | 2-4 sentences — concrete enough that the reader could sketch it |
| **Strengths** | What this is genuinely good at — not generic ("it's simple"), specific ("you skip the migration step entirely") |
| **Weaknesses** | What hurts in production, on month 6, when the team grows |
| **Dealbreaker check** | One concrete scenario where this option *fails* for this user's context |
| **Hidden cost** | Ops burden, hiring market, debugging pain, vendor lock-in, license, on-call load |
| **Reversibility** | Cost to switch off this option in 12 months |

In `--deep` mode: also produce a **failure-mode catalog** per option (what breaks at scale, under load, under attack, when the team turns over).

## Phase 4 — Converge

Don't punt. Pick one. State:

- **Recommendation:** Option X.
- **Why it wins:** One paragraph, grounded in the user's *actual* constraints from Phase 1.
- **Runner-up:** Option Y wins if {specific condition flips} — name the condition.
- **Avoid:** Option Z because {dealbreaker}. Or "no option avoids the user's biggest risk — here's how to mitigate it regardless."

If you genuinely cannot pick because a constraint is missing, identify the missing constraint and ask one targeted question. Don't hide indecision behind "it depends."

## Phase 5 — Brief

### Where to save

- Active plan context (from session hooks): `{plan_dir}/brainstorm-{YYYYMMDD}-{slug}.md`
- Otherwise: `plans/reports/brainstorm-{YYYYMMDD-HHMM}-{slug}.md` (use the report path injected by hooks)
- `--quick` mode: skip the file. Verbal output only.

### Template (default mode)

```markdown
# Brainstorm: {Topic}

_Date: {YYYY-MM-DD} · Mode: default_

## TL;DR
- **Recommendation:** {Option X}, because {one sentence rooted in user's constraints}.
- **Runner-up:** {Option Y} — wins when {specific condition}.
- **Avoid:** {Option Z} — {dealbreaker}.

## The Decision
The exact decision being made, restated in one sentence.

## Constraints & Success Criteria
- Constraint: {fixed thing}
- Constraint: {fixed thing}
- Success: {what "good" looks like for this user}
- Reversibility: {high | medium | low — and what that implies}

## Options

### Option A — {name}
- **Pitch:** {one-sentence steel-man}
- **How it works:** {2-4 sentences, concrete}
- **Strengths:** {specific, not generic}
- **Weaknesses:** {what hurts in month 6}
- **Dealbreaker scenario:** {one concrete failure case}
- **Hidden cost:** {ops, hiring, lock-in, debugging}
- **Reversibility:** {cost to switch off}

### Option B — {name}
(same shape)

### Option C — {name}
(same shape)

## Comparison

| Criterion | A | B | C |
|---|---|---|---|
| Time to first ship | … | … | … |
| Ops burden | … | … | … |
| Reversibility | … | … | … |
| Failure blast radius | … | … | … |
| {user-specific criterion} | … | … | … |

## Recommendation
The full case. Why X wins *given the user's constraints*. The condition under which the runner-up takes over. What we're explicitly trading away.

## Open Questions
What couldn't be answered without more input. What would change the recommendation.

## Next Step
- If user wants a plan: `vd:plan` with this brief as input
- If user wants to validate before committing: spike Option X for {time-box}
```

### Template additions for `--deep` mode

Add these sections after **Recommendation**:

```markdown
## Red-Team Round
For each option, the strongest argument *against* it from a hostile reviewer's perspective. Then the rebuttal — or the concession.

## Failure-Mode Catalog
| Option | Failure | Trigger | Blast radius | Mitigation |
|---|---|---|---|---|
| … | … | … | … | … |

## Migration Paths
- From current state → Option X: cost, breaking changes, sequencing
- Same for runner-up (so the user sees the cost of being wrong)

## Decomposition (if applicable)
If the chosen option has independent sub-parts, list them in build order with rationale.
```

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "User said it's simple — skip the brief" | Simple problems get over-engineered most often. The brief is 80 lines. Write it. |
| "I already know the answer" | Then writing the brief takes 5 minutes. Do it — you may discover you didn't. |
| "Three options is too many for this small thing" | Three is the floor. If the third feels forced, that *is* the lesson — but generate it anyway. |
| "Let me just look at the code first" | Brainstorm tells you what to look for. Phase 1 first. |
| "User wants action, not discussion" | Bad action wastes more time than 10 minutes of brainstorming. Push back politely. |
| "I'll converge later — let me explore more" | If you've laid out 3 stress-tested options, you have enough. Pick. |

## Quality bar

- **3+ genuinely divergent options** — three flavors of the same idea is a fail
- **Steel-manned** — the option you don't favor still gets its strongest case
- **Decisive** — ends with a pick + named conditions for the runner-up
- **Grounded** — the recommendation cites the user's actual constraints, not generic best practice
- **No implementation** — design only; pointer to `vd:plan` for the next step
- **Self-contained** — reader makes the decision from the brief alone

## Specials

- **Greenfield** — bias toward reversibility; the cheapest option that buys time to learn often wins
- **Migration / replacement** — Phase 3 must include the migration cost as a first-class criterion, not an afterthought
- **Performance-driven** — demand realistic-load numbers in Phase 3; reject vendor benchmarks
- **Build-vs-buy** — always include "do nothing" or "use the boring existing tool" as a real option
- **Org-flavored decisions** (microservices, monorepo, framework choice) — Phase 0 must capture team size, hiring market, on-call structure; these decisions are 60% organizational, 40% technical

## Output rules

1. Announce mode (`--quick` / default / `--deep`) in your first reply
2. Phase 1 (frame + scope check) happens *before* any option generation — visible to the user
3. If decomposition triggers, stop and ask — do not deepen
4. Default and `--deep` modes save the brief to disk; `--quick` does not
5. Brief opens with TL;DR — recommendation, runner-up, avoid — before everything else
6. Three+ options, each with the full Phase 3 shape — partial entries are a fail
7. End with Open Questions — what couldn't be resolved, what would change the call
8. After the brief is written, ask if the user wants to invoke `vd:plan` next

## Workflow position

**Typically follows:** `vd:scout` (after surveying the surface), `vd:debug` (when the diagnosis exposes a design decision worth re-deciding), or a fresh ambiguous request

**Typically precedes:** `vd:plan` (for the chosen approach), or `vd:research` (if Phase 3 surfaced an unknown option that needs deep evaluation)

**Compares to:** `vd:research` (known options, cited comparison) — when the user names options, prefer `research`; when the path is unclear, prefer `brainstorm`

## Cross-discipline cues

The decision space differs by discipline — call it out in Phase 1 so options diverge correctly:

- **Software** — hot path is correctness + maintainability + reversibility
- **Data engineering** — hot path is idempotency + lineage + freshness/SLA + backfill cost; "do nothing, materialize later" is often a real option
- **DevOps / infra** — hot path is blast radius + reversibility + multi-env parity + ops burden; managed-service-vs-self-host is almost always one of the three options
- **Analytics / BI** — hot path is metric correctness + governance + refresh latency + governance of definitions; "single source of truth" usually beats "more dashboards"

If the request mixes disciplines, the scope-check rule still applies — decompose before brainstorming.
