# Intake template — 4 questions max

Phase 1's `vd:ultracook "<short goal>"` runs these via `AskUserQuestion`. Order is fixed (later answers depend on earlier ones). Max 4 questions per intake — anything more is bloat; defer to mid-flight editing of `goal.yaml`.

## Q1 — Target kind

**Question:** "Where does this goal land?"
**Header:** `Target kind`
**Multi-select:** false
**Options:**

| Label | Description |
|---|---|
| `Local only` | Edits stay on local branch. No PR, no ship, no deploy. End state: changes committed locally; user reviews. |
| `PR only` | Open PR to the target branch, wait for CI green, stop. No deploy or post-deploy verify. |
| `Cluster / production` | Full pipeline: PR → CI → merge → tag → image build → cluster reconcile → rollout → smoke. |

**Maps to:** `goal.yaml.target.kind` ∈ `{ local, pr-only, cluster }`. Conditional follow-ups: when `cluster` is picked, the resolved workflow auto-adds `image_build_wait`, `reconcile`, `rollout_check`, and the `verify_*` actions (Phase 2 binds these). When `local`, the resolved workflow stops after `cook`.

## Q2 — Action shape

**Question:** "What shape of work is this?"
**Header:** `Action shape`
**Multi-select:** false
**Options:**

| Label | Description |
|---|---|
| `Brainstorm-first` | Design phase needed — invoke `vd:brainstorm` before `vd:plan`. Use for unfamiliar / multi-option work. |
| `Plan-only` | Skip brainstorm; jump straight to `vd:plan`. Use when the approach is decided. |
| `Fix-and-ship` | No design phase; treat as a small targeted fix. Invoke `vd:fix --auto` instead of plan+cook. |
| `Refactor` | TDD shape — plan with `--tdd` flag. |

**Maps to:** prepends to the resolved workflow's action sequence:
- Brainstorm-first → `[brainstorm, plan, ...]`
- Plan-only → `[plan, ...]`
- Fix-and-ship → `[fix, ...]` (skips plan)
- Refactor → `[plan --tdd, ...]`

Stored as `goal.yaml.actions[0]` (the rest of the sequence comes from the project profile).

## Q3 — Branch name (conditional)

**Question:** "Branch name? (Suggested: `{slug-prefixed-by-profile}`)"
**Header:** `Branch name`
**Multi-select:** false
**Options:**

| Label | Description |
|---|---|
| Suggested name (from slug + profile prefix) | Use as-is. |
| Different name | User types via the "Other" option. |

**Skip when `--reuse` passed.** When skipped, `goal.yaml.project.branch` is captured from the current branch (`git rev-parse --abbrev-ref HEAD`). Q4 becomes Q3 in that case (still ≤4 total).

**Maps to:** `goal.yaml.project.branch` + drives `git worktree add ... -b <branch>` in `init-goal.sh`.

**Profile-prefix logic:** the profile's `default_branch_prefix` (e.g. `fix/` for goclaw) is prepended to the slug. User can strip/override via "Other".

## Q4 — Autonomy

**Question:** "How autonomous?"
**Header:** `Autonomy`
**Multi-select:** false
**Options:**

| Label | Description |
|---|---|
| `Semi (recommended)` | Gates only at high-blast-radius transitions: first plan approval, ship confirmation, final post-deploy verify. Default. |
| `Manual` | Every action gated. Use while learning the skill or debugging a stuck goal. |
| `Auto` | No gates. Only stops on terminal state or budget exhaustion. For trusted workflows. |

**Maps to:** `goal.yaml.autonomy` ∈ `{ manual, semi, auto }`. Default = `semi` if the user dismisses the question or "Other" is empty.

## Answer → goal.yaml mapping

```
ULTRACOOK_TARGET_KIND   →  target.kind
ULTRACOOK_ACTION_SHAPE  →  actions[0]  (prepended; rest from profile)
ULTRACOOK_BRANCH        →  project.branch + worktree branch name
ULTRACOOK_AUTONOMY      →  autonomy
```

These are set as env vars by SKILL.md after the AskUserQuestion calls, then `bash scripts/init-goal.sh "<short_goal>"` reads them.

## Q-skip logic for `--reuse`

When `--reuse` is passed:
- Q3 (branch name) is skipped — `goal.yaml.project.branch = $(git rev-parse --abbrev-ref HEAD)`, `goal.yaml.project.worktree_path = null`.
- Total questions becomes 3.

The "≤4 questions" success criterion holds in both modes.

## Anti-bloat reminders

Things that look like good intake questions but should NOT be added (they cause decision fatigue and are recoverable mid-flight by editing `goal.yaml`):

- Token / iteration budgets — use defaults; let the user edit `goal.yaml.budgets` if they want different.
- Verifier list — derived from the resolved profile + target.kind, not user-input.
- Risk tier — optional field; tag in goal.yaml after the fact if you want plan-audit auto-run.
- Plan-audit yes/no — gated by `risk_tier`, not a separate question.

If a future user asks for a new intake question, push back hard: can it be a `goal.yaml` field with a sane default instead?
