# Runtime detection

`vd:ultracook` works across Claude Code and Codex (TUI + `codex exec`). The top-level `SKILL.md` is a thin router that detects which runtime is invoking it and dispatches to `runtimes/claude-code.md` or `runtimes/codex.md`. This file documents the detection logic.

## Implementation

`scripts/detect-runtime.sh` is the canonical detector. Stdout is one of `claude-code` / `codex` / `codex-exec`. Exit 3 on unknown (diagnostic to stderr). `scripts/test-detect-runtime.sh` is the truth-table regression guard - run it after any change here.

## Detection precedence

Top wins:

1. **`ULTRACOOK_RUNTIME` env override** (`claude-code` / `codex` / `codex-exec`) - explicit, deterministic. Use in CI or wrappers.
2. **Claude env signal** - any of `CLAUDE_PROJECT_DIR`, `CLAUDE_TOOL_USE_ID`, `CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_ENTRYPOINT` → `claude-code`. **CLAUDE wins even when Codex is also set** (see below); a one-line note goes to stderr so the rare reverse case can be corrected with `ULTRACOOK_RUNTIME=codex`.
3. **Codex env signal** - `CODEX_SESSION_ID` set → `codex`, or `codex-exec` when the explicit exec contract `ULTRACOOK_EXEC=1` is set.
4. **CLI-on-PATH probes** - `codex` available + `claude` not → `codex` (`codex-exec` if `ULTRACOOK_EXEC=1`). `claude` available → `claude-code`.
5. **Codex recency fallback (last resort)** - a Codex JSONL under `~/.codex/sessions/` modified within 5 min + `codex` on PATH → `codex`. **Demoted below the PATH probes** because it manufactures `codex` false-positives for anyone who used codex recently while now in Claude Code.
6. **Else** - unknown (exit 3); refuse with an explicit `ULTRACOOK_RUNTIME` recommendation.

## Why CLAUDE wins when both signals are present

Codex's `shell_environment_policy.inherit=all` leaks `CODEX_SESSION_ID` into child shells - including a Claude Code session launched from a Codex shell - so "both set" most often means "Claude is the active runtime, Codex is an ancestor." The `CLAUDE_CODE_*` vars are set by the active Claude process. Routing to `claude-code` (with a stderr note) is therefore the correct default; the v0.2 "fail-closed on both" would force an override on every normal invocation in such a shell. Override with `ULTRACOOK_RUNTIME=codex` for the inverse (a Codex session with leaked `CLAUDE_*`).

## `codex exec` is an explicit contract

No env var distinguishes `codex exec` (non-interactive) from the `codex` TUI in codex-cli - there is no `CODEX_EXEC`/`CODEX_SANDBOX` marker, and TTY/process checks are unreliable (Claude's Bash tool is also non-TTY). So exec mode is detected ONLY via the explicit `ULTRACOOK_EXEC=1` (or `ULTRACOOK_RUNTIME=codex-exec`). In `codex-exec`, the router skips the interactive intake and reads default-answer flags - see `references/codex-runtime.md` → "CI / non-interactive usage".

## Why env vars over PATH-probe

PATH probes (`command -v codex` / `command -v claude`) only confirm the CLI is INSTALLED, not which one is CURRENTLY INVOKING this skill. A user with both CLIs installed but running Claude Code should NOT be routed to Codex just because `codex` is on PATH. Env vars are the authoritative signal for "who's calling me right now."

## What if neither runtime is detectable?

Happens when a user runs a script directly from a plain shell, or a test harness strips env. The detector exits 3 (`unknown`); the SKILL.md router prints an actionable "Set `ULTRACOOK_RUNTIME=…`" message. Plain-shell users can also bypass the router by calling individual scripts directly - they're all runtime-agnostic by design.
