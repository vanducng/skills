---
name: interview
description: "Extracts what the user actually wants before any options, plan, or code. One question at a time with a stated hypothesis until an explicit yes on a restated intent (outcome, user, success, constraint, out of scope). Use when the ask is underspecified, missing who/why/success/constraint, or the user says 'interview me', 'grill me', 'before we start', 'are we sure', 'align first'. Do not use for unambiguous mechanical edits, pure info questions, or solution-space exploration - that's vd:brainstorm."
license: MIT
argument-hint: "[topic or ask] [--grill]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Interview

> What people ask for and what they want are different things. Close that gap before it costs a plan or a PR.

## What this skill is - and isn't

| Skill | Question it answers | Output |
|---|---|---|
| **`vd:interview`** | **"What do you actually want?"** | **Confirmed intent (outcome / user / success / constraint / out of scope)** |
| `vd:brainstorm` | "How should we approach this?" | Decision brief with 3+ options |
| `vd:wayfinder` | "The deciding will not fit one session - what must be decided, in what order?" | Shared map of decision tickets |
| `vd:research` | "Which known option should I pick?" | Cited comparison |
| `vd:plan` | "What are the steps?" | Phased plan |

Interview extracts **want**. It does not invent approaches, write phases, or touch source. If the user already knows the outcome and is choosing between designs, that is `vd:brainstorm`.

## Hard rules

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
| `--grill` | User has a plan/idea to stress-test | Walk decisions one at a time with a recommended answer; same yes gate |

Detect `--grill` from the flag or "grill this", "stress-test my plan". Announce the mode in the first reply.

## Workflow

### 0. Interactive check

If there is no live user (CI, scheduled, auto-loop, `ULTRACOOK_EXEC=1`): stop. List the missing slots (who / why / success / constraint / out of scope). Do not fill them in.

If the ask is already a typo, rename, or a self-contained one-liner and you can write the restate at ≥95% confidence: write it, ask once, and skip the loop.

### 1. Hypothesize

One sentence + an honest 0–100% number:

```
HYPOTHESIS: You want a standup answer to "how are we doing?", and "dashboard" was the convention that came to mind.
CONFIDENCE: ~30% - missing: who it's for, which metric, what success looks like
```

If you cannot write that sentence, you do not understand the ask yet. Do not skip to questions.

Confidence below ~70% must name what is missing.

### 2. Ask one question

Prefer A/B/C when the answer space is bounded. Always attach your recommended answer.

```
Q: Who is this for on Monday morning?
A) The person running standup (recommended - matches "how are we doing?")
B) Leadership reviewing a weekly pack
C) Individual ICs checking their own numbers
```

On Claude Code, `AskUserQuestion` with one question. Elsewhere, the same prompt in plain text. Wait.

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

Then hand off. Do not start the next skill until they pick one, unless they already said "then plan" / "then brainstorm":

| After confirm | Next |
|---|---|
| How is undecided, one session | `vd:brainstorm` with this file |
| How is undecided and the deciding will not fit one session | `vd:wayfinder` with this file |
| How is decided | `vd:plan` with this file |
| Tiny, mechanical, already specified | they may skip to `vd:cook --quick` - they say so |

## Rationalizations to catch

| Thought | Reality |
|---|---|
| "The ask is clear enough" | If you cannot write the six-line restate right now, it isn't. Step 1 first. |
| "Asking wastes their time" | Four targeted questions are cheap. The wrong PR is not. |
| "I'll figure it out as I build" | Discovery during implementation is rework. |
| "They said whatever I think" | Delegation is not a decision. Offer two concrete options. |
| "I'll give them options so they can pick" | Options widen the search. Asking narrows it. That is `vd:brainstorm`, after this. |
| "Attaching my guess is leading them" | Leading is the point. The risk is sycophancy, not a visible hypothesis. |
| "We've talked enough, I get it" | Can you predict their answer to the next three questions? If not, you don't. |
| "They said yes" | A yes to a vague restate is hollow. Rewrite the six lines. |
| "Non-interactive, I'll assume" | Hard rule 7. Missing slots are a blocker. |

## Red flags

- Three or more questions in one message
- A question with no hypothesis attached
- Accepting "whatever you think" as terminal
- A spec, plan, or option list before the yes
- Skipping Out of scope
- Confidence below 70% with no reason
- Saving the intent file before the yes

## Verification

- [ ] Hypothesis + confidence in the first turn
- [ ] One question at a time, each with a recommended answer
- [ ] Facts looked up, not asked
- [ ] Convention/sophistication answers probed once
- [ ] Six-line restate including Out of scope
- [ ] Explicit yes (not "sounds good")
- [ ] Intent file written to `Reports:` only after the yes
- [ ] Handoff named (`vd:brainstorm` / `vd:wayfinder` / `vd:plan` / user-requested `--quick`)

## Workflow position

**Typically follows:** a vague ask, `vd:ultracook` when want is unclear, or a user saying "interview me" / "grill me"

**Typically precedes:** `vd:brainstorm` (how), `vd:wayfinder` (multi-session deciding), or `vd:plan` (steps)

**Compares to:** `vd:brainstorm` Phase 1 asks clarifying questions to frame *options*. This skill refuses options until want is confirmed. `vd:wayfinder` charts many sessions of decisions once the destination is named.
