# Python → Go Translation Rules

**Locked rules.** Stack defaults are survey-anchored (Go Developer Survey 2025) and verified-current as of 2026-05-23. Library cross-refs point into the [gostack](../../gostack/SKILL.md) skill for opinions on `samber/*` libraries - `gostack` is the place to look for **when** to reach for each and what the sharp edges are.

## How to read this file

Each row is a Python construct on the left and the canonical Go translation on the right. The "Cross-ref" column points to the gostack reference when one of Sam Berthe's libraries is the right answer; "stdlib" means use Go's standard library directly. **Library names in code are the actual Go import paths** - not skill names.

## Language constructs

| Python | Go | Cross-ref |
|---|---|---|
| `class Foo(Base):` (inheritance) | `type Foo struct{}` + interface, embed `*Base` only when truly is-a | stdlib |
| `class Foo:` (data + methods) | `type Foo struct{}` + free functions; or interface + concrete impl | stdlib |
| `@dataclass` | `type Foo struct{}` + `func NewFoo(...) (*Foo, error)` | stdlib |
| `@dataclass` with defaults | constructor + functional options pattern | stdlib |
| `Enum` | `type X int; const ( A X = iota; ... )` + `String()` + Marshal/Unmarshal if serialized | stdlib |
| `Optional[T]` (nullable field) | `mo.Option[T]` for JSON nullable; `*T` for nullable pointer; `(T, bool)` for lookup; `(T, error)` for failure | [gostack/mo](../../gostack/references/mo.md) - Option only |
| `Optional[T]` (return value) | `(T, error)` for failure; `(T, bool)` for lookup; don't reach for `mo.Option[T]` blindly | [gostack/mo](../../gostack/references/mo.md) |
| `Union[A, B]` | interface + type switch; or `mo.Either[A, B]` if both sides are valid alternatives | [gostack/mo](../../gostack/references/mo.md) - rarely needed |
| `dict[str, Any]` (at boundary) | `map[string]any` at IO boundary; decode into concrete struct ASAP | stdlib |
| list comprehension `[f(x) for x in xs]` | for-loop with append OR `lo.Map` (only if 2+ chained transforms) | [gostack/lo](../../gostack/references/lo.md) |
| list comprehension w/ filter | `lo.FilterMap` or `lo.Filter` + `lo.Map` | [gostack/lo](../../gostack/references/lo.md) |
| `sum(xs)` | `for _, v := range xs { sum += v }` or `lo.Sum` | stdlib preferred |
| `sorted(xs)` | `slices.Sort(xs)` (Go 1.21+) | stdlib |
| `xs.sort(key=fn)` | `slices.SortFunc(xs, less)` | stdlib |
| `x in xs` | `slices.Contains(xs, x)` (Go 1.21+) | stdlib - **do not** use `lo.Contains` |
| `set(xs)` | `lo.Uniq(xs)` for slice-dedup; `map[T]struct{}` for set semantics | [gostack/lo](../../gostack/references/lo.md) |
| `groupby(xs, key=fn)` | `lo.GroupBy(xs, fn)` | [gostack/lo](../../gostack/references/lo.md) |
| `zip(a, b)` | `lo.Zip2(a, b)` | [gostack/lo](../../gostack/references/lo.md) |
| `chunk(xs, n)` | `lo.Chunk(xs, n)` | [gostack/lo](../../gostack/references/lo.md) |

## Concurrency

| Python | Go | Cross-ref |
|---|---|---|
| `async def f()` | `func f()` returning `(T, error)` | stdlib |
| `await f()` | direct call; concurrency via goroutine + channel | stdlib |
| `asyncio.gather(*tasks)` | `errgroup.Group` + `g.Go(...)` + `g.Wait()` | stdlib (`golang.org/x/sync/errgroup`) |
| `asyncio.gather` with bounded concurrency | `errgroup` + `golang.org/x/sync/semaphore.Weighted` | stdlib |
| `asyncio.Queue` | `chan T` (buffered); writer closes | stdlib |
| `asyncio.Lock` / `Semaphore` | `sync.Mutex` / `golang.org/x/sync/semaphore` | stdlib |
| `asyncio.Event` | `chan struct{}` close-to-signal pattern | stdlib |
| `concurrent.futures.ThreadPoolExecutor` | goroutine pool - bare goroutines + errgroup, or `panjf2000/ants/v2` | stdlib first |
| Reactive event stream (rare) | `samber/ro` - but **default away from it**; channels + errgroup usually suffice | [gostack/ro](../../gostack/references/ro.md) |

