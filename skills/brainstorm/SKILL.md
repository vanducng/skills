---
name: brainstorm
description: "Explore the solution space when the path isn't obvious - invent options, stress-test them, pick one. Use for architecture decisions, design tradeoffs, and when the user asks 'how should I approach X?'. Default produces a decision brief; pass `--quick` for chat-only, `--deep` for multi-round adversarial debate with full design doc. Do not use when want is unconfirmed (vd:interview), when the user says 'grill me' (vd:interview --grill), or when the deciding will not fit one session (vd:wayfinder)."
license: MIT
argument-hint: "[topic or problem] [--quick | --deep]"
metadata:
  author: vanducng
  version: "1.3.0"
---

# Brainstorm

## What this skill is - and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:interview` | "What do you actually want?" | Confirmed intent (outcome / success / out of scope) |
| `vd:interview --grill` | "Are these decisions the right ones?" | Same yes gate; decisions walked |
| `vd:research` | "Which of these known options should I pick?" | Comparison report with citations |
| **`vd:brainstorm`** | **"How should I approach this - what are the options?"** | **Decision brief with 3+ invented/curated approaches** |
| `vd:wayfinder` | "The deciding will not fit one session - what must be decided, in what order?" | Shared map of decision tickets |
| `vd:plan` | "Given the chosen approach, what are the steps?" | Phased implementation plan |

Brainstorm is **solution-space exploration**. You may end up recommending a known pattern, but the job is to surface paths the user hasn't considered, then converge. It does not own grilling - that is `vd:interview --grill`.

## Hard rules

1. **No code, no scaffolding, no file edits to source.** Only the brief gets written. If the user pushes for implementation, point them at `vd:plan` or `vd:cook`.
2. **Minimum 3 genuinely divergent options.** If all your options share the same architectural assumption (e.g. all are "different ORMs"), you haven't diverged - invent one that violates the shared assumption (e.g. "no ORM, raw SQL").
3. **Steel-man before strawman.** For each option write the *strongest* case first. If you can't argue for it convincingly, you don't understand it yet.
4. **Brutal honesty.** Name dealbreakers, hidden costs, ops burden, lock-in, hiring market, debugging pain. No marketing language. No symmetric "it's all tradeoffs" hedging - pick one.
5. **Decomposition first, depth second.** If the request spans 3+ independent subsystems, stop and decompose before any deep-dive.

## Modes

| Mode | When | Output |
|---|---|---|
| `--quick` | Single decision, low stakes, user wants chat | Verbal recommendation only - no file written |
| **default** | Standard architecture/design decision | Decision brief saved to disk |
| `--deep` | High-stakes, multi-component, irreversible | Full design doc with red-team round, decomposition, migration paths |

Detect mode from the argument or the user's language ("just a quick take" → `--quick`, "this is going to production" / "we need to get this right" → `--deep`). Announce the mode in your first message.

## Phase 1 - Frame

Before generating options, write down (in your reply, briefly):

- **The decision** - one sentence, in the user's words, restated precisely
- **Constraints** - what's fixed (language, team, deadline, existing systems, cost ceiling)
- **Success criteria** - what makes a chosen option "good" for *this* user
- **Want vs should-want** - the stated ask is sometimes a guess at the real need. Probe once: "you asked for X - is the underlying goal Y?" A wrong-framed problem produces three right answers to the wrong question.
- **Out of scope** - name what this decision explicitly is *not* solving, so options don't sprawl. Carry these into the brief's Non-goals.
- **Reversibility** - how expensive to switch later. High reversibility → bias toward speed. Low reversibility → bias toward depth.

If the *want* is unclear (missing who / why / success / constraint / out of scope) → **stop and run `vd:interview`**. Generating 3 options for an unconfirmed outcome is the wrong skill. Brainstorm starts after intent is confirmed.

If only a *constraint* or success criterion is fuzzy but the outcome is known, **ask before generating options**. Generating 3 wrong-shaped options because you assumed the constraints wastes the whole session.

**How to ask:** one clarifying question per message. Prefer multiple choice (A/B/C) over open-ended when the answer space is bounded - it's faster to answer and surfaces hidden assumptions. Save open-ended for "what does success look like?" style framing. Don't stack 4 questions in one reply.

