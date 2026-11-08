# Standards checklist (when the repo has no REVIEW.md)

This is the always-on lens. Repo-specific rules (i18n, SQL store conventions, mobile UI…) live in the project's `CLAUDE.md` or `docs/code-standards.md` - read those first and layer them on top of this list.

**Correctness**
- Off-by-one, nil/null deref, missing error handling, swallowed errors.
- Race conditions, goroutine leaks, channel ownership, unprotected shared state.
- Edge cases on inputs the author probably didn't test (empty, zero, max, unicode, timezone, DST).

**Security**
- Injection - SQL, command, template, XSS. Look for string concat or `fmt.Sprintf` into queries/shells/HTML.
- Hardcoded secrets, tokens, API keys. Anything resembling base64 or hex of ≥32 chars.
- Auth scoping. `userID` vs `tenantID` vs `sessionID` - never trust the wrong one.
- SSRF, path traversal, open redirect on any URL/path read from input.

**Reliability**
- Retries without idempotency keys.
- Unbounded queues, channels, slices, caches.
- Timeouts: any network call without an explicit timeout is a finding.
- Migrations: any schema change must be reversible OR the PR must call out the irreversibility.

**Performance** (only if there's evidence, not vibes)
- N+1 queries - loop over IDs each issuing a DB call.
- Full table scans on hot paths - verify WHERE/JOIN/ORDER BY against existing indexes (check migrations).
- Allocations in hot loops (Go: profile-guided only; don't pre-optimize).
- Framework AI-slop: `useEffect` for data already in render scope, missing `key`/`useMemo` on heavy lists, `SELECT *` then filter in app code, await-in-loop where a batch call exists. Real, common, cheap to flag.

**Dependencies**
- New dependency for something the stdlib or an existing dep already does → ask "why not the one we have?"
- A heavy/transitive-heavy package for a few lines of logic → flag (supply-chain surface + bundle/binary weight).
- Version bumps that cross a major, or lockfile churn unrelated to the PR's purpose → call out.
- Unpinned/`latest` or a brand-new low-adoption package on a critical path → security finding, not a nit.

**API surface & breakage**
- Renamed/removed exports → downstream breaks.
- Changed response shape / status codes → client breaks.
- Config-file schema change → ops breaks. Needs a migration note or backwards-compat shim.

**Testing**
- New code paths covered? Edge cases tested, not just happy path?
- Tests touching real DB or mocks - match the repo's existing convention. Don't mix.
- Are there tests that would catch the bug if the author re-introduced it tomorrow? If no, ask for one.
- Tests run on fakes but the change reads real data or feeds a downstream reader? Probe it live (`live-verification.md`).

**Change shape**
- Refactor + new behavior in one PR → ask to split. A reviewer can't tell a behavior change from a move when they're tangled, and a bad refactor hides inside the feature diff.
- Dead/zombie code: a function/flag/branch the diff stops calling but leaves behind → flag and *ask* (it may be load-bearing elsewhere - don't assert "remove it"). Same for commented-out blocks.

**Project conventions**
- Read `CLAUDE.md`, `docs/code-standards.md`, `docs/system-architecture.md` if present. Apply repo-specific rules (i18n keys in 3 locales, h-dvh not h-screen, parameterized SQL, etc.).
- Calibrate: if the code is correct, safe, and readable, ship it - don't manufacture findings to look thorough. "Different from how I'd write it" is not a finding (a product choice is a question, not a finding).

