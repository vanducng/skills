# Check Workflow

Validate-only. No writes. No subagents. Run this before `update` on an unfamiliar repo, or as a periodic health check.

## What it checks

| Check | How | Pass criteria |
|---|---|---|
| **Required files present** | `ls docs/*.md README.md` | All required files from canonical set exist |
| **Size budget** | `wc -l docs/*.md README.md \| sort -rn` | All files ≤ `docs.maxLoc` (default 800) |
| **Freshness** | `git log -1 --format=%cI -- <file>` per doc | No file older than 90 days when code has changed since |
| **Internal links** | `node $HOME/.claude/scripts/validate-docs.cjs docs/` | No broken `[link](./file.md)` references |
| **Code references** | same script | Cited paths (e.g. `src/foo.ts:42`) still exist |
| **Config keys** | same script | Referenced config keys present in config files |

## Workflow

### Step 1 — Required files

Canonical required set (from `SKILL.md`):
- `README.md`
- `docs/development-guidelines.md`
- `docs/system-architecture.md`
- `docs/tech-stack.md`
- `docs/deployment.md`

For each missing → report. Suggest `init` if many missing, `update` if a few.

### Step 2 — Size check

```
wc -l docs/*.md README.md 2>/dev/null | sort -rn
```

Compare each to `docs.maxLoc`. Report files over budget with overage amount.

### Step 3 — Freshness

For each doc file:
```
git log -1 --format=%cI -- <file>           # last edit to doc
git log -1 --format=%cI --since=<that-date> # any code commit since?
```

A doc is "stale" if:
- Last edited > 90 days ago **AND** code commits exist since then
- Or last edited > 180 days ago regardless

Report each stale file with last-edit date and commit count since.

### Step 4 — Validation script

```
node $HOME/.claude/scripts/validate-docs.cjs docs/
```

Forward all output. Group by file. Highlight any error (vs warning).

## Output format

```
# Docs Health Check — <date>

## Required files
- [x] README.md (120 LOC)
- [x] docs/development-guidelines.md (180 LOC)
- [x] docs/system-architecture.md (450 LOC)
- [x] docs/tech-stack.md (90 LOC)
- [ ] docs/deployment.md — MISSING

## Size budget (max 800)
- docs/system-architecture.md: 920 LOC — 120 OVER

## Freshness
- docs/tech-stack.md: last edit 2025-11-12 (182 days ago, 47 code commits since) — STALE

## Validation
docs/system-architecture.md:
  - WARN: broken link → ./missing-page.md
  - ERROR: cited path does not exist → src/old-module/foo.ts

## Recommended next action
- `vd:docs update` — drift detected in 2 files
- Or `vd:docs init` for missing-file backfill
```

## Hard rules

- **No writes.** Read-only across the board.
- **No subagents.** Cheap and synchronous — no delegation needed.
- **Surface every finding.** Even minor ones — this is the cheap step to fix them.
- **Don't flag out-of-scope files.** `changelog.md`, `roadmap.md`, `prd.md`, `codebase-summary.md` aren't `vd:docs`'s problem — if they exist, leave them alone.
