# Style, Naming, Types & Patterns

Clarity over cleverness. Linters handle formatting; this covers the judgment calls. When you break a rule here, leave a one-line comment saying why.

## Naming

All identifiers use **MixedCaps** / **mixedCaps** - never underscores (except test subcase names, generated code, cgo). Capitalization *is* the export mechanism, so this is load-bearing.

| Element | Convention | Example |
| --- | --- | --- |
| Package | lowercase, single word, singular | `json`, `user` (not `utils`, `helpers`, `users`) |
| Exported / unexported | UpperCamelCase / lowerCamelCase | `ReadAll`, `parseToken` |
| Interface | method + `-er` | `Reader`, `Closer`, `Stringer` |
| Constant | MixedCaps, **not** ALL_CAPS | `MaxRetries`, `defaultTimeout` |
| Receiver | 1-2 letter abbrev, consistent across methods | `func (s *Server)` - never `this`/`self` |
| Sentinel error | `Err` prefix | `ErrNotFound` |
| Error type | `Error` suffix | `PathError` |
| Constructor | `New` (single type) / `NewTypeName` (multi) | `user.New()`, `http.NewRequest` |
| Boolean field/method | `is`/`has`/`can` prefix | `isReady`, `IsConnected()` |
| Enum (iota) | type-name prefix, sentinel at 0 | `StatusUnknown` at 0, then `StatusReady` |
| Option func | `With` + field | `WithPort()`, `WithLogger()` |
| Variant funcs | `WithContext` / `In` (in-place) / `Must` (panics) / `f` (format) | `QueryContext`, `SortIn`, `MustParse`, `Errorf` |

**Frequently missed:**
- **No stuttering** - the package name is always at the call site: `http.Client` not `http.HTTPClient`, `user.New()` not `user.NewUser()`. Applies to *all* exported names in the package, not just the primary type.
- **Error strings are fully lowercase, including acronyms**, no trailing punctuation: `"invalid message id"`, not `"invalid message ID."`. Sentinel messages carry the package prefix: `errors.New("apiclient: not found")`.
- **Acronyms are all-caps or all-lower**: `URL`, `HTTPServer`, `xmlParser` - never `Url`/`Http`.
- **No `Get` prefix on getters** - `user.Name()`, not `user.GetName()`. Keep `Is`/`Has`/`Can` for boolean predicates.
- **Name length matches scope** - `i` in a 3-line loop; a descriptive name at package level. Import aliases only on collision (`mrand "math/rand"`).

## Formatting & control flow

- Break lines past ~120 chars at **semantic boundaries**. Calls with 4+ args go one per line. A too-long signature usually means too many params - use an options struct.
- `:=` for non-zero values, `var` for zero-value init (signals "starts at zero"). `var buf bytes.Buffer` is ready to use.
- **Slices/maps init explicitly, never nil** - nil map writes panic; nil slices serialize to `null` not `[]`. Preallocate (`make([]T, 0, n)`) only when the size is actually known.
- Composite literals use field names (`&http.Server{Addr: ...}`) - positional breaks on field reorder.
- Early-return errors; drop `else` after `return`. For mutually-exclusive assignment use default-then-`switch`, not an if/else-if chain. Extract 3+ boolean operands into named booleans.
- `switch` over repeated comparisons of one variable. `range` over index loops; `for range n` (1.22+) for counting.

## Function design

- Short, one job, **≤4 params** (else options struct). Parameter order: `ctx` first, then inputs, then output destinations.
- Name returns for docs/clarity in longer funcs; naked returns only in 1-3 line functions.
- Prefer generics over `any` when a concrete type will do: `func Contains[T comparable](s []T, target T) bool`.
- Philosophy: *a little copying beats a little dependency*; avoid `reflect`; minimize public surface (every exported name is a commitment); don't abstract until the pattern is stable.

## Structs & interfaces

- **Keep interfaces 1-3 methods**; compose larger ones (`io.ReadWriteCloser`). "The bigger the interface, the weaker the abstraction."
- **Define interfaces where consumed, not where implemented.** The consumer owns the contract; the implementor exports a concrete struct.
- **Accept interfaces, return structs.** Never return an interface from a constructor.
- **Discover interfaces, don't design them** - start concrete, extract when a 2nd implementation or a test mock demands it.
- **Make the zero value useful** (`var buf bytes.Buffer`, `var mu sync.Mutex`). Lazy-init nil map fields inside methods.
- Compile-time interface check near the type: `var _ io.ReadWriter = (*MyBuffer)(nil)` - free, fails the build if the type drifts.
- Honor canonical method names (`String()`, not `ToString()`).
- **Embedding** promotes the inner API (composition, not inheritance) - embed when the outer type "is a" enhanced inner; use a named field when it only "has a" dependency.
- **Field tags** on every exported field of a serialized struct: `json:"user_id" db:"user_id"`; `json:"-"` to exclude, `,omitempty` to drop zero values.
- **Receivers**: pointer when mutating / holds a `sync.Mutex` / large struct; value when small & immutable. Be consistent - if one method takes a pointer, all do. Embed a `noCopy` sentinel on structs that must not be copied (mutex/channel holders) so `go vet` catches copies.

## Design patterns

- **Functional options** are the default constructor pattern - one `With*` func per option, no breaking changes as the API grows. Options that can fail return an error.
- **Avoid `init()` and mutable globals** - implicit, can't return errors, breaks test isolation. Use explicit constructors that accept dependencies.
- **Enums**: sentinel `Unknown`/`Invalid` at iota 0 so an uninitialized `var s Status` doesn't silently mean a real state.
- Compile regexps once at package level (`var re = regexp.MustCompile(...)`). `//go:embed` for static assets.
- **Panic is for bugs, not expected errors.** Return errors callers can handle; panic only on violated invariants / `Must*` at init.
- **Timeout every external call**; bound every pool/queue/buffer; retry loops check `ctx.Err()` between attempts.
- Keep the domain layer framework-free; validate at boundaries, trust internal code; make illegal states unrepresentable. Ask the developer which architecture (flat/clean/hexagonal/DDD) before imposing structure - don't over-engineer small projects.

## Data structures

- **Preallocate** slices/maps when size is known - each slice growth copies the whole backing array (O(n)); maps rehash. Don't preallocate speculatively.
- `strings.Builder` for building strings (avoids the `String()` copy); `bytes.Buffer` for bidirectional I/O.
- Arrays only for fixed compile-time sizes (digests, IP addresses) - they're comparable and usable as map keys.
- `container/heap` for priority queues, `container/ring` for circular buffers, `container/list` only for frequent middle insertion (poor cache locality otherwise).
- Generic collections use the tightest constraint (`comparable` for keys, `cmp.Ordered` for sorting): `type Set[T comparable] map[T]struct{}`.
- Use `map[K]*V` for large value types to avoid per-access copies. `unsafe.Pointer` only via the 6 spec patterns, never stored in a `uintptr` across statements. `weak.Pointer[T]` (1.24+) for GC-reclaimable caches.

## Doc comments

Every exported symbol (and complex internal ones) gets a doc comment that **starts with the symbol name** and a verb phrase. Explain *why/when/constraints/what-goes-wrong* - not what the signature already states. Package comment (`// Package foo …`) is mandatory. Use `Deprecated:` markers, and `ExampleXxx` functions as executable, test-verified documentation for libraries.
