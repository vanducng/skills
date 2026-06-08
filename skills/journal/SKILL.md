---
name: journal
description: "Write a focused engineering journal entry — retrospective on what just shipped or post-mortem on what just broke. Use after vd:ship, vd:cook, or right after an incident while context is fresh. Saves to .work/journals/ when the project is migrated, else plans/journals/ (personal dev log, not project docs)."
license: MIT
argument-hint: "[topic] [--incident] [--quick] [--since <ref>]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Journal

## What this skill is — and isn't

| Skill | Question it answers | Output |
|---|---|---|
| `vd:ship` | "Land the branch." | Merged target, PR URL |
| `vd:cook` | "Execute the plan." | Code, tests, plan status |
| **`vd:journal`** | **"What just happened, why, and what should future-me know?"** | **One markdown file in `.work/journals/` (migrated) or `plans/journals/` (legacy)** |

Journal **records**. It does not redesign, retest, or roll back. If writing the entry surfaces a real bug — stop, kick to `vd:fix` or `vd:cook`, then come back to journal once the fact pattern stabilises.

## Modes

| Mode | Voice | Use when |
|---|---|---|
| _(default)_ **retro** | Calm, structured. What shipped, what was tricky, what's next. | After `vd:ship`, `vd:cook`, end of session. |
| `--incident` | Brutal-honest, 2am-developer voice. Root cause without euphemism. | A failure happened — outage, data loss, broken migration, repeated test failure, security finding. |
| `--quick` | 3–5 lines, no formal structure. | Drive-by note — small fix, minor decision, surprising bit of context. Pairs with either voice. |

## Hard rules

1. **Specificity beats vibe.** Every entry names at least one concrete artifact: commit SHA, PR #, file path, error string, metric. "We had perf issues" is not a journal entry.
2. **Decision, not narration.** If a choice was made, name the alternatives that lost and why. Otherwise the future reader can't reverse-engineer the call.
3. **Brutal in `--incident`, not performative.** Honesty about root cause is the point — not theatrics. "We shipped without testing the migration" beats both "an oversight occurred" *and* "this is a fucking disaster".
4. **No new design decisions.** Journal records what already happened. New decisions belong in `vd:brainstorm` or `vd:plan`.
5. **One file per event.** Don't append to yesterday's entry. New event → new file. Cross-link if related.
6. **Stop at one page.** Retro: 200–400 words. Incident: 300–600 words. If it's longer, it's a post-mortem doc — link to the journal entry from there, don't bloat the journal.

## Arguments

| Flag | Effect |
|------|--------|
| `[topic]` | Free-text title hint. If omitted, derived from branch + recent commits. |
| `--incident` | Switch to incident voice + structure. Default is retro. |
| `--quick` | Skip the full structure — write a 3–5 line note instead. |
| `--since <ref>` | Scope change analysis to commits since `<ref>` (default: last journal entry or branch divergence point). |
| `--no-subagent` | Force inline writing in main context. Default: delegate to `journal-writer` subagent if available. |

## Workflow

### 1. Gather facts (do not write yet)

- `git log --oneline <since>..HEAD` — what landed
- `git diff --stat <since>..HEAD` — surface area
- Read `## Plan Context` from the hook injection — if a plan dir exists, scan `plan.md` for phase status and the most recent phase file
- For `--incident`: also collect the specific error string, failed test name, log line, or metric that triggered this entry

If `<since>` isn't given:

```
1. Look in .work/journals/ then plans/journals/ for the most recent file → use its date
2. Otherwise, find the merge-base with the default branch
3. Otherwise, last 20 commits
```

### 2. Decide mode (if not flagged)

- Failure / red CI / rollback / security finding → `--incident`
- Successful ship / completed plan / end-of-session wrap → retro (default)
- One-line context worth saving → `--quick`

### 3. Pick the writer

| Condition | Writer |
|---|---|
| Default, `journal-writer` subagent available | Delegate to `journal-writer` via `Agent` tool — keeps main context clean |
| `--no-subagent`, or subagent unavailable | Write inline using the templates below |
| `--quick` | Always inline — subagent overhead > entry size |

If delegating, pass: mode, topic hint, `<since>` ref, plan dir (if any), and the relevant facts already gathered. **Do not** pass full git output — let the subagent re-gather scoped to what it needs.