## Errors

| Python | Go | Cross-ref |
|---|---|---|
| `raise ValueError(msg)` | `return fmt.Errorf("%w: ...", err)` (leaf) or `oops.In("domain").Errorf("...")` (boundary) | [gostack/oops](../../gostack/references/oops.md) |
| `try / except ValueError` | `if err != nil { ... }` - check immediately | stdlib |
| `try / except / finally` | `defer cleanup()` + `if err != nil` | stdlib |
| `raise X from Y` | `oops.Wrapf(y, "...")` or `fmt.Errorf("...: %w", y)` | [gostack/oops](../../gostack/references/oops.md) |
| Custom exception class | sentinel error `var ErrX = errors.New("...")` + `errors.Is`; or typed struct + `errors.As` | stdlib |
| `logger.error("..." + str(user_id))` | `slog.Error("op failed", "user_id", id)` (low cardinality) | [gostack/oops](../../gostack/references/oops.md) - `.With()` keeps message low-cardinality |
| panic recovery in thread | `oops.Recover(func() { ... })` at goroutine entry | [gostack/oops](../../gostack/references/oops.md) |
| `assert x, msg` | `if !x { return oops.Errorf("...") }` - never use Go `assert`-style libs in prod | stdlib |

## Logging

| Python | Go | Cross-ref |
|---|---|---|
| `logging.getLogger(__name__)` | `slog.Default()` or module-scoped logger | stdlib |
| `logger.info("...")` | `slog.Info("...")` | stdlib |
| `logger.info("...", extra={"k": v})` | `slog.Info("...", "k", v)` - attributes flatten | stdlib |
| `loguru.logger.bind(user=u)` | `logger.With("user", u)` | stdlib |
| Multi-handler routing (errors → Sentry, info → stdout) | `slog-multi` Router + `slog-sentry` + JSON handler | [gostack/slog](../../gostack/references/slog.md) |
| Log sampling under load | `slog-sampling` Threshold strategy, sampling-first ordering | [gostack/slog](../../gostack/references/slog.md) |
| PII scrubbing | `slog-formatter` PIIFormatter in Pipe middleware | [gostack/slog](../../gostack/references/slog.md) |
| Datadog / Loki / Sentry sinks | `slog-datadog/v2`, `slog-loki/v3`, `slog-sentry/v2` - **defer .Stop(ctx)** | [gostack/slog](../../gostack/references/slog.md) |
| HTTP request logging middleware | `slog-gin` (default) / `slog-chi` / `slog-echo` v2 / `slog-fiber` | [gostack/slog](../../gostack/references/slog.md) |

## HTTP server

| Python | Go | Notes |
|---|---|---|
| `FastAPI()` | `gin.Default()` (default; user preference + Survey 2025 plurality) | Alternates: chi, Echo, Fiber, stdlib net/http |
| `@app.get("/path")` | `r.GET("/path", handler)` | Gin idiom |
| Pydantic `BaseModel` body | struct + tags + `go-playground/validator` (Gin built-in binding) | - |
| Dependency Injection (Depends) | constructor injection at composition root; `samber/do` v2 once graph >20 services | [gostack/do](../../gostack/references/do.md) |
| Middleware | `r.Use(...)` | Gin idiom |
| CORS | `gin-contrib/cors` | - |
| Sessions | `gin-contrib/sessions` | - |
| Static files | `r.Static("/static", "./assets")` | Gin built-in |
| File upload | `c.SaveUploadedFile(...)` | Gin built-in |
| WebSocket | `coder/websocket` (modern) or `gorilla/websocket` (legacy) | - |
| Rate limit | `ulule/limiter/drivers/middleware/gin` | - |
| Health check | custom handler or `tavsec/gin-healthcheck` | - |
| OpenAPI codegen | `oapi-codegen/oapi-codegen/v2` (Gin generator) | - |

