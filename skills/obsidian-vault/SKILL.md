---
name: obsidian-vault
description: "Capture ideas and notes into the personal Obsidian PARA vault (markdown on disk). Use notesmd-cli when installed, else write files. Activates when the user says 'add an idea', 'capture this', 'vault note', 'inbox this', 'log this in Obsidian', 'keep track of this idea', or asks to file something in PARA. Not for the engineering journal (vd:journal) or Structured.app tasks."
license: MIT
argument-hint: "[idea | --daily | --promote <title>]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Obsidian Vault

The vault is a git folder of Markdown. Agents edit files. Do not drive the Obsidian GUI unless the user asks to open a note.

## Resolve the vault

```text
$OBSIDIAN_VAULT
else $HOME/git/personal/vault
```

Verify `AGENTS.md` exists at that root. If missing, stop and ask.

## Hard rules

1. **Filesystem first.** Create/update `.md` files. `notesmd-cli` is optional sugar. Official `obsidian` CLI needs the app running and is only for `open`.
2. **Inbox, then promote.** New capture goes in `0 Inbox/` (ideas: `0 Inbox/Ideas.md`). Do not invent top-level folders.
3. **Append, do not rewrite.** Newest bullet first under `## Open`. Never delete an idea; move it to `## Promoted` when it becomes a project note.
4. **Android-safe names.** No `" * : < > ? \ |` in filenames. Spaces are fine.
5. **Do not commit plugin dirs.** `.obsidian/`, `.makemd/`, `.space/`, `.trash/` stay local.
6. **Structured MCP is one-way from here.** Vault daily note is source of truth for the list. When the user asks to put tasks on the planner, create Structured all-day tasks for that day (`create_task` + `day` + `is_all_day`). Use the vault's usual task prefix convention when one exists (discover from recent daily notes; do not hardcode org labels). Recurring habits use `create_recurring_task`. Do not try calendar export.
7. **Git only when asked.** Prefix `vault:`.

## Workflow

### Capture an idea

1. Resolve vault.
2. Open `0 Inbox/Ideas.md`.
3. Insert `- YYYY-MM-DD: <one line>` at the top of `## Open`.
4. If the user named a project, also add `0 Inbox/<short-title>.md` with a `[[wikilink]]` back to Ideas.

### Daily note

Path: `0 Inbox/Journals/Daily/YYYY-MM-DD.md`. Create if missing. Match existing notes in that folder.

### Promote

Move the Ideas bullet to `## Promoted`. Write `1 Projects/<title>/<title>.md`. Link both ways.

### Optional CLI

```bash
notesmd-cli list-vaults
notesmd-cli create "0 Inbox/foo.md" --content "..."
notesmd-cli search-content "term"
```

If `notesmd-cli` is missing, write the file with the editor tools.

## Anti-patterns

- Dumping ideas into `vd:journal` (that is the engineering log).
- Opening Obsidian to "make it real". Git + Markdown is enough.
- Calling Local REST API / MCP unless the user already runs that plugin.