### 4. Write the file

Path: write to the injected path (`.work/journals/` when the project is migrated, else legacy `plans/journals/`); when reading prior artifacts, check both. Filename: `journal-{YYYYMMDD-HHMM}-{slug}.md`. Use the naming pattern from the session hook (`## Naming` block) when present.

> Journals are a personal dev log — what *I* learned, decided, or broke — not project documentation. `./docs/` is for artifacts shared with the team (architecture, code standards, changelog).

Final handoff must include an openable entry location, such as
`[journal-entry.md](/absolute/path/to/journal-entry.md)` or
`file:///absolute/path/to/journal-entry.md`, not just the basename.

### 5. Cross-link

- If a `plan.md` exists, append a one-line link to this entry under a "Journal" section at the bottom of `plan.md`.
- If the entry references a PR, drop the PR # in the frontmatter.
- Do **not** auto-edit `CHANGELOG.md` — that's `vd:ship`'s job.

## Templates

### Retro (default)

```markdown
---
date: YYYY-MM-DD HH:mm
mode: retro
branch: <branch>
pr: <#N or n/a>
plan: <plan-dir or n/a>
---

# {Title — what shipped, in 6 words or less}

## What shipped
- {bullet} ({commit-sha or PR#})
- ...

## Why this shape
{1 short paragraph. The decision and the alternatives rejected. If the plan covered this, link the phase file instead of repeating it.}

## What was harder than expected
- {one or two specific snags — file/error/metric}

## What the next dev should know
- {non-obvious fact, gotcha, or convention introduced}

## Next steps
- {actionable, owned, optional date}
```

### Incident

```markdown
---
date: YYYY-MM-DD HH:mm
mode: incident
severity: critical | high | medium | low
component: <system/feature>
status: ongoing | mitigated | resolved
branch: <branch>
---

# {Title — what broke, in 6 words or less}

## What happened
{Factual, terse. When, where, blast radius.}

## The brutal truth
{Root cause, no euphemism. The mistake, the missed signal, the bad assumption.}

## Technical detail
{The error string. The failed test. The metric. The query. At least one concrete artifact.}

## What we tried
- {attempt} → {why it didn't work}

## Lesson
{One sentence a future dev can change behaviour from. Not "be more careful". Something specific — "add a migration dry-run step before ship", "alert on queue depth > 1k".}

## Next steps
- {action} — {owner} — {by when}
```

### Quick

```markdown
---
date: YYYY-MM-DD HH:mm
mode: quick
---

# {Title}

{3–5 lines. One concrete artifact. Move on.}
```

## Token efficiency

- **Default to subagent delegation.** A retro entry doesn't need to live in main context — `journal-writer` re-gathers what it needs and writes the file directly.
- **`--quick` stays inline** — subagent round-trip costs more than the entry.
- **Never read full git diffs in main** when writing inline — `git log --oneline` and `git diff --stat` are enough; pull the actual diff only for files the entry will name.
- **One file write, no review loop.** Journal is not code — don't self-review. The next entry corrects yesterday's wrong take if it matters.

## Quality bar

- **Names, not vibes.** Every entry has at least one path, SHA, PR#, error string, or metric.
- **Decision visible.** A reader six months later can answer: "what did they choose, and what did they reject?"
- **Lesson is behavioural.** "Be more careful" fails the bar. "Add a `--dry-run` flag to migrate.sh" passes.
- **No filler.** If a section in the template has nothing concrete to say, delete it.
- **Honest gaps.** "Root cause unclear — see follow-up issue #N" is allowed and preferred over invented certainty.

## Workflow position

**Typically follows:** `vd:ship` (auto-invokes this skill in Step 8 — manual run is for skipped or out-of-pipeline cases), `vd:cook` (end of phase or end of plan), `vd:fix` (after incident is mitigated).

**Terminal skill** — no typical successor. The next time you want to make a change, start a new pipeline at `vd:scout` or `vd:plan`.

**Compares to:**
- `vd:ship` Step 8 — same writer, but `vd:ship` calls it as part of the pipeline. `vd:journal` is the manual entry point: out-of-band incidents, mid-session reflections, or when ship was run with `--skip-journal`.
- A PR description — PR body is for reviewers landing the change; journal is for the dev opening this folder six months later.