## Backend frameworks (Django/Flask)

| Python | Go | Notes |
|---|---|---|
| `Django` (full stack) | **chi/Gin + sqlc + oapi-codegen** - reject "Go Django" framing | Django ORM/admin/templates have no Go peer; redesign |
| `Django ORM` | sqlc (preferred) or Ent for large schemas | - |
| `Django REST Framework` serializers | struct + tags + validator + JSON codec | - |
| `Django admin` | no Go equivalent - strip or rebuild as a separate Go admin or accept this as missing | - |
| `Flask` route | `r.GET(...)` (Gin) | - |
| `Flask-SQLAlchemy` | sqlc or sqlx | - |
| `Jinja2` template | `html/template` (stdlib) or `a-h/templ` for type-safe components | - |

## Database access

| Python | Go | Cross-ref |
|---|---|---|
| `psycopg2` / `psycopg3` / `asyncpg` | **`github.com/jackc/pgx/v5`** | - |
| `sqlite3` | `modernc.org/sqlite` (no cgo) or `mattn/go-sqlite3` (cgo OK) | - |
| `mysql-connector` / `aiomysql` | `github.com/go-sql-driver/mysql` | - |
| `pymongo` | `go.mongodb.org/mongo-driver/v2` | - |
| `clickhouse-driver` | `github.com/ClickHouse/clickhouse-go/v2` | - |
| `SQLAlchemy` ORM | **`sqlc`** (default) - Ent for large schemas, Bun for fluent SQL, sqlx for raw + helpers, GORM only on explicit flag | - |
| `Alembic` migrations | **`golang-migrate/migrate`** (default) or Atlas (declarative) | - |
| Connection pool | `pgxpool.New(...)` | - |

## Configuration

| Python | Go | Cross-ref |
|---|---|---|
| `pydantic.BaseSettings` / `dynaconf` | **`viper`** (default) - env > file > defaults; or koanf for cleaner abstractions | - |
| `os.getenv` | `viper.GetString(...)` or `os.Getenv` for simple cases | - |
| `python-dotenv` | `joho/godotenv` + viper | - |
| Struct binding | `viper.Unmarshal(&cfg)` with mapstructure tags | - |

## Validation

| Python | Go | Notes |
|---|---|---|
| Pydantic field validators | `go-playground/validator` struct tags | Built-in with Gin |
| `pydantic.validator` decorator | custom validation function registered with validator | - |
| Complex conditional rules | `go-ozzo/ozzo-validation` | When tag-based gets clunky |

## Auth & crypto

| Python | Go | Notes |
|---|---|---|
| `pyjwt` | `github.com/golang-jwt/jwt/v5` | Default JWT |
| JWT alternative | `aidanwoods.dev/go-paseto` | When you control both sides |
| `bcrypt` / `passlib` | `golang.org/x/crypto/bcrypt` | Compat-friendly |
| `argon2` (recommended) | `golang.org/x/crypto/argon2` - Argon2id, OWASP 2024 params m=64MB t=3 p=2 | Default for new projects |
| OAuth2 client | `golang.org/x/oauth2` | - |
| Sessions | `gorilla/sessions` or `alexedwards/scs` | - |
| TOTP | `pquerna/otp` | - |
| WebAuthn / passkeys | `go-webauthn/webauthn` | - |
| RBAC | `casbin/casbin` | - |
| CSRF | `gorilla/csrf` | - |

## Background jobs & scheduling

| Python | Go | Notes |
|---|---|---|
| Celery task | **`hibiken/asynq`** (Redis-backed, Celery-shaped) | Default |
| Celery alternative (Postgres) | `riverqueue/river` | When no Redis |
| Celery + Kafka | `ThreeDotsLabs/watermill` | Event-driven |
| `APScheduler` cron | `robfig/cron/v3` (cron-expression compatible) | - |
| `schedule` lib | `go-co-op/gocron` | - |
| Durable workflows | `temporalio/sdk-go` | When stakes are high |
| Worker pool | `panjf2000/ants/v2` or errgroup + semaphore | stdlib first |
| Retry/backoff | `cenkalti/backoff/v4` or `avast/retry-go/v4` | - |
| Distributed lock | `bsm/redislock` (Redis) or PG advisory locks | - |

