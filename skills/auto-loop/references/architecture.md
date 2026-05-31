# vd:auto-loop architecture

## One-page diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER (Claude Code)                        │
│       vd:auto-loop "<goal>" --verify "<cmd>" [opts]            │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
                 scripts/dispatch.sh  (route by flag)
                  │       │       │       │
        ┌─────────┘       │       │       └─────────┐
        ▼                 ▼       ▼                 ▼
   --status         --cancel   --codex           default
   status-          cancel-    delegate-         install Stop hook +
   reader.sh        loop.sh    to-codex.sh       seed state file
                                                 │
                                                 ▼
                            ┌────────────────────────────────────┐
                            │ Claude Code session loop           │
                            │ ─────────────────────────────────  │
                            │  iter N → model edits files →      │
                            │  writes goal-state.json → STOP     │
                            └────────────────┬───────────────────┘
                                             ▼
                                   stop-hook-handler.sh
                                  ┌──────────┴───────────┐
                                  ▼                      ▼
                        check-budget-caps.sh   (status?)
                         (iter/tokens/wall)        │
                                  │                ├─ pursuing → next-iter prompt
                                  │                ├─ achieved → check-completion-gate.sh
                                  │                │              ├─ run-verifier.sh (2x)
                                  ├─ breach        │              └─ spawn-audit-subagent.sh
                                  ▼                │              (both achieve → terminal)
                       graceful-drain prompt       ├─ unmet/blocked → next-iter prompt
                                                   └─ cancelled    → approve, exit
                            (drift-watchdog.sh advises every iter)

                            (probe-context-pct.sh + write-compaction-summary.sh +
                             restart-fresh-session.sh kick in at restart_at_context_pct)
```

## State machine

```
     [start]
        │
        ▼
   [pursuing] ──model writes status=achieved──▶ [check-completion-gate]
        ▲                                              │
        │                                       ┌──────┴──────┐
        │                                       ▼             ▼
        │                                  verifier+audit  fail/unmet
        │                                  both achieved     │
        │                                       │            │
        │                                       ▼            ▼
        │                                 [achieved★]  [unmet]──┐
        │                                                       │
        └──── re-feed next-iter prompt ─────────────────────────┘
        │
        ├─ caps fire ────▶ [budget-limited★]  (graceful drain)
        ├─ drift = blocked ──▶ [blocked★]
        └─ user --cancel  ──▶ [cancelled★]

★ = terminal
```

## Script contracts

| Script | Stdin | Stdout | Exit |
|---|---|---|---|
| `dispatch.sh` | (none) | help / start banner | 0 ok / 2 usage / 3 conflict |
| `parse-goal-spec.sh` | (none) | `KEY=VALUE\n` lines | 0 / 1 missing fields / 2 file-not-found |
| `state-rw.sh read` | (none) | validated JSON | 0 / 1 invalid / 2 missing |
| `state-rw.sh write` | (none, payload as argv) | (silent) | 0 / 1 invalid |
| `state-rw.sh seed` | (none) | (silent) | 0 |
| `install-stop-hook.sh` | (none) | confirmation line | 0 |
| `uninstall-stop-hook.sh` | (none) | confirmation line | 0 |
| `stop-hook-handler.sh` | Claude Code stop-hook payload | `{decision, reason?}` JSON | 0 always |
| `run-verifier.sh` | (none) | `pass\|fail\|flaky` | 0 pass / 1 fail / 2 flaky |
| `spawn-audit-subagent.sh` | (none) | audit JSON | 0 always |
| `check-completion-gate.sh` | (none) | (logs) | 0 gate-open / 1 gate-closed |
| `probe-token-usage.sh` | (none) | `{tokens_used, source, fidelity}` | 0 |
| `check-budget-caps.sh` | (none) | breach JSON or empty | 0 ok / 1 breach |
| `drift-watchdog.sh` | (none) | `{action, note?}` | 0 always |
| `probe-context-pct.sh` | (none) | `{pct, source}` | 0 |
| `write-compaction-summary.sh` | (none) | path to summary | 0 |
| `restart-fresh-session.sh` | (none) | `{action, summary_path, workspace}` | 0 / 2 max-restarts |
| `status-reader.sh` | (none) | text summary | 0 active / 1 terminal / 2 absent |
| `cancel-loop.sh` | (none) | confirmation summary | 0 |
| `delegate-to-codex.sh` | (none) | handoff banner; `exec`s codex | 2 missing/old codex / 3 conflict |

## Files written by the loop

```
.auto-loop/
├── heartbeat.json          dispatch.sh creates; cancel-loop.sh removes
├── goal-state.json         state-rw.sh atomic-writes; never edited directly
├── hooks-backup.json       install-stop-hook.sh writes; uninstall restores from
├── gate-history.jsonl      append-only by stop-hook-handler & check-completion-gate
├── verifier-{iter}.log     run-verifier.sh; rotates, keeps last 20
├── audit-{iter}.json       spawn-audit-subagent.sh
├── compaction-{iter}.md    write-compaction-summary.sh
├── restart-history.jsonl   append-only by restart-fresh-session.sh
├── diff-signatures.log     drift-watchdog.sh (one line per iter)
└── file-edits.log          drift-watchdog.sh (per-file edit tally)
```

`.claude/settings.local.json` is the only repo file mutated outside `.auto-loop/`,
and only its `hooks.Stop` entry is touched (with prior config backed up to
`.auto-loop/hooks-backup.json`).