### Scope check (mandatory)

If the request describes 3+ independent concerns ("build platform with auth + billing + analytics + chat") **stop**. Do not brainstorm. Reply:

> This spans N independent subsystems. Each deserves its own brainstorm. Suggested decomposition: [A, B, C]. Suggested order: [reason]. Pick one to start.

Do not deepen until the user picks one. This is the single most common failure mode of brainstorming sessions. When the decomposition itself spans more sessions than one brainstorm-per-part can carry - many interdependent decisions, weeks of fog - offer `vd:wayfinder` to chart the whole space as a decision map instead.

## Phase 2 - Diverge

Generate at least **3 genuinely different options**. Force divergence:

- **Option A** - the obvious one (what most engineers would reach for)
- **Option B** - a different architectural shape (different boundary, different layer, different paradigm)
- **Option C** - the one that violates a shared assumption of A and B (no DB, no service, build vs buy, manual vs automated, do nothing)

If you find yourself generating "X with Postgres / X with MySQL / X with SQLite" - that's one option, not three. Restart.

**Name the lens behind each option** so divergence is deliberate, not luck. Pick a different generative lens per option - say which:

- **Inversion** - solve the opposite ("don't store it" vs "store it better").
- **Constraint removal** - drop a constraint everyone assumed ("what if cost/latency/consistency didn't matter here?").
- **Audience shift** - design for a different user (the operator, not the end user; the future maintainer).
- **Combination** - fuse two existing approaches into one.
- **Simplification** - the do-less / do-nothing option.
- **10x** - what would you build if this had to handle 10x the scale/users/data.
- **Expert lens** - how would a {distributed-systems / security / data} specialist frame it.

For a deeper toolkit (SCAMPER, How-Might-We, JTBD, pre-mortem), see [`references/ideation-frameworks.md`](references/ideation-frameworks.md).

Where helpful, pull in proven patterns: search the web (`WebSearch`), read library docs, scan the codebase. Don't invent in a vacuum when the wheel exists. But also don't *only* surface known options - the user could have searched too.

