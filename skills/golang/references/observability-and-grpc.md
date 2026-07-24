# Observability & gRPC

## Observability

Five complementary signals; a feature isn't done until it's observable.

| Signal | Answers | Tool |
| --- | --- | --- |
| Logs | What happened? | `log/slog` |
| Metrics | How much / how fast? | Prometheus client |
| Traces | Where did time go? | OpenTelemetry |
| Profiles | Why slow / leaking? | pprof, Pyroscope |
| RUM | How do users experience it? | PostHog, Segment (server-side) |

**Structured logging (`log/slog`):**
- Production services emit **structured JSON**, not freeform strings. Migrate `zap`/`logrus`/`zerolog` → `slog` (stdlib since 1.21, stable, no extra dependency).
- Right level: Debug (dev), Info (normal), Warn (degraded), Error (needs attention).
- Log with context (`slog.InfoContext(ctx, ...)`) to correlate with traces. The `otelslog` bridge injects `trace_id`/`span_id` automatically.
- **Log OR return an error, never both.** No PII in logs.

**Metrics (Prometheus):**
- **Histogram, not Summary, for latency** - Histograms aggregate server-side and support `histogram_quantile()` (P50/P90/P99). Every HTTP endpoint gets latency + error-rate metrics.
- **Keep label cardinality low** - never use unbounded values (user IDs, full URLs, raw paths) as label values; use the route *pattern*. High cardinality destroys Prometheus.
- Counter for rates, Gauge for snapshots, Histogram for distributions. Write the PromQL query and alert rule as comments above each metric declaration.

**Tracing (OpenTelemetry):** configure the `TracerProvider` early, then add spans to every meaningful operation (service methods, DB queries, external calls, queue ops). Record errors with `span.RecordError()`. Propagate context across service boundaries - it carries `trace_id`/`span_id`/deadlines. Sample (you can't collect everything at scale).

**Profiling:** enable pprof via an env-var toggle (no redeploy), secure it with auth, isolate the network. Pyroscope for always-on continuous profiling. For deep measurement methodology see concurrency-and-performance.md.

**Definition of done:** metrics declared (with PromQL + alert-rule comments), structured logging with context variants and no PII, spans on every I/O boundary, dashboards + alerts wired (start from [awesome-prometheus-alerts](https://samber.github.io/awesome-prometheus-alerts/) - the four golden signals: latency, traffic, errors, saturation), and key business events tracked server-side with consent checks. Alerting mistakes: `irate` instead of `rate`, missing `for:` (causes flapping).

For the `slog-*` ecosystem (multi, sampling, formatter, HTTP middleware, cloud sinks) and `samber/oops` structured errors, see **gostack**.

## gRPC

Treat gRPC as a pure transport layer, separate from business logic. Official impl: `google.golang.org/grpc`.

**Proto organization:** by domain with versioned dirs (`proto/user/v1/`). Always use `Request`/`Response` **wrapper messages** - bare types like `string` can't gain fields later. Generate with `buf` or `protoc` (`protoc-gen-go`, `protoc-gen-go-grpc`).

**Server:**
- Implement the health service (`grpc_health_v1`) - Kubernetes probes need it or pods get killed during deploys.
- Interceptors (`ChainUnaryInterceptor`) for cross-cutting concerns (logging, auth, recovery) - keeps handlers clean.
- `GracefulStop()` with a timeout fallback to `Stop()` (drains in-flight RPCs without hanging).
- **Disable reflection in production** - it exposes the full API surface.
- TLS in production always; mTLS or a service mesh for service-to-service; `credentials.PerRPCCredentials` + an auth interceptor for user auth.

**Client:** reuse connections (HTTP/2 multiplexes - one-per-request wastes handshakes); set a deadline on **every** call (`context.WithTimeout`); `round_robin` over headless services via `dns:///`; pass metadata via `metadata.NewOutgoingContext`.

**Errors - return `status.Error` with a specific code**, never a raw `error` (becomes `codes.Unknown`, telling the client nothing). The code drives client retry/fail-fast decisions:

| Code | When |
| --- | --- |
| `InvalidArgument` | malformed input |
| `NotFound` / `AlreadyExists` | entity missing / conflict |
| `Unauthenticated` / `PermissionDenied` | bad token / lacks permission |
| `FailedPrecondition` | wrong system state |
| `ResourceExhausted` | rate/quota exceeded |
| `Unavailable` | transient - safe to retry |
| `DeadlineExceeded` | timeout |
| `Internal` | unexpected bug |

```go
if errors.Is(err, ErrNotFound) {
    return nil, status.Errorf(codes.NotFound, "user %q not found", req.UserId)
}
return nil, status.Errorf(codes.Internal, "lookup failed: %v", err)
```

Attach field-level validation via `errdetails.BadRequest` + `status.WithDetails`. **Stream** over large single messages (avoids size limits, lowers memory). Test with `bufconn` (in-memory, full stack, no network) and assert the expected status codes. Tune `keepalive` and `MaxRecvMsgSize` only when needed - most services don't need connection pooling; profile first.
