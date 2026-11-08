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
node "$B/board.cjs" render --all                                          # re-render every board under the root (after a template or pele update)
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
| `missions` | `[{id, name, goal, status, slices: [{id, name, owner, status, progress, note, pr?, diagram?}]}]` | status: `planned`, `doing`, `blocked`, `done`, `decide`; progress 0-100; `diagram` names a `diagrams` id drawn under the slice's note (a statechart, for example) |
| `decisions` | `[{id, q, rec, status, why, evidence, decided}]` | `C<n>` accepted, `Q<n>` or `R<n>` open (`decide`). Each row shows the id, a small status badge and the question at full width; opening it shows the recommendation, why and evidence |
| `log` | `[[when, what, evidence]]` | provider writes, merges, Jira edits, dispatches |
| `facts` | `[[fact, source]]` | what was read, with its source; newest first |
| `links` | `[[title, url]]` | consoles, PRs, tickets, docs |
| `sections` | `[{id, title, nav?, place?, html}]` | hand-written HTML cards (intent, design, knowledge references). `place`: omitted puts the card between the headline block and the missions (as before); `"after"` puts it right after the missions; `"bottom"` puts it after the decision log (risks). Tables in `html` become stacked rows on a phone when their first row is `<th>` cells. A `<p class="sub">` is muted small text |
| `diagrams` | `{id: "<Mermaid text>"}` | drawn by pele at render time into `<div data-diagram="id"></div>` placed in a section, or under a slice that names it; see Diagram conventions |

## Reading the board

The page is built for a phone first and scales up; it needs no network beyond its own server (no CDN, no web fonts).

- **First screen.** Phase, title and headline, the **Needs you** card with its asks (each can link to its detail; an ask longer than six lines has a Show more button), then the Blocked, Open decisions and In progress counts and the open decisions themselves. From 1024px a sticky section rail sits on the left and the same blocks lead in two columns; below that the top bar has a section menu.
- **Find things.** One search box covers slices, decisions, the done log and facts; the chips filter slices by status (All, Doing, Blocked, Decide for slices that need a decision, Done). The Blocked and In progress tiles set the same filter. Open missions are listed first and finished ones after them (board order within each group); done missions start collapsed; long lists (done log, decision log, facts, links) show their first rows and a "Show all" button, and search always looks at every row.
- **What changed.** The browser remembers what each board looked like at the end of the last visit (per board path, in `localStorage`). When `updated` moves on, slices, decisions and log rows that are new or different get a dot, and a "N changed since your last visit" button and a Changed chip appear. Reloading inside the same visit, including the reload after the seat applies notes, keeps the dots. `updated` also shows as relative time ("2 h ago") when it is in the `YYYY-MM-DD HH:MM` form.
- **Deep links.** `#dec-<id>` opens a decision, `#<slice id>` opens a slice and its note, `#m-<mission id>` opens a mission (the older `#mission-<n>`, counted in board order, still works), `#<section id>` scrolls to a section; a `needs` link uses any of them.
- **Theme and print.** Follows the system dark mode until the Theme button is used, then remembers the choice (`?theme=light|dark` overrides it for one load). Print opens every section on a light page. Without JavaScript the page shows a plain summary written at render time.
- **Links are checked.** Only `http(s)`, `mailto`, same-page anchors and relative paths become links, in `needs`, `pr`, `log` evidence and `links`; anything else is shown as text.
- **Errors.** Data that cannot be parsed shows an error card instead of a blank page; a section that fails to draw does not stop the rest.

## Feedback from the board

