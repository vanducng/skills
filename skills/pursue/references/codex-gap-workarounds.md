# Codex gap workarounds

Three real gaps between Claude Code and Codex tool surfaces that `vd:pursue` v0.2 papers over. Each gap has a workaround documented here with: (1) the problem, (2) the chosen workaround, (3) implementation pointer, (4) isolation test, (5) known limitations.

## Workaround 1: Skill-to-skill invocation

**Gap.** Codex has no native `Skill` tool (no way for a running skill to invoke another skill mid-execution). Codex skills are auto-matched from descriptions when the user prompts; there's no programmatic "call skill X with these args" primitive.

**Workaround.** `codex exec resume --last "use the X skill to: ..."`. The resumed session reads pursue's prompt, auto-matches the named skill based on its description, and runs.

**Implementation.** `scripts/codex-bridge.sh codex_exec_resume_last <skill> <prompt>`. Captures `--json` event stream, parses for final agent message, returns tail for journal capture. Recursion guard via `VD_PURSUE_DEPTH`.

**Isolation test.** From inside a Codex TUI:
```bash
codex exec resume --last "use the vd:plan skill to: --deep small fix"
# Expected: a plan dir is created at plans/{date}-small-fix/.
# Verify: ls plans/ | grep small-fix
```

**Limitations.**
- **Auto-match non-determinism.** If two skills have overlapping descriptions, Codex may pick the wrong one. Mitigation: clear, non-overlapping skill descriptions; Phase 5 dogfood measures false-match rate.
- **`--last` race.** If the user spawned another Codex session between pursue actions, `--last` resolves to that one. Mitigation: Phase 5+ adds explicit `--session-id` capture; v0.2 ships `--last` only.
- **No exec mode.** Inside `codex exec` (non-interactive), `codex exec resume` works, but the resumed session's `ask_user_question` will fail. Pursue intake already refuses `codex exec` mode; this only affects actions invoked AFTER intake.

## Workaround 2: Monitor (event-driven external wait)

**Gap.** Codex has no analog to Claude Code's `Monitor` tool — no way to spawn a background polling script whose stdout lines become events flowing back to the agent. Codex's `--json` event stream is OF the agent itself, not of external commands.

**Workaround.** PostToolUse hook + `additionalContext` injection. pursue registers a hook scoped to a specific `tool_use_id`; the hook polls the user-specified condition and injects status into the model's next turn.

**Implementation.**
- `scripts/codex-monitor-hook.sh` — the hook handler. Reads PostToolUse payload from stdin (via `codex_hook_payload_read`), finds the matching `iterations/NNN-action-monitor.spec.json`, runs the poll command, writes `.result.json` on terminal state, emits `hookSpecificOutput.additionalContext` for the model.
- Pursue executor (in `runtimes/codex.md`) writes the spec before triggering the hook:
  ```json
  {
    "tool_use_id": "...",
    "action": "wait_ci",
    "poll_cmd": "gh pr checks $PR_NUMBER --json bucket -q 'all(.[]; .bucket != \"pending\")'",
    "timeout_seconds": 600,
    "terminal_when": "exit_zero",
    "started_at_epoch": 1716624000
  }
  ```
- After triggering, pursue waits for `.result.json` (next executor iteration checks for it). When present, parses `{status, exit_code, evidence}` and proceeds.

**Isolation test.**
```bash
# Setup: create a fake spec.
mkdir -p /tmp/pursue-monitor-test/iterations
cat > /tmp/pursue-monitor-test/iterations/001-test-monitor.spec.json <<'JSON'
{"tool_use_id":"test","action":"sentinel","poll_cmd":"test -f /tmp/sentinel","timeout_seconds":60,"terminal_when":"exit_zero","started_at_epoch": $(date +%s)}
JSON

# Trigger: simulate hook payload.
cd /tmp/pursue-monitor-test
echo '{"tool_use_id":"test","tool_name":"Bash","tool_response":{}}' \
  | bash ~/skills/skills/pursue/scripts/codex-monitor-hook.sh

# Should emit "still waiting" since /tmp/sentinel doesn't exist yet.

# Now touch the sentinel + re-run hook.
touch /tmp/sentinel
echo '{"tool_use_id":"test","tool_name":"Bash","tool_response":{}}' \
  | bash ~/skills/skills/pursue/scripts/codex-monitor-hook.sh

# Should emit "PASS" + write 001-test-monitor.result.json.
test -f /tmp/pursue-monitor-test/iterations/001-test-monitor.result.json
rm -f /tmp/sentinel
```

**Limitations.**
- **`additionalContext` budget.** Every Monitor invocation injects a status line into the next turn's context. Capped at 200 chars per injection. Long CI waits → many injections → context burn. Watch for this in Phase 5 dogfood; if it's pathological, fall back to a per-action polling loop in `runtimes/codex.md` instead of using hooks.
- **Hook scope.** PostToolUse fires for EVERY tool call. `codex-monitor-hook.sh` is a no-op when there's no matching spec, but every Bash/Read/Edit call goes through it. Acceptable overhead (<10ms typical).
- **Stale spec leaks** when pursue dies mid-wait — covered by `codex-hook-cleanup.sh` (Workaround 4 below).

## Workaround 3: `vd:auto-loop` delegation on Codex

