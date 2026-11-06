# Tracking board

One HTML page per initiative (one or more missions that move together), so the operator and every later session can see missions, slices, decisions with their reasons, and open asks without re-reading transcripts. The data lives in `board.json`; `board.cjs` renders `index.html` from `template.html`; `server.cjs`, started by `serve.sh`, publishes the boards on the tailnet and carries the operator's notes back to the rig's human seat.

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
node "$B/board.cjs" login <org>/<project>/<slug>                         # one-time link that lets a browser send feedback
node "$B/board.cjs" list
node "$B/board.cjs" check <org>/<project>/<slug>                         # lint and parse every diagram before render
bash "$B/serve.sh"                                                        # once per machine boot; idempotent
bash "$B/status.sh" --rig <rig> --project-dir <project dir> --missions <m8-x,m9-y> \
  --repo <owner/repo> --search "<TICKET-1> OR <TICKET-2> in:title"       # data for a periodic brief
```

## board.json

| Key | Shape | Notes |
|---|---|---|
| `owner_seat` | string | the human seat that receives this board's feedback, e.g. `lead-human@<rig>`; `init` fills it from `OPENRIG_SESSION_NAME` |
| `title`, `headline`, `phase`, `updated` | strings | `updated` in the operator's zone; headline in the brief's form (state, done/total, what waits) |
| `needs` | `[string \| {text, href, link?}]` | open asks for the operator; empty when none. An object adds a link to the detail (`#dec-<id>` for a decision row, a section `#<id>`, or a URL); `link` is the link text, default `details` |
| `missions` | `[{id, name, goal, status, slices: [{id, name, owner, status, progress, note, pr?}]}]` | status: `planned`, `doing`, `blocked`, `done`, `decide`; progress 0-100 |
| `decisions` | `[{id, q, rec, status, why, evidence, decided}]` | `C<n>` accepted, `Q<n>` or `R<n>` open (`decide`); the decision log shows why and evidence |
| `log` | `[[when, what, evidence]]` | provider writes, merges, Jira edits, dispatches |
| `facts` | `[[fact, source]]` | what was read, with its source; newest first |
| `links` | `[[title, url]]` | consoles, PRs, tickets, docs |
| `sections` | `[{id, title, nav?, place?, html}]` | hand-written HTML cards (intent, design, knowledge references); shown before the missions, or after the decision log with `"place": "bottom"` (risks) |
| `diagrams` | `{id: "<Mermaid text>"}` | rendered by pele into `<div data-diagram="id"></div>` placed in a section |

## Feedback from the board

The operator turns on **Annotate**, clicks a card or a table row (or selects text in it) and adds a note: change, comment or question. Notes collect in the floating **Changes** panel on the right and stay in that browser until sent. **Send feedback** posts them; the board's owner seat receives them as one user message, applies them, and the panel shows the seat's progress and reply while the page reloads with the update.

```
browser ──POST feedback──► server.cjs ──► feedback/inbox/<id>.json ──► board-bridge (Pi extension, owner seat)
   ▲                            │                                         └► pi.sendUserMessage(notes), followUp when busy
   └──── events: status, reply, reload ◄── feedback/status, feedback/done, index.html ◄── the seat applies, renders, replies
```

- **Install once per machine:** the `board-bridge` Pi extension ships with the operator's dotfiles (`dotfiles/pi/.pi/agent/extensions/board-bridge.js` in vanducng/dotfiles, linked by `make stow-pi`); `/reload` in the human seat to load it. It runs only in a seat named `*-human@*`, serves only boards whose `owner_seat` is that seat, and finds `board.cjs` through `$OPENRIG_BOARD_CLI`, `~/skills`, or the installed skill.
- **Log in once per browser:** open the URL from `board.cjs login`. The server sets an HttpOnly, SameSite=Strict cookie and drops the token from the address. Without it the page is read-only. The token is `<root>/.board-token` (mode 600); deleting it and restarting the server logs every browser out.
- **The seat's reply** ends with one line per note: `<note id>: applied | deferred | needs you - <why>`. Applying a note follows the normal rules: records in git, build work to the rig's owner seat, `render` at the end.
- **Live updates** are server-sent events (`/events`): one-way and reconnecting, so no WebSocket is needed.
- `feedback/` keeps every batch (`inbox`, `processing`, `status`, `done`) as the audit trail; it is never served.

## Diagram conventions

Every board uses one palette, defined once in `template.html`. A diagram names roles, never colors, so the same thing looks the same on every board and the colors can change in one place. `board.cjs check` rejects `classDef`, `style`, `linkStyle`, `fill:` and `rgb(...)` in diagrams, and any role not in this table.

| Role | Color | Flowchart | Sequence participant |
|---|---|---|---|
| `ours` | blue | `A["Checkout"]:::ours`, or `class A,B ours` | `participant P@{ "type": "control" } as Checkout` |
| `provider` | purple | third-party platform: `:::provider` | `participant R@{ "type": "boundary" } as Retell` |
| `person` | amber | a phone or a person: `:::person` | `actor L as Lead` |
| `store` | gray | database, bucket, ledger: `:::store` | `participant D@{ "type": "database" } as DB` (also `queue`) |
| `legacy` | dashed gray | what is being replaced: `:::legacy` | - |
| `risk` | red | a failure path: `:::risk` | `critical <label> ... end` frame |
| `done` | green | proven or shipped: `:::done` | - |

- Subgraphs take a role with `class <subgraph-id> <role>` (not `subgraph X:::role`).
- Edges: `-->` a call, `-.->` a callback, webhook or config write, `==>` the critical path.
- Each diagram gets a legend of the roles it uses, under it, automatically.
- Requires pele 1.13 or later: roles are CSS classes on the rendered SVG, recolored through pele's own variables.

## Rules

- Update on events (a decision, a slice state change, a merge, a provider write), then `render`. Do not rewrite it every turn.
- Every number on the board comes from a source read that turn; unknown is `?`.
- No secrets, tokens or client data. Personal phone numbers only when the operator asked for them on the board; git records keep the last 4 digits.
- Diagrams use Mermaid syntax rendered by [pele](https://github.com/obsidianmd/pele). A `;` ends a statement in Mermaid, so never put one inside a sequence-diagram note or message; a diagram that fails to parse shows its source text instead.
- The tailnet URL does not load on the serving machine itself; check there with `http://127.0.0.1:<port>/<org>/<project>/<slug>/`.
- Periodic briefs (when the operator asks for one every N minutes): run `status.sh`, update the board's slices and `log`, render, then send the brief with the board link.
- When the initiative ends, set every mission's status, keep the folder, and leave the URL working.
