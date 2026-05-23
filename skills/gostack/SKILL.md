---
name: gostack
description: "My curated Go stack reference — opinionated guide to Sam Berthe's libraries (lo Lodash helpers, oops structured errors, do v2 DI, mo monads, slog logging ecosystem, hot in-memory cache pre-1.0, ro reactive streams pre-1.0). Use when writing or reviewing Go code that imports github.com/samber/*, when deciding between these libraries and the stdlib, when adopting or upgrading any of them, or when scaffolding a new Go service and considering this ecosystem."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
  upstream-author: "Sam Berthe (samber)"
  upstreams:
    lo: "https://github.com/samber/lo @ v1.53.0 (2026-03-02) — stable, MIT, 21.2k stars"
    oops: "https://github.com/samber/oops @ v1.21.0 (2026-01-18) — stable, MIT"
    do: "https://github.com/samber/do @ v2.0.0 (2025-09-21) — v2 only, MIT"
    mo: "https://github.com/samber/mo @ v1.16.0 (2025-09-25) — stable, MIT"
    slog-multi: "https://github.com/samber/slog-multi @ v1.8.0 (2026-03-25)"
    slog-sampling: "https://github.com/samber/slog-sampling @ v1.6.0 (2026-03-25)"
    slog-formatter: "https://github.com/samber/slog-formatter @ v1.3.0 (2026-03-25)"
    slog-echo: "https://github.com/samber/slog-echo @ v2.0.0 (2026-05-04) — v2 breaking change from v1"
    slog-loki: "https://github.com/samber/slog-loki @ v3.7.2 (2026-03-25) — on v3"
    hot: "https://github.com/samber/hot @ v0.13.0 (2026-03-11) — PRE-1.0, API can break"
    ro: "https://github.com/samber/ro @ v0.3.0 (2026-03-02) — PRE-1.0, young, API churning, Apache-2.0"
  versions-verified: "2026-05-23"
  acknowledgments: "Libraries by Sam Berthe (samber). API patterns and reference material distilled from samber/cc-skills-golang."
---

# gostack

My curated Go library stack — opinionated take on Sam Berthe's `github.com/samber/*` ecosystem. Generics-first, zero-dep, prolifically maintained. This skill is the decision matrix on top of his work: when to reach for each library, when to deliberately not, and which versions are battle-tested **today**.

Not a fork of upstream documentation. The libraries are Sam Berthe's; the opinions are mine, with verified-current versions pinned at the top of each reference.

## When to load which reference

The model: SKILL.md is the dispatcher. Open exactly one reference file based on the task at hand.

| If the task involves... | Open | Library |
|---|---|---|
| Collection transforms (Map, Filter, Reduce, GroupBy, Chunk, Flatten, Uniq, Zip…) | [references/lo.md](references/lo.md) | `samber/lo` |
| Errors that need context, attributes, stack traces, public messages, or APM grouping | [references/oops.md](references/oops.md) | `samber/oops` |
| Dependency injection container — services, scopes, lifecycle, graceful shutdown | [references/do.md](references/do.md) | `samber/do` (v2) |
| Optional/Result/Either monads, FP composition, nullable JSON fields | [references/mo.md](references/mo.md) | `samber/mo` |
| Structured logging — handler composition, sampling, PII formatting, HTTP middleware, cloud sinks | [references/slog.md](references/slog.md) | `samber/slog-*` ecosystem |
| In-memory cache with LRU/LFU/W-TinyLFU/S3FIFO, TTL, loaders, singleflight | [references/hot.md](references/hot.md) | `samber/hot` (pre-1.0) |
| Reactive streams, infinite event pipelines, multi-source async combine | [references/ro.md](references/ro.md) | `samber/ro` (pre-1.0) |

## My one-line take on each

| Library | Reach for it when… | Skip it when… |
|---|---|---|
| **lo** | Stdlib `slices`/`maps` doesn't cover the transform (Map/Filter/Reduce/GroupBy/Chunk/Flatten) | The stdlib **does** cover it. Don't pull `lo.Contains` if `slices.Contains` exists. |
| **oops** | Errors cross architectural boundaries (handler ↔ service ↔ repo) and need to land cleanly in APM | Inside leaf functions where plain `fmt.Errorf("…: %w", err)` is enough |
| **do** v2 | Service graph >~20 nodes, lifecycle management matters, want runtime container | Small services where manual constructor wiring fits on one screen. **Never use v1.** |
| **mo** | JSON nullable fields (`Option[T]`), FP-leaning team | Production code paths where `if err != nil` reads better to Go reviewers |
| **slog-multi / sampling / formatter** | Logging pipeline needs routing, sampling, or PII scrubbing before sinks | Single-handler stdout/JSON setup. Don't pipe what you don't route. |
| **hot** | Read-through cache with loader + singleflight on warm read paths | Anything OK with `patrickmn/go-cache` or where stdlib `sync.Map` + TTL goroutine suffices. **Pre-1.0 — pin the version.** |
| **ro** | Multi-source async pipeline that would be a 200-line `select` mess | Almost everything else in Go. **Pre-1.0, niche, default away from it.** Try `errgroup` + channels first. |

