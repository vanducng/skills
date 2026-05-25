---
phase: stub
version: 0.2.0-phase-1
---

# Codex runtime adapter — Phase 1 stub

This file is the Codex-flavor body of `vd:pursue`. **Phase 2 of v0.2 fills the executor protocol.** Phase 1 ships ONLY this stub.

If you reached this file by invoking `/vd:pursue` from a Codex session: the executor is not yet implemented for Codex. Your options:

1. **Wait for v0.2 Phase 2.** Plan dir: `~/skills/plans/260525-1501-pursue-v0.2-codex/`. Phase 2 ships intake + sequential executor for Codex (~3h work).
2. **Use Claude Code instead.** v0.1 + v0.2-Phase-1 fully work on Claude Code. Invoke `/vd:pursue` from a Claude Code session.
3. **Drop to manual.** All bash scripts under `scripts/` are runtime-agnostic. You can run them directly:
   ```
   bash ~/.codex/skills/pursue/scripts/init-goal.sh "<goal>"        # intake (no AskUserQuestion — pass via env vars)
   bash ~/.codex/skills/pursue/scripts/resolve-workflow.sh <goal-dir>  # dry-run
   ```
   See `references/codex-runtime.md` for the bridge details + workarounds.

## Sub-verbs (already work via shared scripts — call directly)

```
bash ~/.codex/skills/pursue/scripts/status.sh        # auto-detect most recent in-progress goal
bash ~/.codex/skills/pursue/scripts/kill.sh --goal-dir <dir> --reason "<text>"
bash ~/.codex/skills/pursue/scripts/resolve-workflow.sh <goal-dir>
```

These are runtime-agnostic; they work from any shell.

## Phase 2 sneak peek (what this file becomes)

```
1. Entry routing (mirror runtimes/claude-code.md):
   - bare /vd:pursue → resume-mode (auto-detect most recent in-progress goal)
   - /vd:pursue "<goal>" → intake mode
   - /vd:pursue status | kill | resolve → sub-verb dispatch
2. Intake (Codex flavor): 4× `ask_user_question` mirroring the Claude Code intake.
3. Sequential executor: read state → decide next action → gate-check (Codex's ask_user_question for gates) →
   dispatch via codex-bridge.sh / codex exec resume → verify → journal → update state → loop.
4. codex exec (non-interactive) handling: error out with actionable message; default-answer-mode is v0.3.
```

See plan: `~/skills/plans/260525-1501-pursue-v0.2-codex/phase-02-build-codex-intake-and-executor.md`.

## References (runtime-agnostic)

- `references/goal-schema.md` — `goal.yaml` v1
- `references/state-schema.md` — `state.json` v1
- `references/action-vocab.md` + `.yaml` — 21 actions
- `references/verifier-vocab.md` + `.yaml` — 7 verifier types
- `references/architecture.md` — two-layer SKILL.md ↔ bash invariant
- `references/codex-runtime.md` — Codex-specific notes + v0.2 roadmap