The operator turns on **Annotate** (pencil in the top bar, then the switch in the Changes sheet), taps a slice, a decision, a log row or a table row (or selects text in it first to quote it) and adds a note: change, comment or question. On a touch screen, pressing and holding a row starts a note without turning Annotate on. The note box is modal like the Changes sheet (the page behind it is inert, Tab stays inside, focus returns when it closes). Below 1024px it fills the visible screen above the keyboard (the visual viewport): one header line with Cancel, the title and the row it is about, and Add note, then the kind selector and the textarea, which is focused when the box opens and keeps one height while typing. From 1024 to 1279px it is a bottom sheet on the keyboard that never covers its row (the page scrolls the row into view above it); from 1280px it sits in a side panel (below that, with the section rail shown, the content column would be under 400px wide next to a panel). An unsent note box and its text survive a reload, so a reload event from the seat does not lose a half-written note. Notes collect in the **Changes** sheet (a side panel from 1280px, shown while it has notes or is open) and stay in that browser until sent. **Send feedback** posts them; the board's owner seat receives them as one user message, applies them, and the sheet shows the seat's progress and reply while the page reloads with the update.

```
browser ──POST feedback──► server.cjs ──► feedback/inbox/<id>.json ──► board-bridge (Pi extension, owner seat)
   ▲                            │                                         └► pi.sendUserMessage(notes), followUp when busy
   └──── events: status, reply, reload ◄── feedback/status, feedback/done, index.html ◄── the seat applies, renders, replies
```

- **Install once per machine:** the `board-bridge` Pi extension ships with the operator's dotfiles (`pi/.pi/agent/extensions/board-bridge.js`, linked by `make stow-pi`); `/reload` in the human seat to load it. It runs only in a seat named `*-human@*`, serves only boards whose `owner_seat` is that seat, and finds `board.cjs` through `$OPENRIG_BOARD_CLI`, `~/skills`, or the installed skill.
- **Two ways to sign in** (without one, the page is read-only):
  - **Tailnet identity:** open the board through its tailnet address. `tailscale serve` adds `Tailscale-User-Login` to each request; a login listed in `<root>/.board-owners` (one per line, `#` comments, mode 600) is signed in, and the page says "Connected as <name>". The operator adds his own login to that file on each host; no login is ever written into this skill. A missing or empty list, or one that others can read or write, means token only.
  - **Token link, once per browser:** open the URL from `board.cjs login`. The server sets an HttpOnly, SameSite=Strict cookie and drops the token from the address. The token is `<root>/.board-token` (mode 600); deleting it and restarting the server logs every browser out.
  - **Threat model:** `tailscale serve` strips `Tailscale-User-*` headers a client sent and sets them for every tailnet user, including devices shared in, which is why the list exists. A process on the same machine could send the header to the loopback port, but it can already write `feedback/inbox` on disk, so this adds no local exposure; the server binds loopback only and is never published with Funnel.
- **The seat's reply** ends with one line per note: `<note id>: applied | deferred | needs you - <why>`. Applying a note follows the normal rules: records in git, build work to the rig's owner seat, `render` at the end.
- **Live updates** are server-sent events (`/events`): one-way and reconnecting, so no WebSocket is needed.
- `feedback/` keeps every batch (`inbox`, `processing`, `status`, `done`) as the audit trail; it is never served.

## Diagram conventions

