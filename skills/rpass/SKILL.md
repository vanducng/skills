---
name: rpass
description: "Create, update, share and remove notes in RPass, Rippling's password manager, through the Aside browser without printing secrets. RPass has no CLI or API: the vault lives in its browser extension, so scripts/rpass.py drives the extension page and the Rippling share page with `aside repl`. Builds copy-paste .env notes from local .env files and shares them with people or Rippling groups at Use, View or Manage. Use when the user says 'put these keys in RPass', 'share the creds in rpass', 'create an rpass note', 'share with the dev team in RPass', 'who has access to the rpass note', or 'move the keys to RPass'. Not for gopass (vd:gopass) or 1Password (vd:onepassword)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# rpass

RPass is the company password manager inside Rippling. There is no CLI and no public vault API; the vault is the RPass browser extension, signed in through the user's Rippling session. Drive it with `scripts/rpass.py`, which writes a mode-600 Aside script, runs it with `aside repl`, deletes it, and prints only its own `RPASS:` lines.

## Rules

1. **Never print a value.** Do not read an item's page text, do not `cat` the body file, and do not echo `aside repl` output yourself. An opened note shows its whole body in the page text, so one stray `innerText` leaks every key. Use only `rpass.py`; it checks field values by equality, never by printing them.
2. **Pick the Aside account signed in to the company Rippling.** `aside host profiles --account <id>` lists profiles per account; pass `--account <id>` or `<id>:<profile>`. A wrong account opens a different vault or none.
3. **Company vault only.** Personal-vault items cannot be shared. `put` aborts when the vault picker shows a personal vault; pass `--vault "<exact vault name>"` to require one.
4. **Shape secrets as .env blocks** so people copy and paste: `rpass.py envblocks --title "<what>" --out <file> <dir>/.env ...` writes one `# ===== <path> =====` block per file, mode 600. Leave out keys for personal machines.
5. **Share to groups, not lists of people,** when a team owns the work: `--add "Teams > Org > Team"` as the picker shows it. Then add only the people outside the group. `access` lists the resolved people.
6. **Access levels:** `use` (Use but not view), `view` (Use and view: needed to copy values), `manage` (use, view, edit, share; the highest level on a note).
7. **Every write is the user's call:** creating, editing, sharing and removing all reach other people. Confirm the note name, vault and recipients first. `remove` needs `--yes`.

## Commands

```bash
S=<this skill dir>/scripts/rpass.py
python3 $S envblocks --title "app API keys" --out /tmp/note.env services/api/.env services/worker/.env
python3 $S put    --account <id> --name <note-name> --body-file /tmp/note.env [--vault "<vault>"]   # create, or edit when the name exists
python3 $S share  --account <id> --name <note-name> --add "Teams > Org > Team" --access manage [--add "<person>"] [--remove "<person>"] [--set "<existing>"]
python3 $S access --account <id> --name <note-name>        # who has access, and the resolved people
python3 $S remove --account <id> --name <note-name> --yes
rm -f /tmp/note.env
```

Each command exits 1 and prints `ABORT: ...` when a check fails: a name that matches several picker entries, a personal vault, or a field that did not take the value.

## What the page looks like

`references/ui-map.md` lists the selectors the script relies on (search box, item menu, share page test ids). Read it when a command stops matching the page after an RPass update.