**Gap.** Pursue's `cook` action delegates to `vd:auto-loop` for the iteration loop. On Claude Code, `vd:auto-loop` uses Stop-hook re-feed. On Codex, `vd:auto-loop` has a `--codex` mode that delegates to native `/goal`. Pursue needs to pass `--codex` only when running on Codex.

**Workaround.** `scripts/delegate-to-auto-loop.sh` detects runtime via `detect-runtime.sh` and appends `--codex` to the `vd:auto-loop` invocation args when runtime is `codex`.

**Implementation.** ~5 LOC in `delegate-to-auto-loop.sh` — detect runtime + conditional flag append. Other logic (compound verifier, marker file, recursion guard, precondition checks) unchanged.

**Isolation test.**
```bash
# From a Codex TUI session:
PURSUE_RUNTIME=codex bash ~/skills/skills/pursue/scripts/delegate-to-auto-loop.sh \
  --goal-dir /tmp/fake-goal-dir --action cook
# (will fail on the build-compound-verifier step if no goal.yaml — but check
#  the args before the exit: should contain `--codex` flag in the JSON hint.)

# Compare against Claude Code path:
PURSUE_RUNTIME=claude-code bash ~/skills/skills/pursue/scripts/delegate-to-auto-loop.sh \
  --goal-dir /tmp/fake-goal-dir --action cook
# args should NOT contain `--codex`.
```

**Limitations.**
- **`vd:auto-loop`'s `--codex` mode is TUI-only** (per `~/skills/skills/auto-loop/references/codex-delegation.md`: "codex exec does not (yet) accept /goal as an argument. So delegation is inherently interactive"). The chain `pursue → codex exec resume → vd:auto-loop --codex → /goal` has 3 handoffs. The middle one (`codex exec resume`) IS interactive-capable, so this should work — but Phase 5 dogfood must verify the resumed session can actually exec `/goal`. If it can't, pursue's cook on Codex degrades to running `vd:auto-loop` in non-`--codex` mode (loses /goal's pause/resume + cross-surface sync).
- **No Codex /goal pause/resume integration.** Pursue's `kill` sub-verb writes `state.terminal=abandoned`; on Codex with `/goal` running, the user must also `/goal cancel` separately. Document in the kill output. v0.3 wires this.

## Workaround 4: Hook teardown (SessionStart sweep)

**Gap.** If pursue dies mid-Monitor-wait, the registered hook stays alive — and the `iterations/*-monitor.spec.json` file persists. Subsequent Codex sessions will inherit a pre-registered hook with a stale spec.

**Workaround.** `scripts/codex-hook-cleanup.sh` runs as a Codex SessionStart hook. It sweeps `iterations/*-monitor.spec.json` files older than 24h that have NO matching `.result.json` (i.e. died mid-wait).

**Implementation.** Self-contained bash script. Searches `$HOME/git`, `$HOME/Projects`, `$HOME/Code`, and `$PWD` for spec files matching the stale criteria. Logs each sweep to `~/.pursue/cleanup.log`. Emits an optional `systemMessage` to the user if anything was swept.

**Isolation test.**
```bash
# Setup: create a stale spec.
mkdir -p /tmp/pursue-stale/iterations
cat > /tmp/pursue-stale/iterations/001-stale-monitor.spec.json <<'JSON'
{"tool_use_id":"old","action":"old"}
JSON
touch -t 202401010000 /tmp/pursue-stale/iterations/001-stale-monitor.spec.json

# Run cleanup (simulating SessionStart hook trigger from $PWD).
cd /tmp/pursue-stale
echo '{}' | bash ~/skills/skills/pursue/scripts/codex-hook-cleanup.sh

# Verify: spec is gone, cleanup log has entry.
test ! -f iterations/001-stale-monitor.spec.json
grep stale ~/.pursue/cleanup.log | tail -1
```

**Limitations.**
- **Search roots are heuristic.** If user's worktrees live outside `$HOME/git|Projects|Code`, stale specs there won't be swept. Mitigation: extend SEARCH_ROOTS array.
- **24h threshold is generous.** A real wait > 24h would be falsely swept. v0.3 reduces to 4h once dogfood confirms it's safe.

## Hook registration (manual setup until v0.3 automates)

Codex hooks are registered in user-level config (per [Codex Hooks docs](https://developers.openai.com/codex/hooks)). v0.2 ships the hook SCRIPTS but does NOT auto-register them. User must add to their Codex config:

```toml
# ~/.codex/config.toml (or equivalent)
[[hooks.PostToolUse]]
matcher = ".*"

[[hooks.PostToolUse.hooks]]
type = "command"
command = "bash ~/.agents/skills/pursue/scripts/codex-monitor-hook.sh"

[[hooks.SessionStart]]
matcher = ".*"

[[hooks.SessionStart.hooks]]
type = "command"
command = "bash ~/.agents/skills/pursue/scripts/codex-hook-cleanup.sh"
```

v0.3 ships an `install-hooks` sub-verb that does this automatically.

## Cross-runtime portability invariant

All workarounds preserve the v0.1 invariant: **`goal.yaml` + `state.json` on disk are the source of truth.** No workaround stores state in Codex-specific opaque blobs (`~/.codex/sessions/*.jsonl` is read-only forensics, not authoritative state). This is what makes Phase 5's keystone test (cross-runtime resume) work.
