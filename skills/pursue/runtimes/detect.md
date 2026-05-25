# Runtime detection

`vd:pursue` works in two runtimes: Claude Code and Codex (TUI). The top-level `SKILL.md` is a thin router that detects which runtime is invoking it and dispatches to `runtimes/claude-code.md` or `runtimes/codex.md`. This file documents the detection logic.

## Implementation

`scripts/detect-runtime.sh` is the canonical detector. Stdout is one of `claude-code` / `codex`. Exit 2 on ambiguous, exit 3 on unknown — both with diagnostic to stderr.

## Detection precedence

Top wins:

1. **`PURSUE_RUNTIME` env override** (`claude-code` / `codex`) — explicit, deterministic. Use this in CI or scripts that wrap pursue.
2. **Ambiguous fail-closed** — if both Claude (`CLAUDE_PROJECT_DIR` / `CLAUDE_TOOL_USE_ID`) AND Codex (`CODEX_SESSION_ID`) env vars are set, refuse. Caller must set `PURSUE_RUNTIME` explicitly. Rare (happens only in nested sessions or contrived testing).
3. **Claude env signal** — `CLAUDE_PROJECT_DIR` or `CLAUDE_TOOL_USE_ID` set → `claude-code`.
4. **Codex env signal** — `CODEX_SESSION_ID` set → `codex`.
5. **Codex recency fallback** — if `CODEX_SESSION_ID` doesn't propagate to bash subshells (verified during Phase 1 — see "Env propagation probe" below) AND a Codex JSONL session file under `~/.codex/sessions/` was modified within the last 5 min AND `codex` is on PATH → `codex`. This catches the "in a Codex TUI shell, but the env var didn't propagate to a `bash` subprocess" case.
6. **CLI-on-PATH probes** — if `codex` available + `claude` not → `codex`. If `claude` available → `claude-code`.
7. **Else** — unknown; refuse with explicit `PURSUE_RUNTIME` recommendation.

## Why fail-closed on ambiguity

If a user is running Claude Code inside a Codex shell (or vice versa), routing them to the wrong adapter silently is worse than asking once. Set `PURSUE_RUNTIME=claude-code` or `PURSUE_RUNTIME=codex` to disambiguate.

## Env propagation probe

Phase 1 step 3 runs `bash -c 'env | grep -i codex'` inside a Codex TUI to verify `CODEX_SESSION_ID` propagates. The outcome determines whether step 5 (recency fallback) is actually load-bearing:

- **If env DOES propagate:** step 5 is defensive, only fires in edge cases (deeply nested shells, sourced rc files unsetting vars).
- **If env DOES NOT propagate:** step 5 is the primary Codex signal for any bash-tool call (because every bash call from Codex spawns a fresh shell).

**Probe result (fill in during Phase 1 step 3):** _TBD — to be filled by the contributor running the cook_.

## Why env vars over PATH-probe

PATH probes (`command -v codex` / `command -v claude`) only confirm the CLI is INSTALLED, not which one is CURRENTLY INVOKING this skill. A user with both CLIs installed but running Claude Code should NOT be routed to Codex just because `codex` is on PATH. Env vars are the authoritative signal for "who's calling me right now."

## What if neither runtime is detectable?

This happens when:
- A user runs `bash scripts/init-goal.sh` directly from a plain shell (no agent at all).
- A test harness invokes pursue with stripped env.

The detector exits 3 with `unknown`. The SKILL.md router (top-level) handles this by printing an actionable message: "Set PURSUE_RUNTIME=claude-code or PURSUE_RUNTIME=codex." Plain-shell users can also bypass the router entirely by calling individual scripts directly — they're all runtime-agnostic by design.
