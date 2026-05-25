# Codex runtime support — deferred to v0.2

`vd:pursue` v0.1 is **Claude Code only**. Codex (OpenAI's coding agent) is not supported in this release. This file documents why + the path forward.

## TL;DR

The research report (`~/skills/plans/reports/researcher-260525-1158-codex-runtime-support.md`) concluded:

> **Recommendation: Ship Claude-Code-first MVP (v0.1), defer Codex to v0.2.**

Cross-runtime single `SKILL.md` is infeasible. Codex `/goal` is TUI-driven with opaque internal state; Claude Code's Stop-hook (the loop primitive `vd:auto-loop` uses) is intra-session with transparent file-based state. The two diverge enough that a single skill body would be 50% adapter code.

The right v0.2 approach is the **adapter pattern**: shared spec files (`goal-schema.md`, `action-vocab.yaml`, etc.) + runtime-specific impl branches in `runtimes/claude-code.md` and `runtimes/codex.md`. Estimate: 2 sprints (~22h).

## What Codex CAN do today (without v0.2 work)

If you're running Codex now:

- **`vd install codex pursue`** will symlink this skill into `~/.codex/skills/pursue/`. The skill files are visible to Codex.
- **The bash scripts work** — same `~/.claude/skills/.venv/` Python, same file layouts. `init-goal.sh`, `resolve-workflow.sh`, etc. are runtime-agnostic.
- **Manual mode** is largely possible — you (the Codex user) can call `bash init-goal.sh`, then `bash resolve-workflow.sh`, then manually invoke `/plan`, `/cook`, etc.

What you CAN'T do today:

- The executor loop (Phase 3+ flow) depends on tools Codex doesn't have (`AskUserQuestion`, `Monitor`, `Skill`, `Agent`). The closest analog is Codex's `/goal` but it's a different shape.
- Mid-session iteration like Claude Code's Stop-hook re-feed.

## The closest existing primitive on Codex

`/vd:auto-loop --codex` delegates to Codex's native `/goal` command (requires codex ≥ 0.128.0 + ChatGPT auth). Use it for single-shot verifier loops (the "drive cook to done" pattern). It's NOT a workflow orchestrator — there's no e2e "intake → plan → cook → ship → verify" shape.

For now: combine `vd:auto-loop --codex` with manual ship/verify steps. This is verbose but functional.

## v0.2 plan sketch

1. **Spec freeze** — `goal-schema.md`, `state-schema.md`, `action-vocab.yaml`, `verifier-vocab.yaml`, `projects/*.toml` stay as-is. They're runtime-agnostic.
2. **Runtime adapter layer**:
   - `runtimes/claude-code.md` — the current SKILL.md body (executor protocol, AskUserQuestion / Skill / Monitor calls). Renamed; the top-level `SKILL.md` becomes a thin router.
   - `runtimes/codex.md` — Codex equivalent. Uses `/goal` for iteration, Codex's prompt-back primitives for gates, polling for "Monitor" (no event-driven analog yet).
3. **Top-level `SKILL.md`** — detects runtime (env var? capability probe?) + dispatches to the right adapter. Bash scripts are unchanged.
4. **Codex-specific gaps**:
   - No `Monitor` → polling loop for `wait_ci` / `image_build_wait`. Slower but works.
   - No `Agent` subagent → audit step degrades to inline review or skip.
   - No `TaskCreate`/`TaskUpdate` → file-based TODO tracking under `iterations/`.
5. **Dogfood Codex run** — one real fix end-to-end via Codex; document gaps + workarounds.

Total estimate: 2 sprints solo. v0.2 is the right time to do this, after v0.1 has matured + revealed any spec-level issues that would invalidate cross-runtime work.

## Why we didn't ship v0.2 in v0.1

- Time-to-value: v0.1 unblocks the goclaw / infra workflows the user runs daily. Waiting for cross-runtime parity would delay that.
- Codex API surface evolution: Codex is at 0.133 today and shipping new primitives every few weeks. A cross-runtime adapter built against a moving target is short-lived.
- Adapter pattern needs the v0.1 spec to settle before it can wrap. Premature abstraction.

## How to track this

- This file = the authoritative deferral doc.
- The brainstorm brief (`plans/reports/brainstorm-260525-1143-e2e-ship-skill.md`) lists Codex as out-of-scope.
- The research report (`plans/reports/researcher-260525-1158-codex-runtime-support.md`) has the full feasibility analysis.
- A v0.2 plan dir will land at `~/skills/plans/{date}-pursue-v0.2-codex/` when the work starts.

## If Codex ships a Claude-Code-compatible tool model

Watch for any of:
- `AskUserQuestion` analog in Codex
- Async-event Monitor primitive
- Stop-hook or similar intra-session re-feed
- Subagent dispatch with fresh-context audit

Any one of these dramatically reduces v0.2's adapter complexity. Currently none are announced (as of 2026-05-25). Re-evaluate if Codex's 0.150+ releases change this.
