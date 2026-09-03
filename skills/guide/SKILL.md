---
name: guide
description: "Catalog front door. Map an ask to the right vd: skill and the next hand-off so agents and humans do not memorize the catalog. Use when the user asks 'which skill', 'how do I start', 'what should I run', 'guide me', 'router', or when several skills could apply (review lenses, browser ladder, diagram picker, get-it-done paths)."
license: MIT
argument-hint: "[what you are trying to do]"
metadata:
  author: vanducng
  version: "0.1.0"
---

# Guide

This skill picks the next skill. It does not interview, plan, or edit source. Name one skill (plus a flag if needed), say why, and stop unless the user asks you to run it.

## Delivery spine

One path: **interview → brainstorm → plan → cook → ship**. `vd:ultracook` runs the smallest slice of the same path.

| If | Use |
|---|---|
| Who / why / success / out of scope is missing | `vd:interview` |
| A plan or idea needs its decisions walked | `vd:interview --grill` |
| Deciding will not fit one session | `vd:interview --wayfinder` |
| Want is clear, how is not | `vd:brainstorm` |
| Approach is picked | `vd:plan` → `vd:cook` → `vd:code-review` → `vd:ship` |
| Something is broken | `vd:debug` → `vd:fix` |
| Drive the whole thing | `vd:ultracook` |

## Three "just get it done" paths

| Path | Pick when |
|---|---|
| `vd:cook --quick` | Tight, no plan, one surface. You will still verify and test. |
| `vd:fix` | Known bug, narrow blast radius. `--quick` on cook covers similar ground. |
| `vd:ultracook` (direct) | User asked to orchestrate and the task is trivial. Ultracook classifies; it should not open a goal-dir. |

If two apply, prefer `vd:fix` for failures, `vd:cook --quick` for small builds, `vd:ultracook` when the user wants a conductor.

## Review lenses

| Question | Skill |
|---|---|
| Ready to land? | `vd:code-review` (posts on a PR) |
| Does it fit the codebase / is it slop? | `vd:code-review --refactor` (local) |
| Can it read easier with behavior frozen? | `vd:simplify` |
| What shape should this have had from day one? | `vd:simplify --aggressive` |
| What can an attacker do? | `vd:security` |
| Does this plan hold up? | `vd:plan --audit` |
| Deterministic owned reviewer CLI? | `vd:miucr` |

## Browser escalation

| Rung | Skill |
|---|---|
| Logged-in browsing in an isolated ego space | `vd:ego-browser` |
| Persistent local Chrome, CDP, video, network mocks | `vd:agent-browser` (+ `vd:browser-profile` to launch) |
| Vendor-free raw-CDP traces | `vd:browser-trace` |
| CAPTCHA / anti-bot / proxy (Browserbase) | `vd:browser` |
| Logged-in end-to-end flows | `vd:web-e2e` |
| Performance | `vd:web-perf` |

Start local. Escalate to `vd:browser` only when a local run hits a wall.

## Diagram picker

| Need | Skill |
|---|---|
| Explain the current topic in chat | `vd:show-me` |
| ASCII sketch | `vd:text-diagram` |
| General SVG / raster | `vd:diagram` |
| Editable whiteboard | `vd:excalidraw` |
| Polished, accessible HTML/SVG with layout guidance | `vd:diagram-design` |

## Discover / decide / iterate

| Need | Skill |
|---|---|
| Map the repo | `vd:scout` |
| Cited comparison of known options | `vd:research` |
| Edge cases / blast radius | `vd:scenario` |
| Keep iterating one command | `vd:auto-loop` |
| Mechanical quality grind | `vd:optimize-loop` |
| Which skill do I run? | this skill |

## Output

1. Restate the ask in one line.
2. Name **one** skill id (and flag).
3. One sentence why the neighbors are wrong.
4. The next hand-off after that skill finishes.

Do not load the target skill's body unless the user says to run it.