## Hard rules I enforce

1. **Verify version before adopting.** GitHub release pages move — confirm the tag in `metadata.upstreams` is still current before pinning in `go.mod`. The `versions-verified` date is when I last looked.
2. **Pre-1.0 libraries (`hot`, `ro`) require version pinning.** No `^0.x` ranges. Pin exact in `go.mod` and gate updates through a code review.
3. **Don't use `samber/do` v1.** It's unmaintained. v2 is incompatible — full migration only.
4. **`lo.Must`, `mo.MustGet`, `do.MustInvoke` are panic-on-error.** Allowed in tests, init, and inside `mo.Do` blocks. **Not allowed in production request paths.**
5. **`oops` error messages must be low-cardinality.** Variable data goes in `.With("key", value)`, not interpolated into the message string. APM grouping breaks otherwise.
6. **Sampling-first ordering for slog.** Place sampling outermost — formatting records that get sampled out wastes CPU.
7. **`samber/lo` is not a replacement for stdlib.** Prefer `slices.Contains`, `slices.Sort`, `maps.Keys`, `maps.Values` when the stdlib covers it. `lo` earns its keep on the things the stdlib doesn't.

## How adoption cascades (my mental model)

If a Go service is going to adopt this ecosystem, the order I'd introduce libraries:

1. **`oops` first** — biggest leverage. Every service has errors; structured errors transform on-call triage.
2. **`slog-multi` + `slog-sampling`** — once errors are structured, route them properly.
3. **`lo`** — once code is being written/reviewed, the Map/Filter/Reduce idioms compound.
4. **`do` v2** — when the constructor wiring in `main.go` exceeds one screen.
5. **`mo`** — only if the team has FP literacy; otherwise it's friction.
6. **`hot`** — only when a specific read-through cache pattern shows up; not as a general "always cache" tool.
7. **`ro`** — last resort. If a problem demands it, you'll know.

## Where this skill plugs into the rest

- `vd:py2go` (Python→Go migration) — defaults to `slog` over zap/zerolog, mentions `samber/oops` for error context, `samber/do` for DI when the graph grows. See py2go's translation rules table for the cross-reference.
- `vd:cook` / `vd:ship` — the lint and review steps benefit from understanding why a PR pulls in `samber/lo` over stdlib (`lo.Contains` vs `slices.Contains` is a code-review smell I want to catch).
- `vd:debug` / `vd:fix` — `samber/oops` error chains preserve the context that makes debugging much faster; this skill is the place to confirm best practices.

## Versions snapshot (verified 2026-05-23)

| Library | Pinned | Released | Maintenance |
|---|---|---|---|
| samber/lo | v1.53.0 | 2026-03-02 | Active (21.2k stars) |
| samber/oops | v1.21.0 | 2026-01-18 | Active |
| samber/do | v2.0.0 | 2025-09-21 | **v2 only — v1 dead** |
| samber/mo | v1.16.0 | 2025-09-25 | Active |
| samber/slog-multi | v1.8.0 | 2026-03-25 | Active |
| samber/slog-sampling | v1.6.0 | 2026-03-25 | Active |
| samber/slog-formatter | v1.3.0 | 2026-03-25 | Active |
| samber/slog-echo | **v2.0.0** | 2026-05-04 | **v2 breaking change** |
| samber/slog-loki | v3.7.2 | 2026-03-25 | On v3 |
| samber/slog-gin / chi / fiber | v1.x | Apr-May 2026 | Active |
| samber/slog-datadog / sentry | v2.x | Mar 2026 | Active |
| samber/hot | **v0.13.0** | 2026-03-11 | **PRE-1.0 — pin exact** |
| samber/ro | **v0.3.0** | 2026-03-02 | **PRE-1.0, young** |

If a version drifts ahead by a major release, re-verify before recommending — especially for the pre-1.0 libraries.

## Adding a new library

Future extension flow:
1. Verify the new `samber/*` repo (active, license, last release) via `gh api repos/samber/<name>`.
2. Add a row to `metadata.upstreams` in this SKILL.md with the pinned version and date.
3. Drop a new `references/<lib>.md` following the structure of `lo.md` (identity → my take → version + install → core patterns → mistakes → when to skip).
4. Add a row to "When to load which reference" and "My one-line take on each" tables above.
