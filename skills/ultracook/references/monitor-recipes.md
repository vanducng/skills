# Monitor recipes

Patterns for using Claude Code's `Monitor` tool from `vd:ultracook` actions that need to wait on long-running external work (CI, GitHub Actions builds, kubectl rollouts) without blocking the session.

**Monitor is NOT a loop primitive** - it's an event-driven async wait. `vd:auto-loop` (via Stop hook) is the loop primitive for iteration; Monitor is for "watch this stream of stdout lines, emit events as they arrive, exit when done."

## Shape

```
Monitor(
  description: "<short label shown in notifications>",
  command: <bash script that prints one line per event and exits when done>,
  timeout_ms: <reasonable cap; default 5min, max 60min>,
  persistent: false   # true only for session-length watches
)
```

Each stdout line of the command becomes a notification message back to the assistant. The assistant continues other work; events arrive in-band as `<task-notification>` messages.

## Recipe 1 - `wait_ci` (PR CI watch)

```bash
prev=""
while true; do
  s=$(gh pr checks $PR_NUMBER --repo $REPO --json name,bucket 2>/dev/null || echo "[]")
  cur=$(echo "$s" | jq -r '.[] | select(.bucket!="pending") | "\(.name): \(.bucket)"' | sort)
  # Emit only NEW completions since last poll (set-difference).
  comm -13 <(echo "$prev") <(echo "$cur")
  prev=$cur
  # Exit when every check is non-pending.
  echo "$s" | jq -e 'length>0 and all(.bucket!="pending")' >/dev/null 2>&1 && { echo "all_done"; break; }
  sleep 30
done
```

**Notifications emitted:** `<name>: <bucket>` per check completion + `all_done` when terminal.

**Gotchas:**
- `gh pr checks` returns `[]` on auth failure - the `|| echo "[]"` keeps the loop alive.
- `bucket=success` is a green check; `bucket=fail` is red; `bucket=pending` is still running. We exit when NONE are pending, regardless of color.
- The verifier (`ci_green`) runs ONCE after monitor exits; it interprets "all non-pending" + "all conclusion=success" as the pass condition.

## Recipe 2 - `image_build_wait` (GHA workflow run watch)

```bash
prev_done=""
while true; do
  # Read both the run-level status and the per-job status array.
  run_status=$(gh run view $RUN_ID --repo $REPO --json status -q .status 2>/dev/null || echo "unknown")
  cur_done=$(gh run view $RUN_ID --repo $REPO --json jobs -q '.jobs[] | select(.status=="completed") | "\(.name): \(.conclusion)"' 2>/dev/null | sort)
  if [ -n "$cur_done" ]; then
    comm -13 <(echo "$prev_done") <(echo "$cur_done")
    prev_done=$cur_done
  fi
  if [ "$run_status" = "completed" ]; then
    conc=$(gh run view $RUN_ID --repo $REPO --json conclusion -q .conclusion 2>/dev/null)
    echo "build_complete: $conc"
    break
  fi
  sleep 45
done
```

**Notifications emitted:** `<job-name>: <conclusion>` per job + `build_complete: <success|failure>` when terminal.

**Zsh gotcha:** the variable name `status` is read-only in zsh (special shell var). We use `run_status` instead. This was a real bug during the goclaw v3.23.4 image-build cycle that informed the monitor-script pattern.

## Recipe 3 - `rollout_check` (kubectl rollout status)

```bash
kubectl --context $KUBE_CONTEXT rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=180s
```

This is a single command, not a polling loop - `kubectl rollout status` blocks until the deployment is fully rolled out OR the timeout fires. Wrap it in Monitor so the session doesn't block 3 minutes inline.

**Exit codes:**
- 0 = rollout completed successfully → the per-action verifier (`cmd_exits_zero`) passes.
- non-zero = timeout / rollback / failure → verifier fails, executor counts as same-signature failure.

## Recipe 4 - log-pattern watch (generic, not currently wired)

For when a future action needs to wait until a log line appears (e.g. "ready to accept connections"):

```bash
tail -F /path/to/app.log | grep --line-buffered -E "Ready to accept|ERROR|Traceback" | head -1
```

`--line-buffered` is critical - without it `grep`'s buffering can hold events for minutes before flushing.

## Coverage principle (lesson from `vd:auto-loop`)

Silence is not success. A Monitor command that prints only the happy-path marker stays silent through a crash - and silence looks identical to "still running." Every Monitor command should emit on both success AND failure signatures:

```bash
# Wrong - silent on crash, hang, or non-success exit:
tail -F run.log | grep --line-buffered "elapsed_steps="

# Right - alternation covers progress + failures we'd act on:
tail -F run.log | grep -E --line-buffered "elapsed_steps=|Traceback|Error|FAILED|Killed|OOM"
```

## When NOT to use Monitor

- The wait is < 30 seconds → just `sleep` in the dispatch bash, no overhead.
- The wait is between actions in a loop body → `vd:auto-loop`'s Stop hook handles iteration, not Monitor.
- The wait is "wake me at 10am tomorrow" → `ScheduleWakeup` (different primitive).
- The work is genuinely synchronous (e.g. `go test`) → just run it; tail the log in the iteration journal afterwards.

Monitor's strength is the EVENT model. If your wait has no events worth emitting one-by-one, use a different primitive.
