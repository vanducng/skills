# Data sources & correction signals

Where the `--mine` finders look, and what a "correction" looks like in each source. All reads are local — no external services.

## Sources

| Source | Location | Read with |
|---|---|---|
| Session transcripts | `~/.claude/projects/<project-hash>/*.jsonl` (one JSON event per line) | Read / Grep |
| Git history | the repo at `repoPath` | `git log`, `git show`, `git log -p -- CLAUDE.md` |
| PR review comments | the repo's remote | `gh pr list`, `gh api .../pulls/comments`, `gh search` |
| Existing rules (for dedupe) | `~/.claude/CLAUDE.md`, `~/.claude/rules/*.md`, project `AGENTS.md` (or `CLAUDE.md`, often symlinked to it), `docs/code-standards.md` | Read |

Resolve `~` to `$HOME` at read time. Never hardcode an absolute home path — the skill must work for any user.

## Correction-signal patterns

A correction is the user steering Claude away from what it just did. Grep transcripts and commit subjects for these (case-insensitive), then read surrounding context to confirm it's a genuine, generalizable correction and not a one-off task instruction:

```
\bno,? (don't|do not|stop|never|again)\b
\b(actually|instead|rather)\b
\bI (told|said|asked) you\b
\b(use|prefer) .+ not .+
\bdon'?t (use|add|create|write|commit)\b
\b(revert|undo|roll ?back)\b
\bwhy (did|are) you\b
\bevery time\b
```

Git: revert commits, subjects containing `fixup`, `oops`, `actually`, `revert`, and any diff touching `CLAUDE.md` / `rules/` (each rule edit is a recorded correction).

PR reviews: the same critique appearing on **multiple** PRs is the strongest signal — a recurring nit is a rule waiting to be written.

## What disqualifies a candidate

- Appears **once** — not a pattern, drop it (Hard rule 3).
- Already covered by an existing rule — dedupe in the Cluster phase (Hard rule 2).
- Task-specific instruction ("use port 8081 for this demo") — not generalizable.
- Vague / unenforceable ("be smarter") — the skeptic kills these.

## Privacy

Transcripts and history may contain secrets or private content. Finders extract only the structured correction (quote + implied rule); they do not copy raw transcript bodies into the result, and nothing leaves the machine.
