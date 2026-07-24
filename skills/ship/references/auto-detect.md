# Auto-Detection Logic

Detect test runner, version file, changelog format, and target branch from project files.

## Test runner

First match wins:

| Check | Command |
|-------|---------|
| `package.json` has `"scripts": { "test": ... }` | `npm test` |
| `Makefile` has `test:` target | `make test` |
| `pytest.ini` OR `pyproject.toml` has `[tool.pytest]` | `pytest` |
| `Cargo.toml` exists | `cargo test` |
| `go.mod` exists | `go test ./...` |
| `Gemfile` + `Rakefile` with test task | `bundle exec rake test` |
| `build.gradle` / `build.gradle.kts` | `./gradlew test` |
| `pom.xml` | `mvn test` |
| `mix.exs` | `mix test` |
| `deno.json` | `deno test` |

Detection snippet:
```bash
if [ -f package.json ] && grep -q '"test"' package.json 2>/dev/null; then
  echo "npm test"
elif [ -f Makefile ] && grep -q '^test:' Makefile 2>/dev/null; then
  echo "make test"
elif [ -f pytest.ini ] || ([ -f pyproject.toml ] && grep -q '\[tool.pytest' pyproject.toml 2>/dev/null); then
  echo "pytest"
elif [ -f Cargo.toml ]; then
  echo "cargo test"
elif [ -f go.mod ]; then
  echo "go test ./..."
else
  echo "NONE"
fi
```

`NONE` → `AskUserQuestion`: "No test runner detected. Skip tests / provide test command?"

## Version file

| Check | Read |
|-------|------|
| `VERSION` plain file | full content |
| `package.json` → `version` | `jq -r .version package.json` |
| `pyproject.toml` → `version` | `grep '^version' pyproject.toml` |
| `Cargo.toml` → `version` | `grep '^version' Cargo.toml` |
| `mix.exs` → `@version` | `grep '@version' mix.exs` |

None found → skip version bump silently.

Bump rules:
- Official: patch (`X.Y.Z` → `X.Y.Z+1`).
- Staging: append `-rc.N` (increment N if an rc tag already exists).
- Beta: append `-beta.N` (increment N if a beta tag already exists).
- Major / breaking signal in diff (new top-level command, removed exported symbol, schema migration, `BREAKING CHANGE` in commit body) → `AskUserQuestion`: major / minor / patch.

## Changelog

| File | Format |
|------|--------|
| `CHANGELOG.md` / `CHANGES.md` / `HISTORY.md` | Keep-a-changelog |

None found → skip silently.

Entry shape:
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- `feat:` commits

### Changed
- `refactor:` / `perf:` commits

### Fixed
- `fix:` commits

### Removed
- explicit removals
```

Categorization sources, in order: conventional-commit prefix → file types touched (e.g. only `*_test.*` → "Test improvements") → diff content (new exported symbol → Added; modified → Changed).

## Default branch

```bash
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
```

Fallback:
```bash
git rev-parse --verify origin/main 2>/dev/null && echo main || echo master
```

## Staging / UAT branch

First existing wins:
```bash
# 1. plain names
for b in staging uat pre-prod preprod; do
  git rev-parse --verify "origin/$b" 2>/dev/null && { echo "$b"; break; }
done
# 2. release/* - pick the newest (most-recent commit)
git for-each-ref --sort=-committerdate --format='%(refname:short)' \
  'refs/remotes/origin/release/*' | head -1 | sed 's@^origin/@@'
```

None found → fall back to dev branch.

## Dev / beta branch

First existing wins:
```bash
for b in dev develop development beta; do
  git rev-parse --verify "origin/$b" 2>/dev/null && { echo "$b"; break; }
done
```

None found → fall back to default branch and warn that the requested mode has nowhere to land.

## Auto-release tooling

Probe for any of these - first match wins, used by Step 13 to decide skip-manual-tag:

| Marker | Tool |
|--------|------|
| `.goreleaser.yml` / `.goreleaser.yaml` | GoReleaser |
| `release-please-config.json` / `.release-please-manifest.json` | release-please |
| `.releaserc` / `.releaserc.{json,yaml,yml}` / `release.config.js` | semantic-release |
| `.changeset/config.json` | Changesets |
| `.github/workflows/release.yml` referencing any of the above tools | CI-driven release |

Detection snippet:
```bash
detect_release_tool() {
  [ -f .goreleaser.yml ] || [ -f .goreleaser.yaml ] && { echo goreleaser; return; }
  [ -f release-please-config.json ] && { echo release-please; return; }
  [ -f .releaserc ] || ls .releaserc.* 2>/dev/null | grep -q . && { echo semantic-release; return; }
  [ -f release.config.js ] && { echo semantic-release; return; }
  [ -d .changeset ] && [ -f .changeset/config.json ] && { echo changesets; return; }
  grep -lE 'goreleaser|release-please|semantic-release|changesets' \
    .github/workflows/release.* 2>/dev/null | head -1 | grep -q . && { echo ci-release; return; }
  echo NONE
}
```

`NONE` → ask user for bump level, tag manually.