## HTTP client

| Python | Go | Notes |
|---|---|---|
| `requests` | `net/http.Client` + always set timeout | stdlib |
| `requests.Session` | `*http.Client` + RoundTripper middleware | stdlib |
| `httpx` (async) | `net/http` + goroutines (errgroup for fan-out) | stdlib |
| Retry + backoff | `hashicorp/go-retryablehttp` | drop-in net/http |
| Circuit breaker | `sony/gobreaker` standalone | compose with any client |
| Full resilience stack | `go-resty/resty` or `gojek/heimdall` | - |
| Webhook signing | stdlib `crypto/hmac` + `crypto/sha256` | - |

## Caching

| Python | Go | Cross-ref |
|---|---|---|
| `functools.lru_cache` | `dgraph-io/ristretto` (in-mem) or `samber/hot` (loader+singleflight) | [gostack/hot](../../gostack/references/hot.md) |
| `redis-py` / `aioredis` | `redis/go-redis/v9` (default) | - |
| Redis (perf-critical) | `redis/rueidis` - **caveat: p99 spikes in some prod environments** | - |
| Memcached | `bradfitz/gomemcache` | - |
| Read-through cache w/ batch loader | `samber/hot` `WithLoaders(...)` - singleflight built-in | [gostack/hot](../../gostack/references/hot.md) |

## Dependency injection

| Python | Go | Cross-ref |
|---|---|---|
| FastAPI `Depends` | constructor injection at composition root (default) | - |
| `dependency-injector` lib | manual wiring until graph >20 services; then `samber/do` v2 | [gostack/do](../../gostack/references/do.md) |
| DI w/ compile-time correctness | `google/wire` | - |
| DI + lifecycle hooks | `uber-go/fx` | - |

## Data pipelines (most fragile category)

| Python | Go | Notes |
|---|---|---|
| `pandas.DataFrame` | streaming `[]Struct{}` + channels - **redesign the pipeline shape**; do not look for a pandas peer | qframe is the closest, gota is cumbersome |
| `numpy.ndarray` load-bearing | **STOP - wrap Python via gRPC.** Do not translate. | - |
| Basic linalg | `gonum.org/v1/gonum` | - |
| CSV | `encoding/csv` (stdlib) + `gocarina/gocsv` for struct binding | - |
| Parquet | `parquet-go/parquet-go` or `segmentio/parquet-go` | - |
| Excel | `xuri/excelize/v2` | - |
| Kafka | `segmentio/kafka-go` or `twmb/franz-go` (perf) | - |
| NATS | `nats-io/nats.go` | - |
| S3 | `aws-sdk-go-v2/service/s3` | - |
| DuckDB (embedded analytics) | `marcboeker/go-duckdb` | When Pandas was used locally |
| Airflow task | DAG redesign; goroutine pipeline or temporalio | Airflow has no Go peer |

## CLI

| Python | Go | Cross-ref |
|---|---|---|
| `Click` / `Typer` | **`spf13/cobra`** + `spf13/viper` | - |
| `rich.console` styling | `charmbracelet/lipgloss` | - |
| `rich.table` | `jedib0t/go-pretty/v6` | - |
| `rich.markdown` | `charmbracelet/glamour` | - |
| `tqdm` progress bar | `schollz/progressbar/v3` | - |
| `prompt_toolkit.prompt` | `charmbracelet/huh` (modern forms) or `AlecAivazis/survey/v2` | - |
| spinner | `briandowns/spinner` | - |
| color output | `fatih/color` or `charmbracelet/lipgloss` | - |

## TUI

