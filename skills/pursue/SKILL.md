---
name: pursue
description: "Goal-driven workflow orchestrator. Intake → worktree → plan → cook → ship → verify. Delegates iteration to `vd:auto-loop`. v0.2 supports Claude Code + Codex TUI (dual runtimes via `runtimes/{claude-code,codex}.md` dispatch). Use to drive a feature/fix from short-goal prompt to verified deployment with hard guardrails and resume-across-compaction."
license: MIT
argument-hint: "[<short goal> | resume | status | kill --reason <text> | resolve <goal-dir>] [--reuse] [--manual | --semi | --auto]"
metadata:
  author: vanducng
  version: "0.2.0"
---

# Pursue — runtime router

This file is the entry point for `vd:pursue`. It detects which runtime is invoking (Claude Code or Codex) and dispatches to the right adapter under `runtimes/`. Most users won't read this file — they'll land in the adapter directly.

## Quick reference

| Form | Action |
|---|---|
| `vd:pursue "<goal>"` | New goal — intake → goal.yaml + state.json → executor loop |
| `vd:pursue` (no args) | Resume — auto-detect most recent in-progress goal-dir, skip intake, jump to executor |
| `vd:pursue status` | Print one-screen status (scripts/status.sh — runtime-agnostic) |
| `vd:pursue kill --reason "<text>"` | Write terminal=abandoned (scripts/kill.sh — runtime-agnostic) |
| `vd:pursue resolve <goal-dir>` | Dry-run the resolved workflow (scripts/resolve-workflow.sh — runtime-agnostic) |

Flags: `--reuse` (no worktree), `--manual` / `--semi` (default) / `--auto` (autonomy).

## Runtime dispatch

1. Run `bash scripts/detect-runtime.sh`. Output is `claude-code` or `codex`.
2. If exit 2 (ambiguous): refuse with the diagnostic. Set `PURSUE_RUNTIME=claude-code` or `PURSUE_RUNTIME=codex` and retry.
3. If exit 3 (unknown — no env signals + no CLI on PATH): print "Cannot detect runtime. Set `PURSUE_RUNTIME` env var explicitly."
4. Else follow the runtime body:
   - `claude-code` → see `runtimes/claude-code.md`
   - `codex` → see `runtimes/codex.md`

The sub-verbs (`status`, `kill`, `resolve`) short-circuit the runtime dispatch — they invoke `scripts/<sub-verb>.sh` directly because those scripts are runtime-agnostic.

## Hard rules (apply across both runtimes)

1. **State on disk is source of truth.** `plans/goals/{slug}/goal.yaml` + `state.json` survive context compaction. The Phase 5 keystone test proves goals are portable across runtimes via state.json — same goal can be started on one runtime and finished on the other.
2. **Loop primitive = `vd:auto-loop` (Stop hook on Claude / `--codex` → native `/goal` on Codex).** Not `ScheduleWakeup`. Monitor is only for event-driven async waits.
3. **No auto-merge on the skills repo.** `vd:ship official` (no `--auto`).
4. **Closed-set verifier vocabulary + `shell` escape.** Six built-ins + `shell`.
5. **Two verifier layers.** Per-action verifiers (cook iteration) vs workflow-level `target.verifiers` (verify_* phases). Never mix.
6. **Hard guardrails.** Global iter cap (30), per-phase retry caps (3 rebases, 2 CI reruns), same-signature failure recognizer, token-cap prompt-back at 80%.
7. **Composes existing `vd:*` skills** — never reimplements.

## Architecture

```
SKILL.md (this file)                       — router (detect + dispatch)
runtimes/
  claude-code.md                           — Claude Code adapter (v0.1 body)
  codex.md                                 — Codex adapter (Phase 2 fills body; Phase 1 is stub)
  detect.md                                — runtime detection spec
scripts/
  detect-runtime.sh                        — NEW: runtime detector
  init-goal.sh + 13 v0.1 scripts           — runtime-agnostic; both runtimes call them
  codex-bridge.sh                          — NEW Phase 2: codex exec subprocess + hook helpers
  codex-monitor-hook.sh                    — NEW Phase 3: PostToolUse Monitor analog
  codex-hook-cleanup.sh                    — NEW Phase 3: SessionStart stale-hook sweeper
  notify.sh                                — NEW Phase 4: PushNotification analog
references/                                — 11 docs, runtime-agnostic (except codex-runtime.md)
  codex-runtime.md                         — Codex specifics (renamed from codex-deferred.md in Phase 1)
  codex-gap-workarounds.md                 — NEW Phase 3: Skill-to-skill / Monitor / vd:auto-loop --codex bridges
projects/                                  — 4 TOML profiles, runtime-agnostic
```

## See also

- `runtimes/detect.md` — detection precedence + ambiguity rules
- `references/codex-runtime.md` — Codex-specific notes
- `~/skills/plans/260525-1501-pursue-v0.2-codex/` — v0.2 implementation plan
- `README.md` — install + quick-start for both runtimes
