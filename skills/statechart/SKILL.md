---
name: statechart
description: "Checks a TLA+ model of something that moves between states (a checkout, an upload, a protocol, a job with retries) with the TLC model checker and draws it as a Mermaid statechart in the reader's words, marking each state that breaks a rule and the shortest path to it. Use when asked to 'draw the states', 'chart how this flow works', 'statechart', 'can this ever happen', 'check this flow keeps the rule', 'model the lifecycle', or to show a bug about order, duplicates, retries or late events as a path through states. Declines work with no states, such as a pure function. Not for architecture or sequence diagrams (vd:archify, vd:diagram-design)."
license: MIT
argument-hint: "<the flow, its rules, or the code to chart>"
metadata:
  author: vanducng
  version: "0.1.1"
  upstream: "https://github.com/cursor/plugins/tree/main/pstack/skills/statechart"
  upstream_commit: "6b0300214a09fd6029cfb7077043125758cd1fd2"
  upstream_license: "MIT, Copyright (c) 2026 Lauren Tan (LICENSE.txt)"
---

# statechart

A chart of how a system moves between states, checked by TLC, in the words of the person who decides whether the behavior is right: the reader. A hand-drawn diagram proves nothing; this one comes from every state the model can reach.

`SC=<this skill's directory>/scripts/statechart`

## First: does the work have states?

Use it when the work has three or more states, or a rule about order, duplicates or retries (charged twice, a late webhook, a retry after cancel). Otherwise decline: say the code or flow has no states worth charting (a pure function maps input to output; a single request and reply has no lifecycle), write no model and draw no diagram, and suggest a table of inputs and outputs as tests instead.

## Steps

1. **Name the states and the rules** in the reader's words. Rules come from the reader. When you chart code, today's behavior is the code's: read every guard and every path that changes state, and keep what the code does, not what it should do.
2. **Write the model** in the folder the user names, else a scratch folder outside the repo: `Spec.tla` and `Spec.cfg`. Each rule the reader agrees to is an `INVARIANT`; never weaken one to make it hold. Keep constants small. Read `references/spec.md` before writing it: `Next` as a disjunction of named actions, and end states that would otherwise break `NoDeadlock`.
3. **Write the view** `view.mjs`: `state(vars)` returns the reader's label for a state, `step(action, from, to)` the arrow's label as the reader sees it happen ("the webhook arrives late"). No variable or function names in labels. About 20 arrows at most. `references/view.md` covers parent states, parallel regions, conditions in brackets, colors and hiding steps.
4. **Run it:** `"$SC" Spec.tla --view view.mjs --out chart`. Exit 0 means every rule holds, 1 means one breaks; both write `chart/report.md` and `chart/chart.mmd`. Any other exit is an error in the model: fix it and run again.
5. **Read the report** (`references/report.md`): `breaks` and `mayBreak` marks, the shortest path to each broken rule, and the rules it could not check.
6. **Hand off:**
   - show `chart.mmd` as a `mermaid` code block;
   - one line per broken rule: the rule, the reader's sentence for it, and the path as the report numbers it;
   - what the model leaves out, and which steps the chart hides;
   - the command that makes the files again, with a new `--out` folder.
7. **When the model describes code,** replay each bug path against the real code as a test or a live repro, one step per action. If the bug does not occur, the model is wrong until you show it is not.

## Brownfield work (from shape)

Draw two charts: **today**, modeled from the code, and **intended**, from the reader's rules. The reader approves the rules; each approved rule becomes an invariant of the intended model. Each invariant and each bug path on the today chart becomes a test line in the record's proof contract (for example "a late webhook after cancel charges nothing: test fails on the old code, passes on the new").

## Toolchain

The command needs Node 22.18 or later (or Bun 1.1.5, Deno 2). It finds TLC in this order: `TLA2TOOLS` (path to `tla2tools.jar`) with `JAVA`; the pinned mise installs (`http:tla2tools` 1.7.4 and `java@temurin-25`), which work offline once installed; otherwise it installs them with mise, which needs the network. Set both `TLA2TOOLS` and `JAVA` when the `java` on `PATH` is not Java 11 or later.

Render an image only when the user asks for one, or when the chart is too large to read as text: `references/render.md`.

## Rules

- **TLC draws the chart.** Never hand-draw or edit `chart.mmd`; change the model or the view and run again.
- **The reader's words, not the code's.** A label a reader cannot act on ("status=waiting") is a defect.
- **A broken rule stays visible.** Never merge two states that break different rules, and never hide a state on a bug path.
- **No states, no chart.** Declining is a correct answer.
