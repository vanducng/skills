# Contributing to vd

## Dev setup

Requires Go 1.23+ and `make`.

```sh
git clone https://github.com/vanducng/skills.git
cd skills/tools/vd

make build    # compile → ./vd
make test     # go test ./...
make vet      # go vet ./...
make lint     # golangci-lint run (requires golangci-lint in PATH)
```

Install golangci-lint (if missing):
```sh
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
```

Install goimports (required by the lint formatter):
```sh
go install golang.org/x/tools/cmd/goimports@latest
```

Run a single command without building first:
```sh
make run ARGS="init --force"   # go run ./cmd/vd init --force
```

## Running tests

```sh
make test                                         # all packages
go test ./internal/cli/... -v -run TestAdd        # single test
go test ./... -race -cover                        # with race detector + coverage
```

Integration tests that touch the network or filesystem are in `internal/cli/*_test.go` and `internal/source/*_test.go`. They use temporary Git fixtures and do not require a real upstream connection in the fast path (the fetcher uses a local bare-clone fixture).

The snapshot test in `internal/target/claude_bundle_test.go` is a critical gate: it asserts that the bundle emitter produces byte-equal output to `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`. If that test fails after your change, update the snapshots in `internal/target/testdata/bundle-snapshot/` to reflect the intended new output.

## Conventional commits

Use the `vd:` scope for changes to this CLI:

```
feat(vd): add --dry-run flag to vd sync
fix(vd): handle empty skills.lock on first sync
docs(vd): update config-schema.md with version_strategy field
test(vd): add snapshot test for per-skill emitter
chore(vd): bump golangci-lint to v1.62
refactor(vd): extract executor into separate package
```

For changes to the repo's skills (not the CLI), omit the `vd:` scope:
```
feat: add skills/browser-trace from browserbase
```

Do not reference AI tools in commit messages.

## File ownership rules

- CLI source lives entirely in `tools/vd/`. Do not modify files outside this tree unless explicitly coordinated.
- Test files in `internal/*/` are owned by the same team as the package they test.
- Snapshot data in `internal/target/testdata/` is generated — update it by running the test with `-update` flag (see test file header).

## Release flow

Releases are coordinated by [release-please](https://github.com/googleapis/release-please) (version PR) and shipped by GoReleaser (tag → binaries + Homebrew formula).

1. Merge conventional commits to `main` (`feat(vd): ...`, `fix(vd): ...`).
2. release-please opens a PR titled `chore(main): release vd X.Y.Z` that bumps `tools/vd/CHANGELOG.md` and `.release-please-manifest.json`.
3. Merge the release PR.
4. **Manually push the tag** (release-please cannot create the GitHub Release directly due to a v5 action limitation; we skip that step):
   ```sh
   git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. The tag push triggers `vd-release.yml` → GoReleaser → cross-platform binaries published to a new GitHub Release, plus the Homebrew formula updated in `vanducng/homebrew-tap`.

## CI

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `vd-test.yml` | Push / PR touching `tools/vd/**` | `go test ./... -race`, `golangci-lint run` |
| `vd-release.yml` | Tag push `v*` | GoReleaser cross-compile + GitHub Release |
| `vd-release-please.yml` | Push to `main` | release-please PR management |
| `validate.yml` | Push / PR touching `skills/**` | Frontmatter lint on SKILL.md files |

## Where to file issues

GitHub Issues on `vanducng/skills`. Tag CLI-specific issues with the `vd-cli` label.

Include:
- `vd --version` output.
- OS and Go version (`go version`).
- Minimal reproduction steps.
- Relevant section of `skills.toml` (redact personal URLs if needed).
