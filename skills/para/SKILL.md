---
name: para
description: "Apply Tiago Forte's PARA method (Projects, Areas, Resources, Archives) as canonically defined to any store: a file system, cloud drive, notes app or Obsidian vault, or a markdown knowledge base that agents read and write. Use to classify items by actionability, decide project vs area vs resource vs archive, set up or audit a PARA structure, plan a reorganization or migration, run a weekly or monthly PARA review, or design agent memory on PARA without rot. Triggers: 'PARA', 'is this a project or an area', 'organize by actionability', 'set up PARA', 'PARA audit', 'archive finished projects', 'weekly review'. Not for capturing one note into the personal vault (vd:obsidian-vault) or the engineering journal (vd:journal)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# PARA

PARA sorts information by how actionable it is right now, not by what kind of thing it is or where it came from. Four buckets, most to least actionable:

| Bucket | Is | Test |
|---|---|---|
| Projects | an outcome with a goal and a deadline or timeframe, being worked on now | can it be finished, and is something happening on it this week or month? |
| Areas | an ongoing responsibility with a standard to maintain, no end date | would something suffer if it were neglected? |
| Resources | a topic of interest or reference, no responsibility attached | useful to look up or share, but nothing breaks if ignored |
| Archives | anything inactive from the other three | done, dropped, handed off, or no longer interesting |

An inbox sits in front of the four. It holds capture, in time order, until a review files it. Calendars, email, chat and ticket trackers are chronological by nature and are never reorganized by PARA; PARA pages link to them.

Read `references/classification.md` before classifying anything non-obvious. Read `references/stores.md` before setting PARA up on a specific store.

## Hard rules

1. **Plan first, act second.** Never create, move, rename or archive anything until a complete written plan is shown and the owner says yes. Say this before the first scan.
2. **Never delete; archive.** Archives keep everything findable and can be reactivated. Superseded facts are kept as history, not removed.
3. **Link, never duplicate.** One home per item. Relate items with links or tags, never copies.
4. **Most actionable wins a tie.** Project over Area, Area over Resource. Inside one Area, file to the most specific active Project.
5. **Just in time.** Create a folder or page only when there is something to put in it. No empty scaffolding.
6. **Top level only.** PARA governs the four buckets and one level of named items inside them. Keep everything below informal.
7. **Project names are labels.** A short label, with the goal and the deadline kept beside it (inventory, frontmatter), never in the name.

## Classify an item

1. Goal and deadline, with work happening now? Then it is a **Project**, even when it lives inside an Area.
2. Otherwise, an ongoing standard someone is accountable for? Then it is an **Area**.
3. Otherwise, useful reference or interest? Then it is a **Resource**.
4. Otherwise, inactive? Then it goes to **Archives**. If it is none of these, leave it in the inbox, or ask whether to delete it.

Watch for the two classic errors:
- an Area disguised as a Project ("improve sales" has no end);
- an actionable unit buried in an Area ("2026 tax filing" belongs in Projects, not under Finances).

A future project is not a project. Keep it as an idea on its Area until work starts.

When unsure, ask in small batches of 3-5 items, giving a recommended answer and one line of reason for each. Never guess silently on an item you cannot read; describe it and offer 2-3 placements.

## Reorganize a store

1. **Discover (read-only).**
   - Read any existing context (a personal context doc, a project list) before asking anything.
   - Ask for:
     - current projects, each with a goal and a deadline;
     - areas of responsibility;
     - time-bound initiatives inside each area (these become Projects);
     - topics of interest.
   - Scan the top level, opening unclear items to judge them by content rather than by name.
2. **Choose the path when PARA, or something like it, already exists:**
   - audit and update;
   - sort only the loose items;
   - fresh start (everything into a dated archive first, then pull forward only what is active).
3. **Resolve every ambiguous item** before writing the plan, so the plan has no open questions.
4. **Present the plan.** It lists:
   - every folder or page to create;
   - every move with its source and destination;
   - every archive;
   - what is deliberately not created yet.
5. **Execute** only after an explicit yes. A change to the plan is re-shown and needs a new yes.
6. **Report:**
   - counts per bucket;
   - the judgment calls made, so they can be double-checked;
   - anything that could not be placed or moved, and what is needed to resolve it.
7. **Write the inventory:**
   - Projects, each with its goal and due date;
   - Areas, each with the standard it maintains;
   - Resources, each with one line;
   - Archives.

## Reviews

| Cadence | Do |
|---|---|
| Weekly | **Retitle**: names that no longer match their content. **Sort**: finished projects to Archives, resources that became responsibilities to Areas. **Update**: new projects that need a home, stalled projects to cancel or archive, archived items to reactivate. Clear the inbox. |
| Monthly | Areas and Resources that are no longer held or wanted go to Archives. Look for themes mentioned 3 or more times that deserve their own Area or Resource. |
| Yearly | Re-architect: which Areas still describe the owner's life and work? |

A healthy project list holds 10-20 active Projects. More than 25 usually means Areas in disguise or projects that should be cancelled. Two signals to check:
- a goal with no project is a dream, not yet activated;
- a project with no goal is a hobby.

## Agent knowledge bases

The same canon applies when agents keep memory. The extra rules exist because agents act on stale text with confidence:
- capture is append-only and dated;
- consolidation happens in scheduled passes, never on every write;
- live state (ticket status, thread state) is linked, never copied;
- indexes are generated;
- every page carries its lifecycle (`status`, `stale_after`).

See `references/stores.md`, Agent knowledge base. When a repository defines its own contract for such a store, that contract wins on paths and fields. This skill supplies the classification and review rules.

## Sources

- Tiago Forte, *The PARA Method* (2023), and [The PARA Method](https://fortelabs.com/blog/para/).
- Forte, [The Weekly Review is an Operating System](https://fortelabs.com/blog/the-weekly-review-is-an-operating-system/).
- Andrej Karpathy, [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), for an agent-kept wiki with ingest, query and lint.