Every board uses one palette, defined once in `template.html`. A diagram names roles, never colors, so the same thing looks the same on every board and the colors can change in one place. `board.cjs check` rejects `classDef`, `style`, `linkStyle`, `fill:` and `rgb(...)` in diagrams, and any role not in this table (a statechart's own marks are mapped first, below).

| Role | Color | Flowchart | Sequence participant |
|---|---|---|---|
| `ours` | blue | `A["Polaris"]:::ours`, or `class A,B ours` | `participant P@{ "type": "control" } as Polaris` |
| `provider` | purple | third-party platform: `:::provider` | `participant R@{ "type": "boundary" } as Retell` |
| `person` | amber | a phone or a person: `:::person` | `actor L as Lead` |
| `store` | gray | database, bucket, ledger: `:::store` | `participant D@{ "type": "database" } as DB` (also `queue`) |
| `legacy` | dashed gray | what is being replaced: `:::legacy` | - |
| `risk` | red | a failure path: `:::risk` | `critical <label> ... end` frame |
| `done` | green | proven or shipped: `:::done` | - |

- Subgraphs take a role with `class <subgraph-id> <role>` (not `subgraph X:::role`).
- A statechart from the `statechart` skill goes in as written. `render` and `check` map its phase colors to roles (blue `ours`, orange `person`, purple `provider`, yellow `store`, teal `done`, tan `legacy`, pink `ours`) and `breaks` and `mayBreak` to `risk`, and drop its two `classDef` lines; `bugPath` (a state on the shortest path to a bug) gets a thick red border and `repeats` a dashed one. Its own Legend block names the phases. Any other `classDef` is still rejected.
- Edges: `-->` a call, `-.->` a callback, webhook or config write, `==>` the critical path.
- Each diagram gets a legend of the roles it uses, under it, automatically.
- Requires pele 1.13 or later: roles are CSS classes on the rendered SVG, recolored through pele's own variables (they follow the light and dark theme).
- Drawing happens in `board.cjs render`, on the machine that renders, with [pele](https://github.com/obsidianmd/pele) from `$PELE_DIR` (default `~/.cache/openrig-boards`; `npm install --prefix ~/.cache/openrig-boards pele@1.13.0`). The page carries the finished SVG, so the viewer needs no network. A flowchart written `LR` or `RL` is also drawn top-down for narrow screens. A diagram pele cannot draw, or a render without pele, shows its source text instead (and `render` says so on stderr). Each diagram has a Full size button and a collapsible source, which is also its text alternative.

## Changing the template

`template.html` is one file: a token block (`--tb-*` and `--role-*` custom properties, the names the board index page copies), the shell and board CSS, and the page script. Keep the token names; a value change goes in both dark blocks.

```bash
node --test skills/openrig-workspace/references/tracking-board/tests/board.test.cjs   # render contract, helpers, tokens, contrast
```

- `fixtures/board.json` is the synthetic board (a done mission, mixed statuses, open and accepted decisions, a long log, facts, links, a diagram, a slice with a statechart, a risks table); `fixtures/empty.json` is what `init` writes. Never put a real board in the repo.
- Render a fixture into a scratch root and serve it to look at it: `OPENRIG_BOARDS_ROOT=<scratch> node board.cjs render --all`, then `OPENRIG_BOARDS_ROOT=<scratch> OPENRIG_BOARDS_PORT=<free port> node server.cjs`. Check 390, 768 and 1440 wide, light and dark, the Changes sheet, a note box, and one feedback round trip. For the phone note box run `node tests/mobile-composer.check.cjs <rendered index.html> [--shots --out <dir>]`: headless Chrome with the iOS keyboard simulated, asserting every frame while a note is typed. `?now=<ISO time>` fixes the clock for captures.
- The page's pure helpers sit between `tb:helpers:start` and `tb:helpers:end` in the script so the tests can load them without a DOM.

## Rules

- Update on events (a decision, a slice state change, a merge, a provider write), then `render`. Do not rewrite it every turn.
- Every number on the board comes from a source read that turn; unknown is `?`.
- No secrets, tokens or client data. Personal phone numbers only when the operator asked for them on the board; git records keep the last 4 digits.
- Diagrams use Mermaid syntax rendered by [pele](https://github.com/obsidianmd/pele). A `;` ends a statement in Mermaid, so never put one inside a sequence-diagram note or message; a diagram that fails to parse shows its source text instead.
- The tailnet URL does not load on the serving machine itself; check there with `http://127.0.0.1:<port>/<org>/<project>/<slug>/`.
- Periodic briefs (when the operator asks for one every N minutes): run `status.sh`, update the board's slices and `log`, render, then send the brief with the board link.
- When the initiative ends, set every mission's status, keep the folder, and leave the URL working.
