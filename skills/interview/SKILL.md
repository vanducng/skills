---
name: interview
description: "Extracts what the user actually wants before any options, plan, or code. One question at a time with a stated hypothesis until an explicit yes on a restated intent (outcome, user, success, constraint, out of scope). Use when the ask is underspecified, missing who/why/success/constraint, or the user says 'interview me', 'grill me', 'before we start', 'are we sure', 'align first'. Pass --grill to walk an existing plan or idea. Pass --wayfinder (or 'chart this', 'work the map', 'this is huge', 'we'll be at this for a while') when the deciding will not fit one session - a shared map of decision tickets. Do not use for unambiguous mechanical edits, pure info questions, or solution-space exploration (vd:brainstorm)."
license: MIT
argument-hint: "[topic or ask] [--grill | --wayfinder]"
metadata:
  author: vanducng
  version: "1.2.0"
---

# Interview

Interview extracts **want**: outcome / user / success / constraint / out of scope, confirmed with an explicit yes. `--grill` walks an existing plan or idea. `--wayfinder` charts a multi-session decision map. Those are modes of this skill, not other skills - do not look for `vd:wayfinder`. This skill does not invent approaches, write build phases, or touch production source. If the user already knows the outcome and is choosing between designs in one session, that is `vd:brainstorm`.

## Hard rules

Default and `--grill` (want / walk-an-idea). `--wayfinder` uses the map rules in [`references/wayfinder.md`](references/wayfinder.md) instead.

1. **One question per message.** Batching is a survey, not an interview. Why: a stacked list gets a polite yes, not a decision.
2. **State a hypothesis + confidence before asking.** Attach your best guess and a recommended answer. Why: reacting is faster than generating from scratch, and a visible guess is easy to correct.
3. **Never ask a fact you can look up.** Repo layout, current stack, existing APIs, prior ADRs - read them. Why: the user's job is decisions, not research.
4. **Explicit yes on a concrete restate.** "Sounds good", "whatever you think", and silence are not yes. Why: a hollow yes becomes the wrong PR.
5. **Out of scope is mandatory.** Half of misalignment is silent disagreement about what is *not* being built.
6. **No options, no plan, no code** until the restate is confirmed. Why: options widen the search; this skill narrows it.
7. **Non-interactive is a blocker, not a guess.** CI, `vd:auto-loop`, `ultracook --auto` / exec: write the missing slots and stop. Do not invent the user.

## Modes

| Mode | When | Behavior |
|---|---|---|
| **default** | Ask is a want ("build X", "make it faster") | Extract outcome until confirmed |
| `--grill` | User has a plan/idea to stress-test | Walk decisions one at a time with a recommended answer; same yes gate. Other skills compose this via [`references/grilling.md`](references/grilling.md) |
| `--wayfinder` | Deciding will not fit one session | Chart and work a shared map of decision tickets - [`references/wayfinder.md`](references/wayfinder.md) |

Detect `--grill` from the flag or "grill this", "stress-test my plan". Detect `--wayfinder` from the flag or "chart this", "wayfinder", "work the map", "this is huge", "we'll be at this for a while". If both could apply, `--wayfinder` wins (it will call `--grill` on individual tickets). Announce the mode in the first reply.

## Workflow

`--wayfinder` does not use this loop. Follow [`references/wayfinder.md`](references/wayfinder.md).

### 0. Interactive check

If there is no live user (CI, scheduled, auto-loop, `ULTRACOOK_EXEC=1`): stop. List the missing slots (who / why / success / constraint / out of scope). Do not fill them in.

If the ask is already a typo, rename, or a self-contained one-liner and you can write the restate at ≥95% confidence: write it, ask once, and skip the loop.

### 1. Hypothesize

One sentence + an honest 0-100% number:

```
HYPOTHESIS: You want a standup answer to "how are we doing?", and "dashboard" was the convention that came to mind.
CONFIDENCE: ~30% - missing: who it's for, which metric, what success looks like
```

If you cannot write that sentence, you do not understand the ask yet. Do not skip to questions. Confidence below ~70% must name what is missing.

### 2. Ask one question

Prefer A/B/C when the answer space is bounded. Always attach your recommended answer. On Claude Code, `AskUserQuestion` with one question; elsewhere, the same prompt in plain text. Wait.

Do **not** ask "what would be best practice?". Ask what they actually want.

### 3. Probe convention and sophistication

When the answer is a convention ("a dashboard", "make it scalable", "clean architecture", "modern"):

> If you didn't have to justify this to anyone, what would you actually want?

One probe is enough. Then return to Step 2.

### 4. Restate

When confidence is high, write this back - their words, 6 lines:

```
Here's what I now think you want:

- Outcome:      <one line>
- User:         <who benefits>
- Why now:      <what changed>
- Success:      <how we know it worked>
- Constraint:   <the binding limit>
- Out of scope: <what we are explicitly not doing>

Yes / no / refine?
```

### 5. Confirm

The gate is an explicit **yes**. These are not yes:

| Heard | Do this |
|---|---|
| "Whatever you think" | Re-ask with two concrete options as a choice |
| "Sounds good" | "Anything you'd refine?" - silence is not confirmation |
| "Sure, let's go" | Same follow-up; often a polite exit |
| A yes to a vague restate | Rewrite the six lines concretely and re-confirm |

`--grill`: the session is done when every blocking decision has a recommended answer the user accepted. Same yes gate on the final restate.

### 6. Write and hand off

**Feature-first repos - claim a feature first.** If the hook context shows `Feature: none`, run `workbench new <slug>` once, then use the paths it prints. Skip when a feature is already active.

Write to the injected `Reports:` path: `interview-{YYYYMMDD-HHMM}-{slug}.md`. Do not write the file before the yes.

```markdown
# Intent: {title}

- Outcome:
- User:
- Why now:
- Success:
- Constraint:
- Out of scope:
- How decided: yes | no

## Notes
{only decisions the user actually made}
```

Then hand off. Do not start the next skill until they pick one, unless they already said "then plan" / "then brainstorm" / "then wayfinder":

| After confirm | Next |
|---|---|
| How is undecided, one session | `vd:brainstorm` with this file |
| How is undecided and the deciding will not fit one session | stay on this skill: `--wayfinder` |
| How is decided | `vd:plan` with this file |
| Tiny, mechanical, already specified | they may skip to `vd:cook --quick` - they say so |

`--wayfinder` verification: follow the checklist in [`references/wayfinder.md`](references/wayfinder.md).
