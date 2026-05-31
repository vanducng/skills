# Troubleshooting vd:auto-loop

## Loop won't stop after `--cancel`

Possible cause: stale heartbeat with a live PID that's actually a different process
that happened to inherit the slot.

Diagnose:
```bash
cat .auto-loop/heartbeat.json | jq .pid
ps -p <pid>
```

If the process is genuinely unrelated (not `claude`, not the dispatch shell), purge
manually:
```bash
rm .auto-loop/heartbeat.json
bash skills/auto-loop/scripts/uninstall-stop-hook.sh "$(pwd)"
```

## Verifier always fails (false negatives)

The gate runs the verifier **twice** and requires both to pass. If your verifier is
intermittently flaky:

1. Check `.auto-loop/verifier-*.log` for the actual failure reason — flakiness in the
   verifier itself (test ordering, network calls, race conditions) shows up as one
   pass + one fail per iter (`flaky` in gate-history).
2. Fix the verifier. Don't bypass the 2-run dedupe — it's the floor that prevents
   false-positive completion.

## Audit always votes `unmet`

The audit subagent reads goal text + diff summary and votes independently. If it
keeps voting `unmet`:

1. **Goal text is too vague.** Tighten: "all bats tests pass" → "all bats tests in
   tests/parser/ pass and `coverage` reports >80% line coverage on src/parser.py".
2. **Audit subagent unavailable.** When `claude` headless is not on PATH (CI environments
   often skip it), the spawn defaults to `unmet` to keep the gate closed. Check:
   ```bash
   command -v claude || echo "claude headless missing"
   ```
3. **Audit response unparseable.** Check `.auto-loop/audit-{iter}.json` — if reason is
   "audit response unparseable", the audit subagent emitted prose instead of JSON.
   Update the audit prompt template if this is recurring.

## Restart never fires (loop crashes at high context)

Possible cause: `probe-context-pct.sh` returns `unknown` source (no statusline,
no tiktoken). Fall-through to native auto-compact — which may not handle very long
loops.

Diagnose:
```bash
bash skills/auto-loop/scripts/probe-context-pct.sh
# {"pct": -1, "source": "unknown"}  ← no probe path available
```

Workarounds:
1. Install tiktoken: `~/.claude/skills/.venv/bin/python3 -m pip install tiktoken`
2. Lower `max_iterations` so the loop terminates before context bloats.
3. Set `restart_at_context_pct: 50` in `goal.md` to give native compaction more
   headroom.

## Codex delegation refused

```
delegate-to-codex: codex /goal requires 0.128.0+; you have 0.127.0
```
Upgrade: `npm i -g @openai/codex`

```
delegate-to-codex: codex CLI not installed
```
Install per https://developers.openai.com/codex/quickstart, or use the in-house loop.

```
delegate-to-codex: another vd:auto-loop is live (pid=...)
```
A previous session left a live heartbeat. Run `vd:auto-loop --cancel` first.

## Two concurrent loops in same workspace

By design, dispatch refuses to start a second loop in the same workspace. The
heartbeat acts as a per-workspace lock. If you really need parallel loops, run
them in separate clones / worktrees.

## Stop hook runs but loop doesn't continue

Diagnose:
```bash
# Was the hook registered?
jq .hooks.Stop .claude/settings.local.json

# Is the heartbeat alive?
pid=$(jq -r .pid .auto-loop/heartbeat.json)
kill -0 "$pid" && echo alive || echo dead
```

If the PID is dead but the heartbeat persists, the dispatch shell may have exited
(e.g. user pressed Ctrl-C in the terminal that started `vd:auto-loop`). The next
session start will purge the stale heartbeat automatically; or run `--cancel` to
clean up immediately.

## "schema validation failed" on state-rw

```
state-rw: schema validation failed: 'achieved' is not one of [...]
```
The model wrote an invalid status into goal-state.json. The atomic write rejects
it; the previous state remains. Inspect the audit log:
```bash
cat .auto-loop/audit-$(jq -r .iteration .auto-loop/goal-state.json).json
```
If the model is consistently writing bogus statuses, tighten the next-iter-prompt
template (`templates/next-iteration-prompt.md`) to spell out the enum.

## Iteration cap fires before goal reasonable progress

Either:
1. Goal too ambitious for the cap. Raise `--max-iterations` or split into sub-goals
   (run multiple `vd:auto-loop` invocations sequentially via `vd:plan`).
2. The model is thrashing — `drift-watchdog.sh` should escalate after 3 stagnant or
   5-edit iters. Check `.auto-loop/diff-signatures.log` and `file-edits.log`.
