# Smoke test recipe

A reproducible end-to-end test of `vd:auto-loop` from a clean checkout. Goal:
"increment a counter file to 3", verifier checks the counter equals 3.

## Prerequisites

- `bats-core` installed (`brew install bats-core` on macOS).
- `jq` installed.
- A scratch git repository.

## Recipe

```bash
# 1. Scratch workspace
SCRATCH=$(mktemp -d)
cd "$SCRATCH"
git init -q
echo 0 > counter.txt
git add -A
git -c user.email=t@t -c user.name=t commit -qm init

# 2. Define the goal
cat > goal.md <<'EOF'
# Goal
Set counter.txt to contain exactly the number 3.

# Verify
verify: `test "$(cat counter.txt)" = "3"`

# Caps
max_iterations: 5
max_wallclock: 5m
EOF

# 3. Start the loop
vd:auto-loop --goal-file goal.md
# (Inside Claude Code: the model will edit counter.txt, set goal-state.json
# with status=achieved, the Stop hook will run the verifier 2x and the
# audit subagent. Both votes "achieved" → the loop ends.)

# 4. Inspect
cat .auto-loop/gate-history.jsonl       # one line per gate decision
cat .auto-loop/goal-state.json | jq .   # final state
ls .auto-loop/verifier-*.log            # verifier output per iter
```

## Expected outcome

- ≤5 iterations.
- `goal-state.json` ends with `status: achieved` (two-vote gate passed).
- `counter.txt` contains `3`.
- `.claude/settings.local.json` has been restored to its pre-install state
  (no `hooks.Stop` entry left over).
- Stop hook automatically uninstalled by the loop on terminal achieved status
  is currently a follow-up; explicit `--cancel` cleans up if needed.

## Programmatic test (no Claude Code)

The bats suite exercises the same plumbing without a live model:

```bash
bats skills/auto-loop/tests/
# 25/25 passing covers parser, state-rw, completion gate, budget caps,
# cancel/status semantics.
```

## What this smoke test does *not* cover

- Real model behaviour and audit-subagent quality (need a live `claude` headless
  invocation).
- Phase-restart compaction at high context use (synthetic-only path; the test in
  `architecture.md` notes this).
- Codex `/goal` delegation (manual; needs `codex ≥ 0.128.0` and ChatGPT auth).
