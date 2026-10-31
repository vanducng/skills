# Applying PARA to a store

Use the same four buckets and the same spelling on every store that holds information by category. Create a folder on a store only when that store has something to put in it.

## Stores that do and do not take PARA

| Store | PARA? | Notes |
|---|---|---|
| File system, cloud drive | yes | A cloud drive is for content others need to open. |
| Notes app or vault (Obsidian, Notion) | yes | Best for text. Link notes rather than copying them. |
| Task manager | Projects and Areas only | Tasks belong to an outcome or a responsibility. |
| Calendar, email, chat, ticket tracker | no | Chronological by nature. Link to them from PARA pages. |
| Photos | no | Chronological. |
| Password manager | no | Keep sensitive records there, not in PARA folders. |

Where to put a new item:

1. An appointment goes to the calendar.
2. A task goes to the task manager.
3. Text goes to the notes app.
4. Shared content goes to the cloud drive.
5. Anything else goes to the file system.

## Human-browsed stores

These are stores a person scans by eye: a file system, a drive, a vault.

- Use numbered top folders so they sort by actionability: `0 Inbox`, `1 Projects`, `2 Areas`, `3 Resources`, `4 Archives`.
- Optional naming makes a mixed list readable at a glance:
  - Projects get a short label, optionally prefixed with an emoji;
  - Areas use Capitalized Titles;
  - Resources use lowercase titles.
- Every file lives inside a named item folder, never loose at a bucket root.
- Treat `Downloads` and `Desktop` as inboxes to clear, not as homes.
- A fresh start moves everything into `4 Archives/Archive <YYYY-MM-DD>/`, then pulls forward only what is active.

## Agent knowledge base

This covers a markdown tree that agents write and read as memory, for example an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/open-knowledge-format) bundle. If the repository defines its own contract for the tree, follow it for names and fields.

**Layout**

- Use plain bucket names (`inbox/ projects/ areas/ resources/ archives/`), because code builds the paths.
- Each project, area or resource is one page, `<bucket>/<slug>.md`, with kebab-case slugs.
- Pages are typed in frontmatter (`type: Playbook | Topic | Decision`), not by subfolder.

**Inbox**

- One dated file per day (`inbox/YYYY-MM/YYYY-MM-DD.md`), with fixed sections owned by the writers that fill them.
- Entries are append-only, each with a stable source anchor.
- A day never moves and is never edited after it closes, so citations stay valid.

**Frontmatter**

| Page | Carries |
|---|---|
| Every page | `type`, `title`, `status: draft \| stable \| deprecated`, `generated: {by, at}`, `stale_after` |
| Project | `goal` and `due` |
| Area | a one-line standard |

An archived page is moved, set to `deprecated` and given `archived_at`. Its first line says why it was archived and where its facts went.

**Consolidation passes**

| Pass | Does |
|---|---|
| Daily | Files closed inbox days into pages as cited facts. Supersedes a fact by moving the old line to `## History`, never deleting it. |
| Weekly | The PARA weekly review: rewrite summaries, retitle, sort, update. |
| Monthly | Lint, and propose archives and new areas. |

A person approves every move. Agents propose; they never archive on their own.

**Anti-rot**

- Link live state (ticket status, thread state), never copy it.
- Generate indexes, and fail a check when they drift.
- When a page is past `stale_after`, verify it against its sources before acting on it.
- Read through a bounded context command: the page top plus recent filed entries. Leave history and archives out unless the task names them.
- Lint each pass. Block on a missing citation, a silently dropped line, an invalid lifecycle value or a copied live state.

## Existing structures

When a store already has PARA or a variant (`Projects`, `Areas`, `Active`, `Reference`, `Done`, an extra `Templates` or `Inbox`), do not default to a fresh start. Offer three paths:

- **audit and update** what is there;
- **sort only the loose items** into it;
- **fresh start**.
