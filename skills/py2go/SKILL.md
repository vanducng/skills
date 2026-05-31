---
name: py2go
description: "Migrate Python projects to idiomatic Go end-to-end. Branches into 6 project-type playbooks (CLI, TUI, HTTP backend, data pipeline, async worker, library) with the right stack defaults (Gin, pgx, sqlc, slog, etc.) and pinned library versions. Default strategy: LLM module-by-module rewrite with golden-file parity tests; --strangler for live-traffic gradual cutover; --spec-first for OpenAPI/proto-driven regeneration. Use when porting a Python codebase to Go, when scaffolding a Go rewrite of a Python service, or when generating CLAUDE.md/MIGRATION.md for an AI-driven migration."
license: MIT
argument-hint: "<python-project-path> [--type cli|tui|http|pipeline|worker|lib|auto] [--strangler] [--spec-first FILE] [--strict-tdd] [--resume] [--dry-run]"
metadata:
  author: vanducng
  version: "0.1.0"
  inspired-by: "https://winder.ai/python-to-go-migration-with-claude-code/"
  acknowledgments: "Methodology extends the Winder.ai case study; stack defaults verified against the Go Developer Survey 2025."
---

# py2go

End-to-end Python → Go migration. Discover the source, lock the design, scaffold the Go module, translate file-by-file with TDD, validate behavioral parity against real data, cut over, then sweep dead code.

The skill is opinionated. It enforces idiomatic Go output over Python-shaped Go, rejects dead toolchains (Grumpy/py2go transpilers), defaults to `sqlc` over GORM, defaults to `pgx` over lib/pq, defaults to `Gin` for HTTP, prefers stdlib `slog` over zap/zerolog, and treats real-data parity validation as non-optional.

## When to load which reference

| Task | Open |
|---|---|
| Decide which Python pattern maps to which Go idiom | [references/translation-rules.md](references/translation-rules.md) |
| Pick the right Go stack per project type | (playbooks — extend as needed) |
| Configure strangler-fig gateway / traffic shadow | (extend as needed) |
| Drive from an existing OpenAPI/proto spec | (extend as needed) |

## The 7 phases

```
discover → design → scaffold → translate → validate → cutover → cleanup
```

1. **Discover** — two-pass: 7 discovery prompts individually → synthesize to `notes/`
2. **Design** — emit `CLAUDE.md` (translation rules) + `MIGRATION.md` (ordered file map + checkboxes)
3. **Scaffold** — `go mod init`, layout, lint (`golangci-lint`), CI, Makefile, smoke target
4. **Translate** — per-file loop: Python source → Go test first → Go impl → `go build && vet && test -race && lint` → commit
5. **Validate** — golden-file parity on real production data + integration tests + dead-code sweep
6. **Cutover** — hard cutover (default) or strangler-fig (`--strangler`)
7. **Cleanup** — orphan sweep, dependency audit, retro

## Project-type playbooks (auto-detected in discover)

| Type | Detected from | Go stack |
|---|---|---|
| CLI | Click/Typer imports, `entry_points` console_scripts | Cobra + Viper + lipgloss |
| TUI | Textual / Rich.live / prompt_toolkit | Bubble Tea + Bubbles + Lipgloss |
| HTTP | FastAPI/Flask/Django/Starlette | **Gin** (default) / chi / Echo / Fiber |
| Pipeline | pandas/polars/Airflow/Prefect/Dagster | streaming `[]T` + channels; qframe; **STOP if NumPy/SciPy heavy** |
| Worker | Celery/RQ/Dramatiq/Arq/Taskiq | asynq (Redis) or river (Postgres) |
| Library | `__init__.py` exports | `pkg/` layout with forced public-API decision |

## Hard guardrails (skill enforces)

1. **No 1:1 syntax port** — Go function signatures must not mirror Python verbatim across >50% of lines.
2. **TDD-or-bust under `--strict-tdd`** — Go test mtime must precede Go impl mtime per commit.
3. **No `lib/pq`** — use `pgx/v5`. lib/pq is in maintenance mode.
4. **No `golang/mock`** — use `go.uber.org/mock` (Google archived original).
5. **No GORM by default** — `sqlc` is default; GORM requires explicit `--orm=gorm` flag.
6. **No `panic` for business errors** — return errors.
7. **No blind `internal/`** — design phase must produce an explicit public-API decision.
8. **No synthetic-only validation** — validate phase refuses to mark complete without a real-data fixture path.
9. **NumPy/SciPy refusal** — if discovery detects them load-bearing, STOP with gRPC-wrap recommendation instead.

## Cross-refs into the rest of the skill ecosystem

- **[gostack](../gostack/SKILL.md)** — Sam Berthe's Go libraries (lo, oops, do, mo, slog, hot, ro). See `references/translation-rules.md` for where each library is the right answer.
- `vd:cook` — once a plan + MIGRATION.md is in place, drive execution phase-by-phase
- `vd:debug` — for the on-call story `oops`/`slog` enables in the migrated service
- `vd:ship` — for the final cutover commit + PR

## Versions snapshot (verified 2026-05-23)

Locked defaults — change requires explicit flag.

| Concern | Pinned default | Cite |
|---|---|---|
| HTTP framework | gin v1.x | Go Survey 2025: 48% adoption |
| Postgres driver | pgx/v5 | lib/pq in maintenance |
| DB access | sqlc | 2× faster than GORM on 15k-row reads |
| Migrations | golang-migrate | Multi-DB, CI-friendly |
| Config | viper | Cobra ecosystem alignment |
| Logger | log/slog (stdlib) | Survey 2025 default for new code |
| Validation | go-playground/validator | Default with Gin |
| Mocking | go.uber.org/mock | Google archived golang/mock |
| OpenAPI codegen | oapi-codegen | Supports Gin/chi/Fiber |
| Queue | asynq (Redis) or river (Postgres) | Celery-shaped or PG-native |
| Cache | ristretto or `gostack@hot` | See [gostack/hot](../gostack/references/hot.md) |
| Auth | golang-jwt/v5 + argon2 | OWASP 2025 recommendation |
| Observability | OpenTelemetry + Prometheus | Industry standard |
| Build/release | goreleaser + ko | Container without Dockerfile |

## Adding a new project-type playbook

1. Detect signal in discover phase (imports, file conventions)
2. Drop `references/playbook-<type>.md` with the canonical Go stack for that shape
3. Add a row to the "Project-type playbooks" table above
4. Update translation rules where the playbook diverges from defaults
