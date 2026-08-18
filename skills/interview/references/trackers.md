# Tracker operations for `vd:interview --wayfinder`

The map needs five operations from whatever tracker the repo uses: create the map issue, create child tickets, wire blocking edges, query the frontier, and claim/close tickets. Resolve the tracker in this order and say which you picked:

1. **The repo declares one** (`AGENTS.md`, `CONTRIBUTING.md`, or the user names it) - use that.
2. **GitHub Issues** - the repo has a GitHub remote and `gh auth status` succeeds.
3. **Jira** - `vd:jira` is configured for this project.
4. **Local markdown** - no tracker available; files under the injected `Plans:` path.

Labels keep the `wayfinder:*` prefix so existing maps still query. That prefix is a tracker type, not a skill ID.

## GitHub Issues (`gh`)

| Operation | Command |
|---|---|
| Create map | `gh issue create --title "<map name>" --label wayfinder:map --body-file <map.md>` (create labels once with `gh label create`) |
| Create ticket | `gh issue create --title "<question gist>" --label "wayfinder:<type>" --body $'## Question\n<question>'` then link as sub-issue of the map (native sub-issues via `gh api` `addSubIssue`; fall back to a `Map: #<n>` body line + task-list on the map if unavailable) |
| Blocking edge | Native issue dependencies ("blocked by") via the issue UI/API where the plan supports it; fall back to a `Blocked by: #<n>` body line |
| Frontier query | Open, unassigned children whose blockers are all closed. GitHub label filters are exact-match (no prefix search), so query each type label: `for t in research prototype grilling task; do gh issue list --label "wayfinder:$t" --no-assignee --state open --json number,title; done` then drop tickets whose dependency field/`Blocked by:` line names an open issue |
| Claim | `gh issue edit <n> --add-assignee @me` |
| Resolve | `gh issue comment <n> --body "<answer>"` then `gh issue close <n>` |

## Jira (`vd:jira`)

Map = an Epic (or a Task labelled `wayfinder-map`); tickets = issues linked to it. Blocking uses Jira's native `blocks` link type; the frontier is a saved JQL: `parent = <MAP> AND status != Done AND assignee IS EMPTY` filtered to issues with no open inward `is blocked by` links. Claim = assign; resolve = comment + transition to Done. Follow `vd:jira` for project keys, types, and transitions.

## Local markdown (fallback)

No shared tracker - the map lives in the repo's artifact area (still shareable through git):

```
{Plans:}/wayfinder-{slug}/
  map.md                    # the map body, plus a "## Tickets" index table the tracker would otherwise render
  tickets/NNN-{slug}.md     # one file per ticket
```

Ticket file frontmatter carries what the tracker would:

```markdown
---
title: "<question gist>"
type: research | prototype | grilling | task
status: open | closed
assignee: <name or empty>
blocked_by: [NNN, NNN]
---

## Question
<the question>

## Resolution   <!-- added when closed -->
<the answer>
```

Frontier = `status: open`, empty `assignee`, all `blocked_by` ids closed. Claim = write your name into `assignee` (commit it - the commit is the concurrency guard). Keep `map.md`'s Tickets table in sync when tickets open/close.

## Concurrency notes (all trackers)

- Claim **first**, before any reading beyond the ticket body - two sessions resolving one ticket wastes both.
- Re-read the map right before writing to it; another session may have appended Decisions since you loaded it.
- Never edit another session's claimed ticket except to add a blocking edge it needs to know about.
