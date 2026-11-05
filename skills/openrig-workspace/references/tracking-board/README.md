# Tracking board

One HTML page per initiative (one or more missions that move together), so the operator and every later session can see missions, slices, decisions with their reasons, and open asks without re-reading transcripts. The data lives in `board.json`; `board.cjs` renders `index.html` from `template.html`; `serve.sh` publishes the boards on the tailnet.

## When to offer it

When a rig or mission starts with more than one slice, or work will span sessions, ask once: "Track this on a board?" On yes, run `init` and put the URL in the mission `SPEC.md` Status section. On no, do nothing. Do not create a board for a one-slice fix.

## Where it lives

| Thing | Path or URL |
|---|---|
| Board files | `$OPENRIG_BOARDS_ROOT/<org>/<project>/<slug>/board.json` and `index.html` (default root `~/.share/openrig/boards`) |
| URL | `https://<machine>.<tailnet>.ts.net/boards/<org>/<project>/<slug>/` (tailnet only) |
| Slug | the mission codes or a short name: `m8-m9-routing-sms`, `m12-intake-v2` |
| Extra pages | other HTML in the same folder (a current-state report, a diagram page), linked from `links` |

The boards root is a capture home (workspace `AGENTS.md`, File homes): it survives the rig but is not git. Decisions and outcomes still go to the mission `NOTES.md` and slice `PROGRESS.md`; the board mirrors them and links back.

## Commands

```bash
B="$HOME/skills/skills/openrig-workspace/references/tracking-board"
node "$B/board.cjs" init <org>/<project>/<slug> --title "<initiative>"   # board.json + index.html, prints the URL
node "$B/board.cjs" render <org>/<project>/<slug>                        # after every board.json edit
node "$B/board.cjs" url <org>/<project>/<slug>
node "$B/board.cjs" list
bash "$B/serve.sh"                                                        # once per machine boot; idempotent
bash "$B/status.sh" --rig <rig> --project-dir <project dir> --missions <m8-x,m9-y> \
  --repo <owner/repo> --search "<TICKET-1> OR <TICKET-2> in:title"       # data for a periodic brief
```

## board.json

| Key | Shape | Notes |
|---|---|---|
| `title`, `headline`, `phase`, `updated` | strings | `updated` in the operator's zone; headline in the brief's form (state, done/total, what waits) |
| `needs` | `[string]` | open asks for the operator; empty when none |
| `missions` | `[{id, name, goal, status, slices: [{id, name, owner, status, progress, note, pr?}]}]` | status: `planned`, `doing`, `blocked`, `done`, `decide`; progress 0-100 |
| `decisions` | `[{id, q, rec, status, why, evidence, decided}]` | `C<n>` accepted, `Q<n>` or `R<n>` open (`decide`); the decision log shows why and evidence |
| `log` | `[[when, what, evidence]]` | provider writes, merges, Jira edits, dispatches |
| `facts` | `[[fact, source]]` | what was read, with its source; newest first |
| `links` | `[[title, url]]` | consoles, PRs, tickets, docs |
| `sections` | `[{id, title, nav?, html}]` | hand-written HTML cards (intent, design, knowledge references) shown before the missions |
| `diagrams` | `{id: "<Mermaid text>"}` | rendered by pele into `<div data-diagram="id"></div>` placed in a section |

## Rules

- Update on events (a decision, a slice state change, a merge, a provider write), then `render`. Do not rewrite it every turn.
- Every number on the board comes from a source read that turn; unknown is `?`.
- No secrets, tokens or client data. Personal phone numbers only when the operator asked for them on the board; git records keep the last 4 digits.
- Diagrams use Mermaid syntax rendered by [pele](https://github.com/obsidianmd/pele). A `;` ends a statement in Mermaid, so never put one inside a sequence-diagram note or message; a diagram that fails to parse shows its source text instead.
- The tailnet URL does not load on the serving machine itself; check there with `http://127.0.0.1:<port>/<org>/<project>/<slug>/`.
- Periodic briefs (when the operator asks for one every N minutes): run `status.sh`, update the board's slices and `log`, render, then send the brief with the board link.
- When the initiative ends, set every mission's status, keep the folder, and leave the URL working.
