# Dogfood — vd:pursue v0.2 (template — fill in during live run)

**Date:** _TBD when user runs the dogfood_
**Runtime baselines:**
- vd CLI version: `vd --version` →
- Codex CLI version: `codex --version` →
- Claude Code version: (from About menu) →

## Dogfood A — Codex-only end-to-end

**Goal picked:** _(tiny goclaw fix — CLAUDE.md typo, copy tweak, doc reorder)_

**Run:**
```
# 1. Open fresh Codex TUI session
codex
# 2. cd to goclaw worktree
cd ~/git/personal/dataplanelabs/worktrees/goclaw-...
# 3. Trigger
vd:pursue "<tiny fix>"
```

**Intake answers:**
- target kind:
- action shape:
- branch:
- autonomy:

**Per-action wall-clock + tokens (fill from journal `codex_session_metrics`):**

| Action | Wall-clock | Tokens (in/cached/out) | Verifier | Notes |
|---|---|---|---|---|
| intake | | | n/a | |
| plan | | | n/a | |
| cook | | | test_suite_passes | |
| code_review | | | n/a | |
| test | | | test_suite_passes | |
| ship | | | ci_green | |
| wait_ci | | | n/a | (Monitor via hook) |
| image_build_wait | | | n/a | |
| reconcile | | | cmd_exits_zero | |
| rollout_check | | | cmd_exits_zero | |
| verify_pod_image | | | pod_image_matches | |
| verify_smoke | | | (target.verifiers) | |
| done | | | | |

**Total time to terminal=done:** _TBD_

**UX divergences from Claude Code:**
- _e.g. ask_user_question tab navigation: ___
- _e.g. error message clarity: ___
- _e.g. semi-mode gate confirmation flow: ___

**Acceptable failures encountered + resolutions:**
- _e.g. CI flake → 1 retry → green: ___

**Blocking failures (any of these → v0.2 not ready):**
- [ ] Intake didn't complete cleanly
- [ ] Cook delegation hung > 10min
- [ ] state.json corruption (parse fail / schema violation)
- [ ] Same action looped > budget caps without same-signature recognizer firing
- [ ] Pursue recursion guard failed (nested pursue spawn)

## Dogfood B — KEYSTONE TEST (cross-runtime resume)

**Setup:**
```
# 1. Open Claude Code session
# 2. Start a fresh small goal
vd:pursue "another tiny fix"
# 3. Walk intake to completion. Confirm goal.yaml + state.json created.
# 4. Exit Claude Code WITHOUT killing the goal (state.terminal stays null).
```

**Cross to Codex:**
```
# 5. Open Codex TUI
codex
# 6. cd to SAME worktree
cd ~/git/personal/dataplanelabs/worktrees/...
# 7. Bare invocation (resume mode)
vd:pursue
```

**Expected:** Codex pursue reads existing goal.yaml + state.json, prints
"resuming goal {slug}", picks up at next pending action. Walks workflow
to terminal=done.

**Switch back to Claude Code:**
```
# 8. New Claude Code session
vd:pursue status
```

**Expected:** Shows terminal=done (Claude Code reads the SAME state.json
that Codex wrote).

**State.json snapshots (capture for forensic):**
- Pre-Claude-Code-exit: _paste state.json contents_
- Post-Codex-resume: _paste_
- Post-done (read from Claude): _paste_

**Rough edges:**
- _e.g. Codex resumed but didn't read goal.yaml.actions correctly: ___
- _e.g. iteration_count off-by-one between runtimes: ___

## Pass/fail gate

- [ ] Dogfood A reached terminal=done end-to-end on Codex
- [ ] KEYSTONE TEST: same goal completed across Claude → Codex via state.json
- [ ] Zero regression on Claude Code (separate small goal still completes)
- [ ] codex_session_metrics correctly populated for at least one Codex action
- [ ] At least one Monitor-style action ran via PostToolUse hook without falling back to phase-3-stub error
- [ ] At least one skill-to-skill dispatch (plan/cook/ship) ran via codex_exec_resume_last and completed
- [ ] VD_PURSUE_DEPTH recursion guard did NOT trip
- [ ] notify.sh fired on any terminal=blocked encountered (if any)

**Overall verdict:** _pass | fail-blocking | fail-with-known-limitations_

## Token + wallclock comparison vs Claude Code (fill v0.1 baseline if available)

| Metric | Claude Code v0.1 | Codex v0.2 | Delta |
|---|---|---|---|
| Total wallclock to done | | | |
| Total tokens | | | |
| Number of gates (semi mode) | | | |
| Number of retries | | | |

## Unresolved questions (after dogfood)

- _add findings here_

## Next steps

If keystone passes: open Phase 5 completion PR + bump skills/pursue/SKILL.md version metadata to 0.2.0 if not already. Update CHANGELOG.md.

If keystone fails: stop. Document root cause + return to relevant phase (most likely Phase 3 if Monitor-related, Phase 2 if executor-related, Phase 1 if state.json portability).
