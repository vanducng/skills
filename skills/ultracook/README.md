# vd:ultracook - open workflow conductor

Hand ultracook a task. It classifies the work and runs the smallest viable path:

- **direct** - trivial/clear → `vd:cook --quick` or `vd:fix`, no machinery
- **pipeline** - a real feature/fix → named skills with checkable `done_when` gates (usually interview → brainstorm → plan → cook → ship)
- **fan-out** - repo-wide / migration / N-finder → parallel packets; the parent owns integration

It stays human-in-the-loop until a gate clears, then drives to a terminal state. State is one `state.json` (schema v2) so a later session can resume. Triage lives in `references/conductor.md`.

## Install

**Claude Code (marketplace):**

```
/plugin marketplace add vanducng/skills
/plugin install vd@vd-skills
```

**Codex / local:**

```
brew install vanducng/tap/vd
vd install codex ultracook
# or: vd install claude --dev ultracook
```

Invoke with the host's prefix (slash in Claude Code, dollar in Codex). Docs below use canonical ids: `vd:ultracook`.

## Usage

```
vd:ultracook "add export-to-csv on settings"
vd:ultracook                  # resume (list-and-pick if several)
vd:ultracook status --all
vd:ultracook kill --reason "pausing this"
```

Autonomy: `--manual` / `--semi` (default) / `--auto`.

## Scripts

| Script | Role |
|---|---|
| `scripts/update-state.sh` | Create or patch `state.json` |
| `scripts/status.sh` | Print one goal or list them |
| `scripts/kill.sh` | Abandon; refuses to clobber a terminal state |
| `scripts/test-state-scripts.sh` | Regression tests for the three scripts |

See `references/state.md` for the schema.
