---
name: asciinema
description: "Record a scripted terminal demo of a CLI or TUI with asciinema: hidden fixture setup, commands typed on screen, TUI keys driven through tmux, a leak gate on the cast, scene-by-scene proof by replaying the cast, an agg GIF for the README, and upload to asciinema.org. Activates when the user says 'asciinema', 'record a terminal demo', 'screencast the CLI', 'record the TUI', 'add a demo GIF to the README', 'make a cast', or 'upload to asciinema'. Do not use for browser recordings (agent-browser) or produced motion video (video)."
license: MIT
category: visuals
keywords: [asciinema, agg, terminal, screencast, demo, cast, gif, tui, tmux, readme]
metadata:
  author: vanducng
  version: "1.0.0"
---

# asciinema

> Script the session, drive it, gate the cast, prove every scene from the cast, then publish. Never record a live shell.

## What this skill is - and isn't

| Situation | Owner |
|---|---|
| README or PR demo of a CLI or TUI, `.cast` + GIF, asciinema.org upload | this skill |
| Recording a browser flow | `agent-browser` |
| Produced video, motion graphics, voiceover | `video` |
| Proving a TUI change frame by frame (no recording) | the project's own screen harness |

## Hard rules

1. **Sample data only.** A public demo runs against a fixture server or sandbox account with generic content. The session script points the tool at an isolated config dir (`XDG_CONFIG_HOME` in a temp dir, fake auth) so it cannot read the real one.
2. **Never record an interactive shell.** A real prompt and rc files leak user, host, and paths. The session script prints a fake `$` prompt and types each command.
3. **The leak gate is not optional.** `record.sh` rewrites the header `command` (asciinema stores the full command line, absolute paths included) and fails on home paths, loopback addresses, token names, and every `--deny` string. A failure means fix the script, never edit around the gate.
4. **Prove scenes from the cast.** Run `cast-check.py --expect` with one marker per scene before calling a recording done. A missing marker means the choreography drifted.
5. **Upload is outward-facing.** Confirm with the user before `asciinema upload` or any visibility change. Uploads default to unlisted.

## Workflow

1. **Build first.** Build the binary under demo before recording; compile output inside the cast is noise. Start the fixture server if the tool needs one.
2. **Write the session script.** Copy `assets/demo-session.sh`. Setup must be silent: every byte printed lands in the cast, even if `clear` follows. The script sets its own env from its arguments, because in TUI mode it runs with the tmux server's environment, not the caller's. One `note` per scene, `clear` between scenes, about 90 seconds in total.
3. **Write the drive script (TUI only).** It is sourced once `--ready` text is on screen and gets these helpers:
   - `k KEY...` - one argument per key. A single character is sent literally (`/`, `?`, `;`); longer names are tmux keys (`Enter`, `Escape`, `Up`, `C-c`). `KEY_DELAY` paces it (default 0.28s).
   - `lit TEXT` - types into an open prompt one character at a time (`TYPE_DELAY`, default 0.07s).
   - `wait_for TEXT [SECS]` - blocks until the text is on screen. Wait on stable UI text, then `sleep` only for viewer pacing.
   - The script must end by quitting the TUI, so the session script reaches its closing scene.
4. **Record.**
   ```bash
   bash scripts/record.sh --session demo-session.sh [--drive drive.sh --ready '? help'] \
     --out "$TMPDIR/demo" --size 120x32 --title '<tool>: <one line>' \
     --deny '<real account name>' --gif docs/assets/demo.gif -- <session args>
   ```
   Without `--drive` it records `--headless` with no tmux. It prints `cast=` and `gif=` paths and exits 1 on a leak.
5. **Verify each scene.** Times match the player because the idle limit is applied.
   ```bash
   uv run scripts/cast-check.py "$TMPDIR/demo/demo.cast" \
     --expect 'timeline=Now · ' --expect 'help=Keys' --at 42.5 --rows 15
   ```
   Any `python3` with `pyte` also works. It exits 1 on a missing marker or a nonzero session exit. `--at` prints the exact screen at a time; use it to inspect a scene that looks wrong.
6. **Review the GIF.** Pull a few frames (`ffmpeg -v error -ss 30 -i demo.gif -frames:v 1 f.png`) and read them for font, colors, and wrapping. GIF seeking is approximate; text truth comes from `--at`.
7. **Publish** (after the user confirms):
   ```bash
   export ASCIINEMA_SERVER_URL=https://asciinema.org
   asciinema auth        # once per machine
   asciinema upload "$TMPDIR/demo/demo.cast" --visibility public --title '<tool>: <one line>'
   ```
   `auth` prints a connect URL that links this machine to whichever account opens it. Treat it as a credential: keep it out of chat, logs, and PRs, open it in the user's signed-in browser (or hand it to them), and confirm the signed-in account is the intended one before connecting.
8. **README.** GitHub's image proxy fails on asciinema's `.svg` preview (503 "Error Fetching Resource"), so commit the GIF and link it to the player:
   ```markdown
   [![<tool> demo: <what it shows>](docs/assets/demo.gif)](https://asciinema.org/a/<id>)
   ```
   Check how GitHub renders it with `gh api markdown -f text='...' -f mode=gfm` and curl the `camo.githubusercontent.com` URL it returns. Every upload gets a new id: update the link, and ask before deleting superseded uploads.

## Scripts

| Script | Does |
|---|---|
| `scripts/record.sh` | Records headless or tmux-driven, scrubs the header, runs the leak gate, renders the GIF with agg |
| `scripts/cast-check.py` | Replays the cast through `pyte`: `--expect LABEL=TEXT` timings, `--at SECONDS` screen dumps, exit status |
| `assets/demo-session.sh` | Session template: silent setup, `note`, `run` with a fake prompt and typed commands |

## Gotchas (asciinema 3.x, agg 1.9)

- `auth` and `upload` say "No asciinema server configured for this CLI." until `ASCIINEMA_SERVER_URL` is set.
- `--idle-time-limit` only writes metadata; captured timings stay raw. Players apply it, `record.sh` passes the same value to agg, and `cast-check.py` applies it.
- v3 casts store the interval since the previous event and `term.cols/rows`; v2 stores absolute times and `width/height`. `cast-check.py` reads both.
- `rec` refuses an existing file without `--overwrite`.
- tmux reads a lone `;` argument as a command separator; `k` and `lit` escape it.
- Keep the tmux pane the same size as `--window-size` with the status bar off (`record.sh` does) so `wait_for` reads the screen the cast records.
- State carries across scenes. A CLI scene that ticks an item turns a later TUI toggle key into an untick. Re-run `cast-check.py` after any scene change.
- A TUI on the alternate screen restores the previous screen on quit, so TUI markers only match while it runs.
- About 1 MB of GIF for 80 seconds at 120x32, font 14, 15 fps.

Install: `brew install asciinema agg tmux`, and `uv` or `pip install pyte` for `cast-check.py`.
