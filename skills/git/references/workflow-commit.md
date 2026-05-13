# Commit Workflow

Default: execute via `git-manager` subagent. `--inline` keeps it in main context.

## Tool 1 — Stage + analyze + secret scan

```bash
git add -A && \
echo "=== STAGED ===" && git diff --cached --stat && \
echo "=== SECURITY ===" && \
git diff --cached | grep -c -iE "(AKIA[0-9A-Z]{16}|api[_-]?key|token|password|secret|credential|private[_-]?key|-----BEGIN|mongodb://|postgres://|mysql://|redis://)" | awk '{print "SECRETS:"$1}' && \
echo "=== GROUPS ===" && \
git diff --cached --name-only | awk -F'/' '{
  if ($0 ~ /^\.github\//)            print "ci:"$0
  else if ($0 ~ /^(docs|README)/)    print "docs:"$0
  else if ($0 ~ /\.(md|txt)$/)       print "docs:"$0
  else if ($0 ~ /(test|spec|__tests__)/) print "test:"$0
  else if ($0 ~ /^\.claude/)         print "claude:"$0
  else if ($0 ~ /(package\.json|package-lock|pnpm-lock|yarn\.lock|go\.sum|Cargo\.lock|poetry\.lock|requirements\.txt|Gemfile\.lock)/) print "deps:"$0
  else if ($0 ~ /(Dockerfile|docker-compose|k8s\/|terraform\/|\.tf$|helm\/)/) print "infra:"$0
  else if ($0 ~ /(\.toml|\.yaml|\.yml|\.json|\.env\.example)$/) print "config:"$0
  else print "code:"$0
}'
```

**If `SECRETS > 0`:** STOP, surface the matching lines, block commit. See `safety-protocols.md`.

## Tool 2 — Split decision

**Single commit** when:
- Single group, FILES ≤ 3, LINES ≤ 50 → one `type(scope): description`
- Tightly coupled (feature + its test, refactor + its types) — keep together even if 2 groups

**Multi-commit** when groups are mixed:

| Group | Commit prefix |
|---|---|
| `ci:` | `ci(<workflow>): ...` |
| `infra:` | `chore(infra): ...` or `feat(infra): ...` |
| `deps:` | `chore(deps): ...` |
| `config:` | `chore(config): ...` |
| `test:` | `test(<scope>): ...` |
| `code:` | `feat|fix|refactor|perf(<scope>): ...` |
| `docs:` | `docs(<scope>): ...` |
| `claude:` | `feat|fix|perf(skill): ...` — note: in `.claude/` use only `feat`/`fix`/`perf`, not `docs` |

Order: ci/infra/deps/config → test → code → docs (config-ish things first so code commits don't sneak in a lockfile bump).

## Tool 3 — Pre-commit checks

Before each commit:
1. **Lint** — run the project's lint command if present (`package.json` scripts, `Makefile`, `pyproject.toml`, etc.). If it fails, abort and surface output.
2. **Search related issues** — `gh issue list --search "<topic>"` if `gh` is available and the message looks issue-worthy. Add `Closes #N` / `Refs #N` to the body if a clear match exists.

Skip these for `chore(deps)`, `chore(config)`, and pure `docs:` commits where lint is irrelevant.

## Tool 4 — Commit

**Single:**
```bash
git commit -m "type(scope): description"
```

**Multi (sequential — reset, re-stage by group, commit):**
```bash
git reset
git add <group-1-files...>
git commit -m "chore(deps): bump <package>"
git add <group-2-files...>
git commit -m "feat(<scope>): <description>"
# ...etc
```

**Body** (HEREDOC for multi-line):
```bash
git commit -m "$(cat <<'EOF'
feat(<scope>): <description>

<optional 1-2 sentences on why, not what>

Closes #N
EOF
)"
```

## Tool 5 — Push (only for `cp` verb)

```bash
git push origin HEAD && echo "✓ pushed: yes" || echo "✓ pushed: no"
```

If no upstream: `git push -u origin HEAD`.
On `non-fast-forward`: report, suggest `git pull --rebase`. Do not force-push.

See `workflow-push.md` for full push error handling.

## Hard rules

- **Never** commit `.env`, credentials, `*.key`, `*.pem`, `secrets/`.
- **Never** use `--no-verify` to bypass hooks. Hook fail = fix the issue.
- **Never** include AI attribution in commit messages.
- **Never** amend an already-pushed commit. New commit instead.