| Python | Go | Cross-ref |
|---|---|---|
| `Textual` | **`charmbracelet/bubbletea`** (Elm architecture - refactor, not 1:1 port) | - |
| `Textual` widgets | `charmbracelet/bubbles` (list, table, viewport, paginator, spinner, progress, textinput, filepicker) | - |
| styling | `charmbracelet/lipgloss` | - |
| forms | `charmbracelet/huh` | - |
| markdown rendering | `charmbracelet/glamour` | - |
| SSH-served TUI | `charmbracelet/wish` | - |

## Encoding / serialization

| Python | Go | Notes |
|---|---|---|
| `json` | `encoding/json` (stdlib) | - |
| JSON perf-critical | `goccy/go-json` or `bytedance/sonic` | After benchmarking |
| `yaml` | `gopkg.in/yaml.v3` | - |
| `toml` | `pelletier/go-toml/v2` | - |
| `protobuf` | `google.golang.org/protobuf` + buf tooling | - |
| `msgpack` | `vmihailenco/msgpack/v5` | - |

## Testing

| Python | Go | Notes |
|---|---|---|
| `pytest` | stdlib `testing` + table-driven + `stretchr/testify/require` | `require` halts; `assert` continues - use `require` 99% of the time |
| `@pytest.mark.parametrize` | table-driven test with `for _, tc := range tests` | stdlib |
| `unittest.mock` | **`go.uber.org/mock`** (Google archived `golang/mock`; Uber owns it) | - |
| Mock generation | `vektra/mockery` or `mockgen` (from uber-go/mock) | - |
| `httpx.MockTransport` | stdlib `net/http/httptest` + `*httptest.Server` | - |
| `pytest-asyncio` | testable goroutines + channels; `testcontainers-go` for real DBs | - |
| Property-based | stdlib `testing.F` (fuzzing, Go 1.18+) or `leanovate/gopter` | - |
| Benchmark | `func BenchmarkX(b *testing.B)` + `benchstat` | stdlib |

## Observability

| Python | Go | Notes |
|---|---|---|
| `opentelemetry-python` | `go.opentelemetry.io/otel` + framework middleware (otelgin, etc.) | - |
| `prometheus_client` | `prometheus/client_golang/prometheus/promhttp` | - |
| `Sentry` | `getsentry/sentry-go` + `samber/slog-sentry/v2` integration | [gostack/slog](../../gostack/references/slog.md) |
| profiling | stdlib `net/http/pprof` | Continuous: Parca / Pyroscope |

## File / time / misc

| Python | Go | Notes |
|---|---|---|
| `pathlib.Path` | stdlib `path/filepath` + `os` | - |
| `datetime` | stdlib `time` - **reject `carbon` clones** | - |
| `uuid` | `google/uuid` | - |
| `watchdog` file watch | `fsnotify/fsnotify` | - |
| `smtplib` / `aiosmtplib` | `wneessen/go-mail` (modern) or `jordan-wright/email` | - |
| `subprocess.run` | stdlib `os/exec` | - |

## Container / build / release

| Python | Go | Notes |
|---|---|---|
| `Dockerfile` (multi-stage) | `goreleaser/goreleaser` for binaries + `ko-build/ko` for containers (no Dockerfile) | - |
| Container base | `gcr.io/distroless/static-debian12` | minimal, secure |
| Lockfile (`poetry.lock`) | `go.mod` + `go.sum` (stdlib) | - |
| Linting | `golangci-lint` v1.62+ | de facto standard |
| Formatting | `gofumpt` + `goimports` | stricter than gofmt |

## Forbidden defaults

Skill refuses these silently - must be explicit override:

- ❌ `lib/pq` - pgx is default
- ❌ `golang/mock` - `go.uber.org/mock` is default
- ❌ GORM as default - sqlc is default
- ❌ Bare `net/http.Get` with no timeout
- ❌ `panic` for business errors
- ❌ AST transpilers (Grumpy, py2go-from-jianyuan) - non-idiomatic, dead toolchains
- ❌ `samber/lo` for stdlib-covered ops (`Contains`, `Sort`, `Keys`) - see [gostack/lo](../../gostack/references/lo.md)
- ❌ `samber/do` v1 - v2 only (v1 is dead)
- ❌ `samber/hot` / `samber/ro` with `^0.x` ranges - pin exact, pre-1.0