**For visual brainstorming** (UI layouts, page/dashboard structure, comparing visual designs): produce a **visual draft** alongside text options - a single static HTML page rendering A/B/C panels in the browser, so the user can react to shapes, not just words. See [Visual draft mode](#visual-draft-mode) below. The brief itself stays text-only - visual drafts are intermediate artifacts.

Once the user picks a direction from the draft, hand off the *final* artifact to the right specialist: `vd:opendesign` for polished marketing/dashboard pages with brand-grade design systems, `vd:diagram` for rendered system / data-flow / sequence diagrams, or `vd:excalidraw` for editable whiteboard sketches. The draft is the cheap throwaway; the specialist produces the keepable artifact.

## Phase 3 - Stress-test (red team)

For each option, fill in:

| Field | What goes here |
|---|---|
| **Pitch** | One sentence steel-man - the strongest case for this option |
| **How it works** | 2-4 sentences - concrete enough that the reader could sketch it |
| **Strengths** | What this is genuinely good at - not generic ("it's simple"), specific ("you skip the migration step entirely") |
| **Weaknesses** | What hurts in production, on month 6, when the team grows |
| **Dealbreaker check** | One concrete scenario where this option *fails* for this user's context |
| **Hidden cost** | Ops burden, hiring market, debugging pain, vendor lock-in, license, on-call load |
| **Reversibility** | Cost to switch off this option in 12 months |

In `--deep` mode: also produce a **failure-mode catalog** per option (what breaks at scale, under load, under attack, when the team turns over).

## Phase 4 - Converge

Don't punt. Pick one. State:

- **Recommendation:** Option X.
- **Why it wins:** One paragraph, grounded in the user's *actual* constraints from Phase 1.
- **Runner-up:** Option Y wins if {specific condition flips} - name the condition.
- **Avoid:** Option Z because {dealbreaker}. Or "no option avoids the user's biggest risk - here's how to mitigate it regardless."

If you genuinely cannot pick because a constraint is missing, identify the missing constraint and ask one targeted question. Don't hide indecision behind "it depends."

## Phase 5 - Brief

### Where to save

**Feature-first repos - claim a feature first.** If the hook context shows `Feature: none` (paths resolve under `_global/scratch/`), run `workbench new <slug>` (kebab summary of the task) before writing, then use the paths it prints - work lands in `features/<slug>/` instead of the shared scratch bin. Idempotent: skip when a feature is already active (a `feat/*` branch, an active plan, or a prior `workbench new`).

Write to the injected `Reports:` path. Filename: `brainstorm-{YYYYMMDD-HHMM}-{slug}.md`. `--quick` mode: skip the file. Verbal output only.

### Template (default mode)

```markdown
# Brainstorm: {Topic}

_Date: {YYYY-MM-DD} · Mode: default_

## TL;DR
- **Recommendation:** {Option X}, because {one sentence rooted in user's constraints}.
- **Runner-up:** {Option Y} - wins when {specific condition}.
- **Avoid:** {Option Z} - {dealbreaker}.

## The Decision
The exact decision being made, restated in one sentence.

## Constraints & Success Criteria
- Constraint: {fixed thing}
- Constraint: {fixed thing}
- Success: {what "good" looks like for this user}
- Reversibility: {high | medium | low - and what that implies}

## Options

### Option A - {name}
- **Pitch:** {one-sentence steel-man}
- **How it works:** {2-4 sentences, concrete}
- **Strengths:** {specific, not generic}
- **Weaknesses:** {what hurts in month 6}
- **Dealbreaker scenario:** {one concrete failure case}
- **Hidden cost:** {ops, hiring, lock-in, debugging}
- **Reversibility:** {cost to switch off}

### Option B - {name}
(same shape)

### Option C - {name}
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

When `--deep` fans its research/red-team rounds out through the Workflow tool, keep each agent's output schema minimal - mark only truly-required fields `required`, avoid `additionalProperties: false`, and paste a one-line valid JSON example into every agent prompt (strict schemas fail ~74% of first attempts, then self-heal on costly retries).

Add these sections after **Recommendation**:

```markdown
## Red-Team Round
For each option, the strongest argument *against* it from a hostile reviewer's perspective. Then the rebuttal - or the concession.

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

## Phase 6 - Self-review & handoff

### Self-review (mandatory before handoff)

After writing the brief, re-read it with fresh eyes and fix issues inline. No second pass - just fix and move on:

1. **Placeholder scan** - any `TBD`, `TODO`, `{...}` template stubs, or unfilled cells in the comparison table? Fill or remove.
2. **Internal consistency** - does the recommendation in TL;DR match the recommendation in the long section? Do the strengths/weaknesses contradict the dealbreaker scenario? Does the runner-up condition actually flip the decision?
3. **Scope check** - is this still one decision, or did it sprawl into 3? If it sprawled, decompose and write multiple briefs.
4. **Ambiguity check** - could any criterion or recommendation be read two ways? Pick one and make it explicit.
5. **Divergence check** - re-read the three options. If two share the same architectural assumption, you didn't diverge - regenerate the weakest one.

### User review gate

After self-review, surface the file with an openable location and stop. Do not auto-invoke `vd:plan`:

> Brief saved to `[brainstorm-topic.md](/absolute/path/to/brainstorm-topic.md)` (`file:///absolute/path/to/brainstorm-topic.md`). Recommendation: **{Option X}**, runner-up **{Option Y}** if {condition}. Please review and tell me if you want changes - or say "plan it" and I'll hand off to `vd:plan`.

If the decision is consequential and hard to reverse (datastore, framework, auth model, a public contract), offer to record it permanently: `vd:docs adr` writes an ADR under `docs/decisions/` capturing the why and the rejected alternatives. The brief is a working artifact; the ADR is the durable team-facing record.

If the user requests changes, edit the brief and re-run the self-review checklist before re-surfacing. Only invoke `vd:plan` after explicit approval.

**Read approval critically - not every "yes" is a real yes.** Watch for these and probe instead of proceeding:

- **Polite yes** - "sounds good" with no engagement on the tradeoffs. Ask which part resonated; a real yes can name why.
- **Tired yes** - agreeing to end the conversation after a long thread. Offer to pause rather than bank a fatigue decision.
- **Deferring yes** - "you're the expert, whatever you think." Push the one judgment call back to them; you can't own a constraint only they know.
- **Misunderstood yes** - agreeing to a different thing than you proposed. Restate the recommendation in one line and confirm it's the same picture.

A decision banked on a fake yes resurfaces as rework two phases later.

`--quick` mode skips Phase 6 entirely - verbal output only.

## Visual draft mode

A lightweight interactive layer for the subset of brainstorm questions where the user would understand a *picture* faster than a paragraph. Static HTML opened in the browser - no server, no event polling, no session state. Borrows the wireframe CSS vocabulary, drops the runtime machinery.

### When to use

**Yes** - the *content itself* is visual:
- "Which dashboard layout?" (sidebar vs topbar vs split)
- "Which signup flow shape?" (single-page vs wizard vs progressive disclosure)
- "Which card layout for the feed?"
- Side-by-side visual comparisons of two interface directions

**No** - text decisions dressed up as visuals:
- "Which auth strategy / database / message queue?" - text comparison table
- "What does 'success' mean here?" - clarifying question
- Anything in the data-engineering / devops / analytics disciplines per [Cross-discipline cues](#cross-discipline-cues)

If you can express the decision as A/B/C bullet points without losing fidelity, skip the visual draft. A question *about* a UI topic isn't automatically a visual question.

### Where to save (standardized artifact directory)

Use the active plan context (injected by session hooks) - **do not invent new directories**, especially not under hidden dotdirs:

- **Plan active:** `{plan_dir}/visuals/brainstorm-{slug}/comparison-{N}.html`
- **No plan:** write to the injected `Visuals:` path. Subdir: `brainstorm-{YYYYMMDD-HHMM}-{slug}/comparison-{N}.html`.

Increment `{N}` per iteration: `comparison-1.html`, `comparison-2.html`. Never overwrite - the trail of drafts is part of the brainstorm record.

### How to render

1. Read the bundled template at `<this-skill-dir>/assets/comparison-template.html`.
2. Copy it to the target path above. Fill the three placeholders:
   - `{{TITLE}}` - the visual question, e.g. "Which dashboard layout?"
   - `{{SUBTITLE}}` - one-sentence framing
   - `{{PANELS}}` - your A/B/C panel HTML, using ONLY the classes documented below
3. `open <path>` (macOS) / `xdg-open <path>` (Linux) to launch in the user's default browser.
4. Tell the user where to open the draft using an openable location, not just the basename:
   *"Visual draft at `[comparison-1.html](/absolute/path/to/comparison-1.html)` (`file:///absolute/path/to/comparison-1.html`). Take a look and reply with the letter you prefer - or describe what's off."*

### CSS vocabulary in the template

Use these classes - don't invent more, don't write inline styles:

| Class | Use for |
|---|---|
| `.options` + `.option[data-choice]` + `.letter` + `.content` | A/B/C lettered cards (conceptual choices) |
| `.cards` + `.card` + `.card-image` + `.card-body` | Richer cards with mockup bodies (visual designs) |
| `.mockup` + `.mockup-header` + `.mockup-body` | Wrapped wireframe (browser-chrome frame) |
| `.split` | Side-by-side mockup pair |
| `.pros-cons` + `.pros` / `.cons` | Tradeoff lists per option |
| `.mock-nav`, `.mock-sidebar`, `.mock-content` | Wireframe layout primitives |
| `.mock-button`, `.mock-input`, `.placeholder` | Wireframe element primitives |

The template handles theme tokens, dark-mode, responsive grid, and a cosmetic click-to-highlight (no event logging - the user replies in chat).

### Iteration

If the user requests changes after seeing the draft, write a **new file** (`comparison-2.html`) - don't overwrite. The diff between iterations is itself useful, and lets the brief reference "we considered layout v1 and rejected it because…".

### Handoff after pick

Once the user picks a direction, the visual draft has served its purpose - it bought a converging decision before any artifact got polished. After the brief is approved (Phase 6), point the user at the right specialist for the *final* artifact:

| Pick shape | Hand off to |
|---|---|
| Polished UI page (landing, dashboard, marketing) | `vd:opendesign` |
| Rendered system / data-flow / sequence diagram | `vd:diagram` |
| Editable whiteboard / architecture sketch | `vd:excalidraw` |

The brainstorm's job is to pick the direction. Materializing it is downstream.

## Anti-rationalization

| Excuse | Reality |
|---|---|
| "User said it's simple - skip the brief" | Simple problems get over-engineered most often. The brief is 80 lines. Write it. |
| "I already know the answer" | Then writing the brief takes 5 minutes. Do it - you may discover you didn't. |
| "Three options is too many for this small thing" | Three is the floor. If the third feels forced, that *is* the lesson - but generate it anyway. |
| "Let me just look at the code first" | Brainstorm tells you what to look for. Phase 1 first. |
| "User wants action, not discussion" | Bad action wastes more time than 10 minutes of brainstorming. Push back politely. |
| "I'll converge later - let me explore more" | If you've laid out 3 stress-tested options, you have enough. Pick. |
| "I'll generate options so they can figure out what they want" | Options widen the search. `vd:interview` narrows it. Run that first. |
| "They said 'build a dashboard' - I know what that means" | Convention, not intent. If you cannot write Outcome / Success / Out of scope, interview first. |

## Quality bar

- **3+ genuinely divergent options** - three flavors of the same idea is a fail
- **Steel-manned** - the option you don't favor still gets its strongest case
- **Decisive** - ends with a pick + named conditions for the runner-up
- **Grounded** - the recommendation cites the user's actual constraints, not generic best practice
- **No implementation** - design only; pointer to `vd:plan` for the next step
- **Self-contained** - reader makes the decision from the brief alone

## Specials

- **Greenfield** - bias toward reversibility; the cheapest option that buys time to learn often wins
- **Migration / replacement** - Phase 3 must include the migration cost as a first-class criterion, not an afterthought
- **Performance-driven** - demand realistic-load numbers in Phase 3; reject vendor benchmarks
- **Build-vs-buy** - always include "do nothing" or "use the boring existing tool" as a real option
- **Org-flavored decisions** (microservices, monorepo, framework choice) - Phase 0 must capture team size, hiring market, on-call structure; these decisions are 60% organizational, 40% technical

## Output rules

1. Announce mode (`--quick` / default / `--deep`) in your first reply
2. Phase 1 (frame + scope check) happens *before* any option generation - visible to the user
3. If decomposition triggers, stop and ask - do not deepen
4. Default and `--deep` modes save the brief to disk; `--quick` does not
5. Brief opens with TL;DR - recommendation, runner-up, avoid - before everything else
6. Three+ options, each with the full Phase 3 shape - partial entries are a fail
7. End with Open Questions - what couldn't be resolved, what would change the call
8. After the brief is written, run Phase 6 self-review, then surface the file path + recommendation and **wait for user approval** before invoking `vd:plan`

## Workflow position

**Typically follows:** `vd:interview` (confirmed want), `vd:scout` (after surveying the surface), `vd:debug` (when the diagnosis exposes a design decision worth re-deciding)

**Typically precedes:** `vd:plan` (for the chosen approach), or `vd:research` (if Phase 3 surfaced an unknown option that needs deep evaluation)

**Compares to:** `vd:interview` (extract want, no options) - when the outcome is unconfirmed, prefer `interview`. `vd:interview --grill` (walk an existing idea) - not a brainstorm mode. `vd:research` (known options, cited comparison) - when the user names options, prefer `research`; when the path is unclear, prefer `brainstorm`. `vd:wayfinder` - when the deciding itself will not fit one session.

## Cross-discipline cues

The decision space differs by discipline - call it out in Phase 1 so options diverge correctly:

- **Software** - hot path is correctness + maintainability + reversibility
- **Data engineering** - hot path is idempotency + lineage + freshness/SLA + backfill cost; "do nothing, materialize later" is often a real option
- **DevOps / infra** - hot path is blast radius + reversibility + multi-env parity + ops burden; managed-service-vs-self-host is almost always one of the three options
- **Analytics / BI** - hot path is metric correctness + governance + refresh latency + governance of definitions; "single source of truth" usually beats "more dashboards"

If the request mixes disciplines, the scope-check rule still applies - decompose before brainstorming.
