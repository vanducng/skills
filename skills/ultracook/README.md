# vd:ultracook - workflow conductor

Hand ultracook a task; it classifies the work and runs the smallest viable workflow:

- **direct** - trivial/clear → just do it, no machinery.
- **pipeline** - a real feature/fix → the needed slice of **brainstorm → plan → cook →
  review → ship**, gating at high-blast transitions, then autonomous; resumes across
  context compaction.
- **fan-out** - repo-wide / migration / N-finder audit → parallel packets via the
  host's native primitive; the parent owns integration.

Ultracook is a **map, not a cage**: a pipeline is a list of *stages*, each a `vd:` skill
name plus a checkable done-when gate. All discipline lives in the invoked skills
(`vd:plan` owns planning rigor, `vd:cook` owns execution, `vd:ship` owns landing);
ultracook classifies, sequences, gates, and keeps resumable state. There is no closed
action vocabulary - adding a capability means naming a skill in the stage list.

## Install

**Claude Code (marketplace):**

```
/plugin marketplace add vanducng/skills
/plugin install vd@vd-skills
```

**Codex / dev-local:**

```
brew install vanducng/tap/vd
vd install codex ultracook     # Codex namespace
vd install claude --dev ultracook   # symlink for Claude Code dev work
```

After install, invoke with the runtime's prefix: slash in Claude Code, dollar in Codex.

## Quick start

```
vd:ultracook "implement cron retry, ship to staging, verify"
```

The conductor classifies the task, proposes a stage flow with done-when gates (you can
edit it in `semi`/`manual`), creates `<state-base>/{slug}/state.json`, and runs the
stages - delegating long red→green iteration to `vd:auto-loop` and plan approval to
Plannotator's plan-review hook where installed.

## Sub-verbs

```
vd:ultracook                           # resume an in-progress goal
vd:ultracook status [<slug>]           # all goals one-line each; stage detail for one (scripts/status.sh)
vd:ultracook kill --reason "<text>"    # terminal=abandoned; refuses if already terminal (scripts/kill.sh)
```

When more than one goal is in flight, bare resume lists them (via `status.sh`) and
asks which to continue - no silent newest-wins.

## Modes

| Flag | Behaviour |
|---|---|
| `--manual` | Every stage gated |
| `--semi` (default) | Gates on first plan approval, ship, and the final done-when check |
| `--auto` | No gates; only stops on terminal state or guardrail |
| `--reuse` | Work in the current checkout; skip `vd:worktree` |

Hard gates (delete/deploy/migrations/secrets/broad codemods/expensive fan-outs) always
ask, even in `--auto`. Switch autonomy mid-flight by editing `state.json.autonomy`.

## On-disk state

State base: `$VD_STATE_PATH` → `<git-root>/.workbench/state` when `.workbench/` exists
→ `$XDG_STATE_HOME/vd/ultracook/<repo-id>/goals`. One file per goal:

```
<state-base>/{slug}/state.json    # goal, autonomy, stages[] with status/done-when/evidence,
                                  # iteration counters, terminal state - schema in references/state.md
```

Resume = read the file, continue from the first stage that is neither `done` nor `skipped`.

## Hard guardrails

- Global iteration cap (default 30) → `blocked`
- Same-signature failure recognizer (3× identical fail → `blocked`, signature surfaced)
- Token-cap prompt-back at ~80% context
- No auto-merge on the skills repo (`vd:ship official`)

## Files

- `SKILL.md` - conductor + flow composition + run loop
- `references/conductor.md` - classification heuristics, gate map, hard gates, fan-out packets
- `references/autonomy-modes.md` - manual/semi/auto semantics
- `references/state.md` - state.json schema v2
- `scripts/` - `update-state.sh` (init/patch, atomic), `status.sh`, `kill.sh`

## Versioning

- v0.x: closed action/verifier vocabularies, dual-runtime adapter files, per-project
  TOML profiles, 22 scripts. Renamed from `vd:pursue` at v0.4.
- v1.0: redesigned as an open conductor. Stages are skill names + done-when gates;
  vocabularies, runtime adapters, profiles, and most scripts removed. State collapsed
  to a single `state.json` (schema v2). Verification delegated to the stage skills
  (cook's `eval-dod.sh` DoD gate, ship's CI watch). Old v0.x goal dirs (`goal.yaml` +
  state schema v1) do not auto-resume - finish or re-create them.
