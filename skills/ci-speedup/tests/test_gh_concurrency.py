"""Guards for the gh data pass's fetch concurrency (the shared pool, the bounded prefetch
buffer, the token-wide rate governor) and — the point of all of it — that NONE of it
changes what the pass measures.

The claim this PR rests on is narrow and testable: parallelising the fetches changes
*when* a gh call is issued, never *which* call, *how many*, or *what comes back*. So
the load-bearing tests here are equivalence tests — run the same collection with the
prefetch waves ON and with them OFF (the pre-PR serial path) and demand byte-identical
findings and an identical gh call count — plus the two ordering invariants the
architecture depends on:

  * results zip back in INPUT order (`pool.map` order, not completion order), and
  * the adaptive deepen ROUNDS stay serial (each round's ranking must see the previous
    round's corrected p50s — ARCHITECTURE §2.1's convergence guarantee).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import threading
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import collect_runs as cr  # noqa: E402


# =============================================================================
# Route keying + the token-bucket governor
# =============================================================================

def test_route_key_collapses_ids_and_drops_the_query_string():
    # Two different runs' job listings are the SAME REST route. Query params never make a
    # new route, and neither does the owner/repo — GitHub templates those as parameters.
    a = cr._route_key("repos/o/r/actions/runs/123/jobs?per_page=100&filter=all")
    b = cr._route_key("repos/o/r/actions/runs/456/jobs?per_page=100")
    assert a == b == "repos/*/*/actions/runs/*/jobs"


def test_route_key_separates_genuinely_different_routes():
    keys = {
        cr._route_key("repos/o/r/actions/runs/1/jobs?per_page=100"),
        cr._route_key("repos/o/r/actions/workflows/7/runs?per_page=20"),
        cr._route_key("repos/o/r/actions/jobs/9/logs"),
        cr._route_key("repos/o/r/commits/abc/check-runs?per_page=100"),
    }
    assert len(keys) == 4


def test_route_key_collapses_non_numeric_params_too():
    """R2. `_route_key` used to collapse only NUMERIC segments, which left two whole
    families keyed per-VALUE — a fresh bucket per commit SHA and a fresh bucket per
    workflow FILE. Under the old per-route governor that meant those families were paced by
    nothing at all (every call arrived at a cold bucket with a full burst).

    A route is the TEMPLATE, not the literal path: two SHAs are one route, two workflow
    files are one route, and two repos are one route."""
    # Per-SHA: `GET /repos/{owner}/{repo}/commits/{ref}/check-runs` is ONE route.
    assert (cr._route_key("repos/o/r/commits/a1b2c3d4/check-runs?per_page=100")
            == cr._route_key("repos/o/r/commits/deadbeef/check-runs?per_page=100")
            == "repos/*/*/commits/*/check-runs")
    # Per-FILE: `GET /repos/{owner}/{repo}/contents/{path}` is ONE route — and `{path}`
    # contains slashes, so it must collapse whole, not segment by segment.
    assert (cr._route_key("repos/o/r/contents/.github/workflows/ci.yml")
            == cr._route_key("repos/o/r/contents/.github/workflows/release.yml")
            == "repos/*/*/contents/*")
    # Per-REPO: a process auditing N repos is hitting ONE route, not N.
    assert (cr._route_key("repos/octo/hello/actions/runs/1/jobs")
            == cr._route_key("repos/other/world/actions/runs/2/jobs"))


class _FakeClock:
    """Monotonic fake clock; `sleep` advances it. Lets the governor's pacing be
    asserted exactly, with no real waiting.

    `max_sleeps` turns a governor LIVE-LOCK into a test failure instead of a hang: the
    bucket's "is a whole token available?" test is a float comparison, and `wait` is
    computed as exactly the time for the missing fraction to accrue — which can re-round to
    a hair under 1.0 and loop forever, sleeping ever-smaller slivers. A hung suite tells you
    nothing; an assertion does."""

    def __init__(self, max_sleeps: int = 100_000) -> None:
        self.t = 0.0
        self.slept: list[float] = []
        self._max_sleeps = max_sleeps

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds
        if len(self.slept) > self._max_sleeps:
            raise AssertionError(
                f"the rate governor slept {len(self.slept)} times — it is live-locking "
                f"(sleeping slivers of {seconds!r}s and never admitting a token)")


#: What GitHub's docs actually say (verbatim, "Rate limits for the REST API" →
#: "Secondary rate limits"): "No more than 900 points per minute are allowed for REST API
#: endpoints, and no more than 2,000 points per minute are allowed for the GraphQL API
#: endpoint." The 900 is an AGGREGATE budget for the token across the whole REST API — the
#: parallel GraphQL clause scores 2,000 against a SINGLE endpoint, and no per-route
#: allowance appears anywhere in GitHub's rate-limit documentation. Every call this module
#: makes is a GET = 1 point, so points == requests.
_GITHUB_REST_POINTS_PER_MIN = 900


def test_the_governor_never_admits_more_than_the_documented_budget_in_any_60s():
    """THE governor invariant — restated against the limit GitHub actually scores.

    An earlier version of this test offered infinite load on ONE route and asserted ≤ 900.
    That proved a property of one BUCKET and said nothing about the number GitHub scores:
    the budget is the TOKEN's, across the whole REST API, so a per-route bucket admitted
    `N_routes × 850`. The load here is spread across MANY routes precisely because that is
    the case the old keying got wrong.

    Offer INFINITE load across every route the pass touches, for 60 fake seconds, and
    demand the TOTAL admitted stays inside GitHub's documented 900/min."""
    routes = [
        "repos/*/*/actions/workflows/*/runs",
        "repos/*/*/actions/runs/*/jobs",
        "repos/*/*/actions/jobs/*/logs",
        "repos/*/*/commits/*/check-runs",
        "repos/*/*/contents/*",
    ]
    clock = _FakeClock()
    gov = cr._RestRateLimiter(now=clock.now, sleep=clock.sleep)   # the SHIPPED constants
    admitted = 0
    while clock.t < 60.0:
        gov.acquire(routes[admitted % len(routes)])
        admitted += 1
    assert admitted <= _GITHUB_REST_POINTS_PER_MIN, (
        f"{admitted} requests admitted across {len(routes)} routes in the first 60s — over "
        f"GitHub's documented {_GITHUB_REST_POINTS_PER_MIN} points/min AGGREGATE secondary "
        "limit for the token; a 403 there burns retry budget and, exhausted, sample data")
    # And the arithmetic that guarantees it, stated directly.
    assert cr._REST_BURST + cr._REST_RATE_PER_MIN <= _GITHUB_REST_POINTS_PER_MIN


def test_the_budget_is_shared_across_routes_because_github_scores_the_token():
    """R2/R7 — the corrected keying, as a behaviour.

    A per-route bucket is not "more conservative": more buckets means MORE admissions. Burn
    the budget on one route and the NEXT route must be paced too, because there is one
    budget, and it belongs to the token."""
    clock = _FakeClock()
    gov = cr._RestRateLimiter(per_min=60, burst=10, now=clock.now, sleep=clock.sleep)
    for _ in range(10):
        gov.acquire("repos/*/*/actions/runs/*/jobs")     # burn the whole burst
    assert clock.slept == []
    gov.acquire("repos/*/*/commits/*/check-runs")        # a DIFFERENT route — still paced
    assert clock.slept == [pytest.approx(1.0)], (
        "a fresh route got a fresh full bucket — the governor is keyed per route, but "
        "GitHub scores the 900/min against the TOKEN across the whole REST API")


def test_the_check_run_and_contents_waves_are_paced_like_everything_else():
    """R2, at the endpoints that were completely unpaced.

    `_route_key` used to collapse only NUMERIC segments, so `commits/{sha}/check-runs` and
    `contents/{file}` each got a brand-new bucket — with a brand-new full burst — on EVERY
    call. Measured against the shipped constants, 60 check-run fetches took 0.0s of pacing.
    This PR also makes the `contents` reads an 8-wide wave (they were serial), so "the
    governor covers them" is load-bearing, not cosmetic."""
    clock = _FakeClock()
    gov = cr._RestRateLimiter(per_min=60, burst=10, now=clock.now, sleep=clock.sleep)
    for i in range(60):                        # 60 DISTINCT SHAs
        gov.acquire(cr._route_key(f"repos/o/r/commits/{i:08x}/check-runs?per_page=100"))
    assert clock.t >= 49.0, (
        f"60 check-run fetches on 60 distinct SHAs were paced for {clock.t}s — a per-SHA "
        "bucket means no pacing at all")

    clock2 = _FakeClock()
    gov2 = cr._RestRateLimiter(per_min=60, burst=10, now=clock2.now, sleep=clock2.sleep)
    for i in range(60):                        # 60 DISTINCT workflow files
        gov2.acquire(cr._route_key(f"repos/o/r/contents/.github/workflows/w{i}.yml"))
    assert clock2.t >= 49.0, (
        f"60 workflow `contents` reads were paced for {clock2.t}s — a per-FILE bucket "
        "means the newly-concurrent contents wave fires at full width, ungoverned")


def test_governor_lets_a_cold_start_burst_up_to_the_burst_allowance():
    # A cold start still bursts — just by `_REST_BURST` (a wave or so), not by a whole
    # minute's budget. So a small repo never notices the governor...
    clock = _FakeClock()
    gov = cr._RestRateLimiter(per_min=60, burst=10, now=clock.now, sleep=clock.sleep)
    for _ in range(10):
        gov.acquire("route/a")
    assert clock.slept == []          # 10 free tokens, zero pauses
    # ...and the 11th is paced, because the burst is the CAPACITY, not the budget.
    gov.acquire("route/a")
    assert clock.slept == [pytest.approx(1.0)]


def test_governor_paces_once_the_bucket_is_dry():
    # per_min=60 => 1 token/sec. Burn the burst, then each further call must wait
    # exactly the refill time for one token.
    clock = _FakeClock()
    gov = cr._RestRateLimiter(per_min=60, burst=10, now=clock.now, sleep=clock.sleep)
    for _ in range(10):
        gov.acquire("route/a")
    gov.acquire("route/a")
    assert clock.slept == [pytest.approx(1.0)]
    gov.acquire("route/a")
    assert clock.slept == [pytest.approx(1.0), pytest.approx(1.0)]


def test_governor_sustains_the_configured_rate_not_the_pool_width():
    # The whole point on a LARGE repo: burst bounds the cold start, the refill rate bounds
    # the sustained pace. Issue 3x the per-minute budget: after the burst, every further
    # call is paced, so the elapsed fake time must be at least the ~170 calls at 1/s.
    clock = _FakeClock()
    gov = cr._RestRateLimiter(per_min=60, burst=10, now=clock.now, sleep=clock.sleep)
    for _ in range(180):
        gov.acquire("route/a")
    assert clock.t >= 169.0


def test_governor_paces_the_aggregate_across_threads():
    # The bucket is shared by the pool's threads, so N threads are paced together, not
    # N-times-over. 8 threads x 20 calls = 160 calls at 60/min with a 10-call burst:
    # 10 free, 150 paced => the fake clock must have advanced ~150s.
    clock = _FakeClock()
    lock = threading.Lock()

    def sleep(seconds: float) -> None:
        with lock:
            clock.sleep(seconds)

    def now() -> float:
        with lock:
            return clock.t

    gov = cr._RestRateLimiter(per_min=60, burst=10, now=now, sleep=sleep)

    def worker() -> None:
        for _ in range(20):
            gov.acquire("route/a")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert clock.t >= 145.0    # ~150 paced calls at 1/s (small float slack)


def test_default_width_is_the_measured_safe_12_and_env_overridable():
    """Width is a tunable module constant. The rate-limit detection / backoff the earlier
    "<= 8" ceiling was waiting on HAS landed (the governor below plus `_invoke`'s
    Retry-After retry and the global breaker), so the cap is lifted and the default is now
    the MEASURED-safe 12 — with the before/after the old ceiling asked for.

    12 was chosen against the WORST case in the dogfood set — gravitational/teleport, 541
    sampled runs: 8 -> 151s, 12 -> 120s (-21%), 16 -> 110s (-27%), all with ZERO rate-limit
    blocks and identical findings. Width 20 on that same repo tripped GitHub's secondary
    limit (2x slower, half the findings dropped), so 12 clears the worst case with margin.

    The knob is env-overridable (`CI_SPEEDUP_FETCH_CONCURRENCY`) for operators on a
    dedicated token; the shipped default (no override) must be 12, and must stay well
    inside GitHub's 100-concurrent secondary limit."""
    assert isinstance(cr._FETCH_CONCURRENCY, int)
    # "No more than 100 concurrent requests" (GitHub's other secondary limit).
    assert 1 <= cr._FETCH_CONCURRENCY <= 100
    # The shipped DEFAULT is the measured-safe 12 — proved in a FRESH interpreter with the
    # override explicitly REMOVED, so an ambient `CI_SPEEDUP_FETCH_CONCURRENCY` in the test
    # env can never silently skip (or flip) this assertion the way an in-process `if not
    # os.environ.get(...)` guard would.
    out = _resolve_width_in_subprocess(value=None)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "12", out.stdout
    # The override must be WIRED (env-derived), not a bare literal a future edit could freeze.
    src = (_SCRIPTS / "collect_runs.py").read_text(encoding="utf-8")
    assert 'os.environ.get("CI_SPEEDUP_FETCH_CONCURRENCY"' in src, (
        "the width must stay env-overridable so an operator on a dedicated token can tune "
        "it without a code change")


def _resolve_width_in_subprocess(value):
    """Resolve `_FETCH_CONCURRENCY` in a FRESH interpreter under a given override value.

    `value=None` removes the var from the child env entirely (proving the true default);
    any string sets it. Import-time resolution is the whole point, so a subprocess is the
    only faithful way to exercise it."""
    import subprocess as _sp
    env = {k: v for k, v in os.environ.items() if k != "CI_SPEEDUP_FETCH_CONCURRENCY"}
    env["PYTHONPATH"] = str(_SCRIPTS)
    if value is not None:
        env["CI_SPEEDUP_FETCH_CONCURRENCY"] = value
    return _sp.run([sys.executable, "-c",
                    "import collect_runs; print(collect_runs._FETCH_CONCURRENCY)"],
                   capture_output=True, text=True, env=env)


def test_env_override_actually_changes_the_width():
    """The override is resolved at import time, so prove it in a FRESH interpreter: setting
    `CI_SPEEDUP_FETCH_CONCURRENCY` must change the resolved constant end-to-end. A bare
    literal (or a value read once and cached wrong) would ignore it and fail this."""
    out = _resolve_width_in_subprocess(value="17")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "17", out.stdout


def test_bad_and_out_of_range_overrides_degrade_safely_never_crash():
    """The override is operator-supplied, so a typo or an over-eager value must NEVER crash
    the pass (a non-int would otherwise raise at module import; a value < 1 would blow up at
    `ThreadPoolExecutor(max_workers=...)` mid-run). Bad input falls back to the default 12;
    out-of-range input clamps to [1, 100]. Each case is checked in a fresh interpreter."""
    # Empty / non-integer / whitespace -> safe default, import does NOT crash. `""` exercises
    # the `if not raw` empty branch; the rest the `int()` ValueError branch.
    for bad in ("", "abc", "12.5", "  ", "8x"):
        out = _resolve_width_in_subprocess(value=bad)
        assert out.returncode == 0, f"{bad!r} crashed import: {out.stderr}"
        assert out.stdout.strip() == "12", f"{bad!r} -> {out.stdout!r}"
    # Below-1 clamps up to 1 (never 0/-N, which would break the ThreadPoolExecutor).
    for low in ("0", "-5"):
        out = _resolve_width_in_subprocess(value=low)
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == "1", f"{low!r} -> {out.stdout!r}"
    # Above GitHub's 100-concurrent ceiling clamps down to 100.
    out = _resolve_width_in_subprocess(value="500")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "100", out.stdout
    # The governor must keep its worst-case 60s window inside the documented budget...
    assert 0 < cr._REST_RATE_PER_MIN < _GITHUB_REST_POINTS_PER_MIN
    assert 0 < cr._REST_BURST
    assert cr._REST_BURST + cr._REST_RATE_PER_MIN <= _GITHUB_REST_POINTS_PER_MIN
    # ...with REAL headroom, not a hair under the ceiling. The budget is the TOKEN's (the
    # user's shell and editor are on it too), GitHub says some endpoints cost more points
    # than a GET and does not publish which, and a 403 here still costs — backoff/retry
    # budget, and lost data if that budget is exhausted. A governor tuned to 94% of the
    # ceiling is not a safety margin.
    assert cr._REST_BURST + cr._REST_RATE_PER_MIN <= 0.8 * _GITHUB_REST_POINTS_PER_MIN, (
        "the governor's worst-case 60s window leaves <20% of GitHub's documented budget "
        "for everything else on the token")


def test_prefetch_window_stays_coupled_to_the_fetch_width():
    """The raw-log prefetch buffer is DERIVED from the pool width — `_TEXT_WINDOW = 2 ×
    width`, `_TEXT_LOW_WATER = width`. A future edit that froze either at a literal would
    silently decouple the buffer from the width (a raised override would no longer scale its
    peak-memory ceiling, or a lowered one would over-allocate). Pin the relationship."""
    assert cr._TEXT_WINDOW == 2 * cr._FETCH_CONCURRENCY
    assert cr._TEXT_LOW_WATER == cr._FETCH_CONCURRENCY


# =============================================================================
# The prefetch buffer — same calls, same count, same answers
# =============================================================================

class _StubbedGh(cr.GhClient):
    """A real `GhClient` (real buffer, real counters, real pop-once semantics) whose
    LIVE fetch is canned — so the buffer's contract can be asserted without gh."""

    def __init__(self, bodies: dict[str, object] | None = None) -> None:
        super().__init__()
        self.bodies = bodies or {}
        self.live: list[str] = []          # every endpoint actually fetched, in order
        self._live_lock = threading.Lock()

    def _json_live(self, endpoint: str, allow_missing: bool = False):
        with self._live_lock:
            self.live.append(endpoint)
        self._bump(query=True)
        return self.bodies.get(endpoint)

    def _text_live(self, endpoint: str, allow_missing: bool = False):
        with self._live_lock:
            self.live.append(endpoint)
        self._bump(query=True)
        return self.bodies.get(endpoint)


def test_prefetched_response_is_served_without_a_second_call():
    c = _StubbedGh({"a": {"v": 1}, "b": {"v": 2}})
    c.prefetch_json(["a", "b"])
    assert c.queries == 2
    assert c.json("a") == {"v": 1}
    assert c.json("b") == {"v": 2}
    assert c.queries == 2                  # served from the buffer, not re-fetched
    assert c.live == ["a", "b"]


def test_prefetch_consumption_is_pop_once_so_the_call_count_is_unchanged():
    # A caller that legitimately requests the same endpoint twice issued TWO calls
    # before this PR and must still issue two. The buffer is not a cache: it must never
    # silently de-duplicate a repeat request into one call (that would change the
    # measured `gh_query_count` and quietly alter the pass's cost profile).
    c = _StubbedGh({"a": {"v": 1}})
    c.prefetch_json(["a"])
    assert c.json("a") == {"v": 1}
    assert c.json("a") == {"v": 1}          # second request re-issues, exactly as before
    assert c.queries == 2
    assert c.live == ["a", "a"]


def test_prefetch_dedups_within_a_wave():
    c = _StubbedGh({"a": {"v": 1}})
    c.prefetch_json(["a", "a", "a"])
    assert c.queries == 1


def test_prefetch_text_serves_job_logs_from_the_buffer():
    c = _StubbedGh({"log/1": "hello", "log/2": "world"})
    c.prefetch_text(["log/1", "log/2"])
    assert c.queries == 2
    assert c.text("log/1") == "hello"
    assert c.text("log/2") == "world"
    assert c.queries == 2


def test_unconsumed_prefetch_is_counted_not_silently_swallowed():
    # A parked response nobody consumed is a gh call the serial path never made. It must
    # surface (the collector logs it) rather than quietly bill the user's rate limit.
    c = _StubbedGh({"a": {"v": 1}, "b": {"v": 2}})
    c.prefetch_json(["a", "b"])
    c.json("a")
    assert c.drain_prefetch() == 1
    assert c.prefetch_unconsumed == 1


# =============================================================================
# R4 — the raw-log prefetch is a BOUNDED WINDOW, not a flat wave (peak memory)
# =============================================================================

class _PeakTrackingGh(cr.GhClient):
    """A real `GhClient` whose text fetch returns a large canned body and records the
    MAX number of logs held live in the buffer at once — the peak-memory proxy."""

    def __init__(self, n: int) -> None:
        super().__init__()
        self._bodies = {f"log/{i}": "x" * 1024 for i in range(n)}
        self.peak_parked = 0

    def available(self) -> bool:
        return True

    def _text_live(self, endpoint: str, allow_missing: bool = False):
        self._bump(query=True)
        with self._lock:
            parked = sum(len(q) for q in self._prefetched_text.values())
        self.peak_parked = max(self.peak_parked, parked)
        return self._bodies.get(endpoint)


def test_text_prefetch_holds_at_most_a_window_of_logs_live():
    """R4. Job logs are the heaviest responses in the pass (multi-MB each). A flat wave over
    the whole plan materialises EVERY log before any is consumed — peak memory O(plan). The
    bounded window holds at most `_TEXT_WINDOW` logs parked at any moment, so peak memory is
    O(window), independent of plan length. Prefetch a plan far longer than the window and
    walk it; the parked set must never exceed the window."""
    n = 20 * cr._TEXT_WINDOW
    c = _PeakTrackingGh(n)
    plan = [f"log/{i}" for i in range(n)]
    c.prefetch_text(plan)
    # Consume the whole plan in order — this is what refills the window.
    for ep in plan:
        assert c.text(ep) is not None
    assert c.queries == n, "every planned log must still be fetched exactly once"
    assert c.peak_parked <= cr._TEXT_WINDOW, (
        f"{c.peak_parked} logs were held live at once (window is {cr._TEXT_WINDOW}) — the "
        "raw-log prefetch reverted to a flat wave; peak memory is O(plan) on a large repo")
    # And it did NOT collapse into a serial trickle: the pool ran full-width per refill.
    assert c.peak_parked >= cr._FETCH_CONCURRENCY


def test_a_window_miss_out_of_plan_order_does_not_double_fetch():
    """A call site that consumes a still-queued log out of plan order fetches it live and
    the window must drop it from the plan — never fetch it a second time later."""
    c = _StubbedGh({f"log/{i}": f"body{i}" for i in range(3 * cr._TEXT_WINDOW)})
    plan = [f"log/{i}" for i in range(3 * cr._TEXT_WINDOW)]
    c.prefetch_text(plan)
    # Reach for an endpoint the window has NOT fetched yet (it is still in `_text_plan`).
    tail = plan[-1]
    assert c.text(tail) == "body" + str(3 * cr._TEXT_WINDOW - 1)
    # Now drain everything else in order.
    for ep in plan[:-1]:
        c.text(ep)
    assert c.drain_prefetch() == 0, "the out-of-order log must not remain double-planned"
    assert c.queries == len(plan), "each log fetched exactly once, none twice"
    assert c.live.count(tail) == 1


# =============================================================================
# A FAILED fetch through the new seam — the property the whole PR rests on
# =============================================================================

class _FailingGh(cr.GhClient):
    """A real `GhClient` (real buffer, real counters) whose live fetch fails on demand,
    reproducing `_json_live`'s two distinct failure classes:

      * `fail`    — a HARD failure (a 403 / timeout / 5xx): ALWAYS counted in `errors`.
      * `missing` — an expected-absent 404: counted only when the call site did NOT pass
                    `allow_missing=True`.
    """

    def __init__(self, bodies: dict[str, object] | None = None,
                 fail: set[str] | None = None,
                 missing: set[str] | None = None) -> None:
        super().__init__()
        self.bodies = bodies or {}
        self.fail = fail or set()
        self.missing = missing or set()

    def _json_live(self, endpoint: str, allow_missing: bool = False):
        self._bump(query=True)
        if endpoint in self.fail:
            self._bump(error=True)
            return None
        if endpoint in self.missing:
            if not allow_missing:
                self._bump(error=True)
            return None
        return self.bodies.get(endpoint)


def test_a_failed_prefetch_reaches_the_consumer_as_a_counted_failure():
    """The single most important property of the prefetch buffer: a fetch that FAILS
    inside the pool must reach its consumer as `None` *and* leave `errors` incremented —
    so `partial_reason` is set and the report's partial-coverage banner fires. A failure
    that arrived as a silent buffer MISS would be re-fetched (double-counted); a failure
    that arrived without its `errors` bump would render as a clean, complete report with
    a hole in it."""
    c = _FailingGh({"a": {"v": 1}}, fail={"b"})
    c.prefetch_json(["a", "b"])
    assert c.json("a") == {"v": 1}
    assert c.json("b") is None            # the failure is DELIVERED, not a buffer miss...
    assert c.queries == 2                 # ...and not re-fetched behind our back
    assert c.errors == 1                  # ...and it trips the partial-coverage banner
    assert c.drain_prefetch() == 0        # the failed slot was consumed, not orphaned


def test_a_parked_failure_is_not_confused_with_a_buffer_miss():
    # `None` is a legitimate parked VALUE. Popping it must not fall through to a live
    # re-fetch — that would issue a call the serial path never made.
    c = _FailingGh(fail={"a"})
    c.prefetch_json(["a"])
    assert c.queries == 1
    assert c.json("a") is None
    assert c.queries == 1                 # served from the buffer; no second call


@pytest.fixture
def _canned_gh(monkeypatch):
    def _install(returncode: int, stderr: str):
        import subprocess as _sp

        def fake_run(*a, **k):
            return _sp.CompletedProcess(args=["gh"], returncode=returncode,
                                        stdout="", stderr=stderr)
        monkeypatch.delenv("CI_SPEEDUP_GH_FIXTURES", raising=False)
        monkeypatch.setattr(cr.subprocess, "run", fake_run)
        # These fixtures drive `GhClient._invoke`'s failure paths, and a rate-limit / 5xx
        # classification is now RETRIED with a jittered 60s+ backoff (post-merge: the live
        # core is main's `_invoke`). The accounting under test — a 403 still counts even
        # under allow_missing — is unchanged; only the retry sleeps are new, so serve them
        # as no-ops rather than actually waiting minutes. `_invoke` and `_sleep_until_
        # unblocked` both back off via `collect_runs.time.sleep`.
        monkeypatch.setattr(cr.time, "sleep", lambda *_a, **_k: None)
    return _install


def test_allow_missing_does_not_count_a_404(_canned_gh):
    # What `allow_missing` actually means: a 404 HERE is expected (no admin on the repo,
    # a workflow file that no longer exists). Not a collection error.
    _canned_gh(1, "gh: Not Found (HTTP 404)")
    c = cr.GhClient()
    assert c.json("repos/o/r/rulesets", allow_missing=True) is None
    assert c.errors == 0


def test_allow_missing_still_counts_a_403_and_says_so_at_warning(_canned_gh, caplog):
    """BLOCKER 2. A secondary-rate-limit 403 also makes `gh api` exit non-zero. Treating it
    like the expected 404 leaves `errors` at 0 → `partial_reason` None → the report's
    partial-coverage banner NEVER fires, and (at the `contents` call sites, which all pass
    `allow_missing=True`) a workflow's entire file-level signal — its `on:` block,
    matrix/shard recognition, timeout specs, event scope — silently evaluates against an
    empty dict. The report renders clean and complete with the data missing."""
    _canned_gh(1, "gh: You have exceeded a secondary rate limit (HTTP 403)")
    c = cr.GhClient()
    with caplog.at_level("WARNING", logger=cr.logger.name):
        assert c.json("repos/o/r/contents/.github/workflows/ci.yml",
                      allow_missing=True) is None
    assert c.errors == 1, "a 403 under allow_missing must still trip the coverage banner"
    assert any("403" in r.getMessage() for r in caplog.records), (
        "the failure must be visible at the default INFO level, not only at DEBUG")


def test_allow_missing_counts_a_403_that_arrives_through_a_prefetch_wave(_canned_gh):
    # The `contents` reads are prefetched with allow_missing=True in ONE late wave — exactly
    # where secondary-limit pressure peaks. The accounting must be identical there.
    _canned_gh(1, "gh: You have exceeded a secondary rate limit (HTTP 403)")
    c = cr.GhClient()
    c.prefetch_json(["repos/o/r/contents/a.yml", "repos/o/r/contents/b.yml"],
                    allow_missing=True)
    assert c.errors == 2, "a 403 in a prefetch wave counts exactly as it would at the site"
    assert c.json("repos/o/r/contents/a.yml", allow_missing=True) is None
    assert c.json("repos/o/r/contents/b.yml", allow_missing=True) is None
    assert c.queries == 2                 # both failures were DELIVERED, not re-fetched
    assert c.drain_prefetch() == 0


def test_an_endpoint_id_containing_404_is_not_mistaken_for_a_status_code(_canned_gh):
    # gh echoes the endpoint in its error text; run id 404 must not read as HTTP 404.
    _canned_gh(1, "gh: HTTP 403 rate limited: repos/o/r/actions/runs/404/jobs")
    c = cr.GhClient()
    assert c.json("repos/o/r/actions/runs/404/jobs", allow_missing=True) is None
    assert c.errors == 1


def test_an_undecodable_job_log_fails_one_call_not_the_whole_wave(monkeypatch):
    """L8. `subprocess.run(..., text=True)` DECODES the child's stdout, and a job log is
    arbitrary bytes. Uncaught, a `UnicodeDecodeError` escapes `pool.map()` and discards the
    entire wave — hundreds of good responses lost to one bad log."""
    monkeypatch.delenv("CI_SPEEDUP_GH_FIXTURES", raising=False)

    def fake_run(args, **k):
        import subprocess as _sp
        if args[-1] == "log/bad":
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        return _sp.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(cr.subprocess, "run", fake_run)
    c = cr.GhClient()
    c.prefetch_text(["log/1", "log/bad", "log/2"])       # must NOT raise
    assert c.text("log/1") == "ok"
    assert c.text("log/bad") is None                     # one failed log...
    assert c.text("log/2") == "ok"                       # ...the wave survives
    assert c.errors == 1


def test_an_emfile_spawning_the_nth_gh_fails_one_call_not_the_whole_wave(monkeypatch):
    """R8. Forking the Nth concurrent `gh` can fail with EMFILE / ENOMEM — an `OSError`,
    NOT its subclass `FileNotFoundError`. The `except` tuples caught `FileNotFoundError`
    (gh missing) but not the base `OSError`, so a spawn failure under descriptor pressure
    escaped `pool.map()` and discarded the whole wave. It must be a single counted failure,
    exactly like the undecodable log above — on BOTH the json and text paths."""
    monkeypatch.delenv("CI_SPEEDUP_GH_FIXTURES", raising=False)

    def fake_run(args, **k):
        import subprocess as _sp
        if args[-1].endswith("/bad"):
            raise OSError(24, "Too many open files")     # EMFILE
        return _sp.CompletedProcess(args=args, returncode=0, stdout='{"ok":1}', stderr="")

    monkeypatch.setattr(cr.subprocess, "run", fake_run)
    c = cr.GhClient()
    c.prefetch_json(["j/1", "j/bad", "j/2"])             # must NOT raise
    assert c.json("j/1") == {"ok": 1}
    assert c.json("j/bad") is None
    assert c.json("j/2") == {"ok": 1}
    assert c.errors == 1
    # And the text path (a raw-log fetch) survives an EMFILE the same way.
    c2 = cr.GhClient()
    c2.prefetch_text(["log/ok", "log/bad"])              # must NOT raise
    assert c2.text("log/bad") is None
    assert c2.errors == 1


# =============================================================================
# The buffer key carries the ACCOUNTING RULE, and never becomes a cache
# =============================================================================

def test_a_permissively_prefetched_response_is_not_served_to_a_strict_call_site(caplog):
    """HIGH 5. `allow_missing` decides whether a failure COUNTS. It is applied at prefetch
    time on a pool thread; if the parked value could then be handed to a call site passing
    `allow_missing=False`, the failure would already have gone uncounted and the consumer
    would just see `None` — a manufactured silent drop, one careless plan edit away. The
    flag is part of the key, so the mismatched consumer misses and fetches live under its
    OWN rule."""
    c = _FailingGh(missing={"e"})
    c.prefetch_json(["e"], allow_missing=True)
    assert c.errors == 0                       # parked under the permissive rule
    with caplog.at_level("WARNING", logger=cr.logger.name):
        assert c.json("e", allow_missing=False) is None
    assert c.errors == 1, "the strict call site's fetch must be counted under ITS rule"
    assert c.queries == 2                      # it really did re-fetch
    assert any("allow_missing" in r.getMessage() for r in caplog.records), (
        "a plan/call-site disagreement about the accounting rule must be loud")


def test_the_buffer_is_not_a_cross_phase_cache_when_a_plan_drifts():
    """A parked-but-unconsumed response used to survive to the end of `collect()`, and a
    LATER wave planning the same endpoint would SKIP it — so a later call site popped the
    STALE value instead of issuing its own call, and the drift guard saw nothing. Each
    planned endpoint is now fetched and queued (FIFO), so plan N's response goes to call
    site N."""
    c = _StubbedGh({"a": {"v": 1}})
    c.prefetch_json(["a"])                     # phase 1 plans it...
    c.prefetch_json(["a"])                     # ...phase 2 plans it again
    assert c.queries == 2, "the second wave must fetch, not reuse phase 1's parked value"
    assert c.json("a") == {"v": 1}
    assert c.json("a") == {"v": 1}
    assert c.queries == 2                      # both consumers were served from the buffer
    assert c.drain_prefetch() == 0


def test_drain_counts_every_queued_leftover_not_just_distinct_endpoints():
    c = _StubbedGh({"a": {"v": 1}})
    c.prefetch_json(["a"])
    c.prefetch_json(["a"])
    assert c.drain_prefetch() == 2
    assert c.prefetch_unconsumed == 2


class _Minimal:
    """A duck-typed client with NO prefetch buffer (the detectors' test doubles, and any
    caller wiring in its own client)."""

    def json(self, endpoint, allow_missing=False):
        return {}

    def text(self, endpoint, allow_missing=False):
        return ""


def test_prefetch_is_optional_on_the_client_contract():
    # `_prefetch_json`/`_prefetch_text` must degrade to a no-op on a client with no
    # buffer: prefetch is an accelerator, and a client without one just fetches serially
    # at the original call site.
    cr._prefetch_json(_Minimal(), ["a", "b"])          # must not raise
    cr._prefetch_text(_Minimal(), ["c"])               # must not raise


def test_a_client_without_a_buffer_says_so_once(caplog, monkeypatch):
    """L7. The duck-typed `getattr(client, "prefetch_json", None)` is forgiving on
    purpose — but a silent miss is also exactly what a RENAME looks like: every wave in the
    run would quietly revert to serial, `drain_prefetch` would disable its own drift guard,
    and the only evidence would be a stopwatch. Name the class once, at DEBUG."""
    monkeypatch.setattr(cr, "_NO_BUFFER_WARNED", set())
    with caplog.at_level("DEBUG", logger=cr.logger.name):
        cr._prefetch_json(_Minimal(), ["a"])
        cr._prefetch_json(_Minimal(), ["b"])           # ...and only ONCE per class+method
        cr._prefetch_text(_Minimal(), ["c"])
    said = [r.getMessage() for r in caplog.records if "_Minimal" in r.getMessage()]
    assert len(said) == 2                              # one per seam (json, text)
    assert any("prefetch_json" in m for m in said)
    assert any("prefetch_text" in m for m in said)


# =============================================================================
# The unpinned 30-day window must not slide mid-run
# =============================================================================

def test_unpinned_window_is_fixed_for_the_whole_run(monkeypatch):
    """`datetime.now()` has SECOND resolution and a collection runs for minutes, so
    re-reading the clock per call let the 30-day volume window slide mid-run — two
    workflows a second apart were counted over two DIFFERENT windows. Worse, one logical
    query then stringified differently at different moments, so the prefetch buffer
    (keyed by the endpoint string) missed and paid for the call twice. The window is now
    resolved once per process."""
    monkeypatch.setattr(cr, "_UNPINNED_NOW", None)
    ticks = iter([_dt.datetime(2026, 6, 1, 12, 0, 0, tzinfo=_dt.timezone.utc),
                  _dt.datetime(2026, 6, 1, 12, 0, 30, tzinfo=_dt.timezone.utc),
                  _dt.datetime(2026, 6, 1, 12, 2, 0, tzinfo=_dt.timezone.utc)])

    class _Clock:
        @staticmethod
        def now(tz=None):
            return next(ticks)

    monkeypatch.setattr(cr._dt, "datetime", _Clock)
    first = cr._window_30d(None)
    later = cr._window_30d(None)
    much_later = cr._window_30d(None)
    assert first == later == much_later     # the clock moved; the window did not


def test_unpinned_window_endpoint_is_stable_so_prefetch_matches_the_call_site(monkeypatch):
    monkeypatch.setattr(cr, "_UNPINNED_NOW", None)
    a = cr._volume_endpoint("o/r", 7, None)
    b = cr._volume_endpoint("o/r", 7, None)
    assert a == b


def test_a_pinned_window_is_unaffected():
    since, upper = cr._window_30d("2026-05-31T18:28:55Z")
    assert upper == "2026-05-31T18:28:55Z"
    assert since == "2026-05-01T18:28:55Z"


# =============================================================================
# Determinism — results zip back in INPUT order, never completion order
# =============================================================================

def test_gather_run_jobs_returns_input_order_under_inverted_completion_order():
    # `_gather_run_jobs`'s callers index into its result positionally, so the flattened
    # pool MUST return input order. Force completion order to be the REVERSE of input
    # order (the last run finishes first) and demand the zip still aligns.
    # Exactly the pool's width, so every fetch really can be in flight at once (a barrier
    # wider than the pool would deadlock — which is itself the point of a bounded pool).
    runs = [{"id": i} for i in range(cr._FETCH_CONCURRENCY)]
    done: list[int] = []
    gate = threading.Barrier(len(runs), timeout=10)

    def fetch(client, repo, run_id):
        gate.wait()                       # every fetch is in flight at once
        # Later ids "finish" first.
        for _ in range((run_id + 1) * 200):
            pass
        done.append(run_id)
        return [{"name": f"job-{run_id}"}]

    kept, failures = cr._gather_run_jobs(None, "o/r", runs, fetch=fetch)
    n = len(runs)
    assert failures == 0
    assert [r["id"] for r, _ in kept] == list(range(n))           # INPUT order
    assert [jobs[0]["name"] for _, jobs in kept] == [f"job-{i}" for i in range(n)]


def test_gather_run_jobs_keeps_failures_and_empties_apart_when_pooled():
    # The None-vs-[] distinction (a FAILED fetch is a coverage gap; an empty run is not)
    # must survive the flattening.
    runs = [{"id": 1}, {"id": 2}, {"id": 3}]

    def fetch(client, repo, run_id):
        return {1: [{"name": "a"}], 2: None, 3: []}[run_id]

    kept, failures = cr._gather_run_jobs(None, "o/r", runs, fetch=fetch)
    assert failures == 1
    assert [r["id"] for r, _ in kept] == [1]


def test_gather_run_jobs_reads_prefetched_listings_without_refetching():
    c = _StubbedGh({cr._run_jobs_endpoint("o/r", i): {"jobs": [{"name": f"j{i}"}]}
                    for i in (1, 2, 3)})
    runs = [{"id": 1}, {"id": 2}, {"id": 3}]
    cr._prefetch_json(c, [cr._run_jobs_endpoint("o/r", r["id"]) for r in runs])
    assert c.queries == 3
    kept, failures = cr._gather_run_jobs(c, "o/r", runs)
    assert c.queries == 3                       # all three came from the buffer
    assert failures == 0
    assert [r["id"] for r, _ in kept] == [1, 2, 3]
    assert [jobs[0]["name"] for _, jobs in kept] == ["j1", "j2", "j3"]


# =============================================================================
# End-to-end equivalence — parallel collection == serial collection
# =============================================================================

def _iso(offset_s: int) -> str:
    base = _dt.datetime(2026, 6, 1, tzinfo=_dt.timezone.utc)
    return (base + _dt.timedelta(seconds=offset_s)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _job(name: str, dur: int, jid: int) -> dict:
    return {"id": jid, "name": name, "status": "completed", "conclusion": "success",
            "started_at": _iso(0), "completed_at": _iso(dur),
            "labels": ["ubuntu-latest"], "html_url": f"https://x/job/{jid}",
            "steps": [{"name": "Run tests", "number": 1, "status": "completed",
                       "conclusion": "success", "started_at": _iso(0),
                       "completed_at": _iso(dur)}]}


class _RepoFake(cr.GhClient):
    """A real `GhClient` (so the prefetch buffer and counters are the real ones) serving
    a canned 2-workflow repo. `waves` records each prefetch wave in order — that's how
    the deepen-round serialisation is asserted below."""

    #  a.yml — `A job`: 1000s on the newest 10 runs, 20s on the older 10.
    #          Shallow (10-run) p50 = 1000s; full-depth p50 = 510s.
    #  b.yml — `B job`: a flat 600s across all 20 runs.
    # So the shallow ranking puts A on top; deepening A CORRECTS it below B, which is
    # what pulls B into a SECOND deepen round. That is exactly ARCHITECTURE §2.1's
    # convergence loop, and it only works if round 2 ranks on round 1's corrected p50.
    def __init__(self) -> None:
        super().__init__()
        self.waves: list[list[str]] = []
        self._wave_lock = threading.Lock()
        self.jobs: dict[int, list[dict]] = {}
        for i in range(20):
            self.jobs[100 + i] = [_job("A job", 1000 if i < 10 else 20, 9000 + i)]
            self.jobs[200 + i] = [_job("B job", 600, 9500 + i)]

    def prefetch_json(self, endpoints, *, allow_missing: bool = False) -> None:
        eps = [e for e in dict.fromkeys(endpoints) if e]
        with self._wave_lock:
            if eps:
                self.waves.append(eps)
        super().prefetch_json(eps, allow_missing=allow_missing)

    def available(self) -> bool:
        return True

    def _runs(self, wf_id: int) -> list[dict]:
        base = 100 if wf_id == 1 else 200
        wall = 1010 if wf_id == 1 else 610
        # Two runs per workflow are RE-RUNS (`run_attempt > 1`), so the rerun-attempt
        # sampler's `filter=all` / `filter=latest` legs actually execute — otherwise the
        # tests below that assert on that plan would pass vacuously.
        #
        # `conclusion`/`status` are REQUIRED post-merge: the loop reads the all-status page
        # and DERIVES the success sample (`_success_runs_from_all_status`, #213), which keeps
        # only `conclusion=="success" and status=="completed"` runs. Server-side
        # `status=success` filtering (the pre-merge path this fixture was written for) made
        # those fields implicit; the derive path reads them, so the canned runs must carry
        # them to model 20 successful runs.
        return [{"id": base + i, "event": "pull_request", "head_sha": f"s{i}",
                 "created_at": _iso(0), "run_started_at": _iso(0),
                 "run_attempt": 2 if i in (3, 7) else 1,
                 "conclusion": "success", "status": "completed",
                 "updated_at": _iso(wall)} for i in range(20)]

    def _json_live(self, endpoint: str, allow_missing: bool = False):
        self._bump(query=True)
        if endpoint.startswith("repos/o/r/actions/workflows?"):
            return {"workflows": [
                {"id": 1, "path": ".github/workflows/a.yml", "name": "a"},
                {"id": 2, "path": ".github/workflows/b.yml", "name": "b"}]}
        m = re.match(r"repos/o/r/actions/workflows/(\d+)/runs\?(.*)", endpoint)
        if m:
            wf_id, qs = int(m.group(1)), m.group(2)
            if "per_page=1&" in qs or qs.startswith("per_page=1&"):
                return {"total_count": 40}
            return {"workflow_runs": self._runs(wf_id)}
        m = re.match(r"repos/o/r/actions/runs/(\d+)/jobs", endpoint)
        if m:
            return {"jobs": self.jobs.get(int(m.group(1)), [])}
        m = re.match(r"repos/o/r/commits/([^/]+)/check-runs", endpoint)
        if m:
            return {"check_runs": [
                {"name": "A job", "started_at": _iso(0), "completed_at": _iso(1000)},
                {"name": "B job", "started_at": _iso(0), "completed_at": _iso(600)}]}
        if endpoint == "repos/o/r":
            return {"default_branch": "main", "visibility": "public"}
        return None

    def _text_live(self, endpoint: str, allow_missing: bool = False):
        self._bump(query=True)
        return ""


def _doc() -> dict:
    return {"findings": [
        {"id": "f1", "workflow_file": ".github/workflows/a.yml"},
        {"id": "f2", "workflow_file": ".github/workflows/b.yml"},
    ]}


def _collect_with(monkeypatch, *, serial: bool) -> tuple[dict, _RepoFake]:
    client = _RepoFake()
    monkeypatch.setattr(cr, "GhClient", lambda: client)
    if serial:
        # The pre-PR path: no prefetch waves at all, every call issued at its original
        # site, one at a time.
        monkeypatch.setattr(cr, "_prefetch_json", lambda *a, **k: None)
        monkeypatch.setattr(cr, "_prefetch_text", lambda *a, **k: None)
    out = cr.collect(_doc(), "o/r", max_runs=20, shallow_runs=10)
    return out, client


def test_parallel_collection_is_byte_identical_to_serial_collection(monkeypatch):
    """THE guard for this PR. Same repo, same fixtures, prefetch waves ON vs OFF — the
    findings document must be identical, down to the byte. If parallelising the fetches
    could change the gate, a pole, or the floor, this fails."""
    with monkeypatch.context() as m:
        parallel, pc = _collect_with(m, serial=False)
    with monkeypatch.context() as m:
        serial, sc = _collect_with(m, serial=True)

    assert json.dumps(parallel, sort_keys=True) == json.dumps(serial, sort_keys=True)


def test_parallel_collection_issues_the_same_gh_calls_as_serial(monkeypatch):
    """Orchestration only: prefetching must not add, drop, or de-duplicate a single gh
    call. Compare the CALL COUNT and the endpoint MULTISET, not the order (reordering
    them is the entire point)."""
    with monkeypatch.context() as m:
        _, pc = _collect_with(m, serial=False)
    with monkeypatch.context() as m:
        _, sc = _collect_with(m, serial=True)

    assert pc.queries == sc.queries
    assert pc.errors == sc.errors == 0
    # Nothing was fetched that no call site consumed.
    assert pc.prefetch_unconsumed == 0


def test_prefetch_drift_is_recorded_in_the_report_not_just_stderr(monkeypatch):
    """MEDIUM 6. The drift guard earned its keep (it caught 31 real unconsumed prefetches
    while this pass was built), but a stderr WARNING dies with the scrollback. The count
    belongs in `data_sources`, where the committed report carries it and the repo's
    data-driven report guards can catch a regression."""
    with monkeypatch.context() as m:
        out, _ = _collect_with(m, serial=False)
    assert out["data_sources"]["prefetch_unconsumed"] == 0

    # And it is a real count, not a hard-coded zero: park something nobody will consume.
    class _Drifted(_RepoFake):
        def prefetch_json(self, endpoints, *, allow_missing: bool = False) -> None:
            super().prefetch_json(endpoints, allow_missing=allow_missing)
            # a plan that fetches a run nobody asks for — the exact drift shape
            super().prefetch_json([cr._run_jobs_endpoint("o/r", 999)],
                                  allow_missing=allow_missing)

    with monkeypatch.context() as m:
        client = _Drifted()
        m.setattr(cr, "GhClient", lambda: client)
        out = cr.collect(_doc(), "o/r", max_runs=20, shallow_runs=10)
    assert out["data_sources"]["prefetch_unconsumed"] > 0


# --- R6: the three raw-LOG prefetch plans, exercised end-to-end -------------------
#
# The base equivalence fixture calls `collect()` with no `data_dir`, no cache-family
# finding, and an empty `_text_live`, so `_attach_cache_log_evidence`, `_cache_distribution`
# and `_persist_pole_logs` — the three `prefetch_text` call sites, and the riskiest
# plan/call-site alignments in the PR — never execute in it. This fixture drives all three:
# a real turbo cold-cache log, an OPT6 cache-family finding, push runs for the
# `_cache_distribution` push probe, `with_logs=True`, and a `data_dir`.

# A turbo cold-cache job log: parses (`blocking_path._parse_log`) to a `turbo-remote-cache`
# leaf (a `_CACHE_LEAF_KEYS` member, so the pole drill triggers `_cache_distribution`), and
# carries a verbatim `cache miss` line (so `_attach_cache_log_evidence` finds a MISS).
_TURBO_COLD_LOG = "\n".join([
    "   • Remote caching disabled",
    "cache miss, executing aaa",
    "cache miss, executing bbb",
    " Tasks:    149 successful, 149 total",
    "Cached:    0 cached, 149 total",
    "  Time:    9m48.772s",
])


class _CacheRepoFake(_RepoFake):
    """`_RepoFake` plus what the three raw-log plans need: push runs on `a.yml` (for the
    `_cache_distribution` push probe), and a turbo cold-cache body from every log fetch.
    Records the raw-log endpoints it served so the push probe's execution is assertable."""

    _PUSH_IDS = range(300, 304)

    def __init__(self) -> None:
        super().__init__()
        self.text_calls: list[str] = []
        self._text_lock = threading.Lock()
        for i in self._PUSH_IDS:                       # push runs' A-job jobs
            self.jobs[i] = [_job("A job", 900, 9300 + (i - 300))]

    def _runs(self, wf_id: int) -> list[dict]:
        runs = super()._runs(wf_id)
        if wf_id == 1:                                 # a.yml also has push runs
            # `conclusion`/`status` for the same reason as `_RepoFake._runs`: the success
            # sample is DERIVED from the all-status page (#213), keeping only completed
            # successes — a push run without them is filtered out, never job-fetched, and
            # the `_cache_distribution` push probe sees no push runs to fetch a log for.
            # PREPEND (not append) so the push runs land INSIDE the derived `max_runs`
            # window: `_success_runs_from_all_status` keeps the first `max_runs` successes
            # in list order, and pushes appended past position 20 would be capped out (the
            # pre-merge path fetched `status=success` unpaginated, so ordering didn't bite).
            push_runs = [{"id": i, "event": "push", "head_sha": f"p{i}",
                          "created_at": _iso(0), "run_started_at": _iso(0),
                          "run_attempt": 1, "conclusion": "success", "status": "completed",
                          "updated_at": _iso(910)}
                         for i in self._PUSH_IDS]
            runs = push_runs + runs
        return runs

    def _text_live(self, endpoint: str, allow_missing: bool = False):
        with self._text_lock:
            self.text_calls.append(endpoint)
        self._bump(query=True)
        return _TURBO_COLD_LOG


def _doc_cache() -> dict:
    # OPT6 is a cache-family pattern with EMPTY keywords, so the miss line matches without
    # a keyword needing to appear in it. `affected_jobs` names the job the walk reads a log
    # for. f2 stays uninstrumented (the b.yml side), as in the base fixture.
    return {"findings": [
        {"id": "f1", "pattern": "OPT6", "workflow_file": ".github/workflows/a.yml",
         "affected_jobs": ["A job"]},
        {"id": "f2", "workflow_file": ".github/workflows/b.yml"},
    ]}


def _collect_cache_with(monkeypatch, *, serial: bool, data_dir) -> tuple[dict, _CacheRepoFake]:
    client = _CacheRepoFake()
    monkeypatch.setattr(cr, "GhClient", lambda: client)
    if serial:
        monkeypatch.setattr(cr, "_prefetch_json", lambda *a, **k: None)
        monkeypatch.setattr(cr, "_prefetch_text", lambda *a, **k: None)
    out = cr.collect(_doc_cache(), "o/r", max_runs=20, with_logs=True,
                     data_dir=data_dir, shallow_runs=10)
    if "data_bundle" in out:                           # the abs data_dir differs per run
        out["data_bundle"]["logs_dir"] = "X"
    return out, client


def test_the_three_text_plans_are_byte_identical_serial_vs_parallel(monkeypatch, tmp_path):
    """R6. `_attach_cache_log_evidence`, `_cache_distribution` and `_persist_pole_logs` are
    the three `prefetch_text` call sites — the riskiest plan/call-site alignments in the PR,
    and the ones the base equivalence fixture never reached. Drive all three with logs ON,
    prefetch waves ON vs OFF, and demand byte-identical findings AND an identical gh call
    count. First, prove all three actually ran (a vacuous pass is the failure mode here)."""
    with monkeypatch.context() as m:
        parallel, pc = _collect_cache_with(m, serial=False, data_dir=tmp_path / "p")
    with monkeypatch.context() as m:
        serial, sc = _collect_cache_with(m, serial=True, data_dir=tmp_path / "s")

    # (1) All three plans genuinely executed — else the equivalence below is vacuous.
    f1 = next(f for f in parallel["findings"] if f["id"] == "f1")
    assert "measured_evidence" in f1, "_attach_cache_log_evidence did not run"
    assert parallel.get("data_bundle", {}).get("logs"), "_persist_pole_logs did not run"
    assert "cache_dist" in json.dumps(parallel), "_cache_distribution did not run"
    # The push probe (the _cache_distribution text plan) fetched a PUSH run's log.
    assert any("9300" in e for e in pc.text_calls), "the push probe never fetched a log"

    # (2) The load-bearing equivalence: same data, same call count, no unconsumed prefetch.
    assert json.dumps(parallel, sort_keys=True) == json.dumps(serial, sort_keys=True)
    assert pc.queries == sc.queries
    assert pc.errors == sc.errors == 0
    assert parallel["data_sources"]["prefetch_unconsumed"] == 0
    assert serial["data_sources"]["prefetch_unconsumed"] == 0


def test_the_rerun_attempt_plan_never_prefetches_the_latest_leg(monkeypatch):
    """A prefetch plan must never be MORE EAGER than its consumer. The `filter=latest` leg
    of the rerun-attempt sample is the one whose call site is actively changing (deriving
    the latest view from the `filter=all` payload, and fetching only a small fallback
    subset). A plan that assumes the leg happens for every run keeps paying for N calls per
    workflow that nobody consumes — they land in `prefetch_unconsumed`, get drained, and
    the only symptom is a warning. So: `filter=all` may be planned, `filter=latest` may
    not."""
    with monkeypatch.context() as m:
        _, c = _collect_with(m, serial=False)
    planned = [e for wave in c.waves for e in wave]
    assert not [e for e in planned if "filter=latest" in e], (
        "the rerun-attempt prefetch plan assumes a `filter=latest` fetch per run — if the "
        "call site stops making it, the plan silently keeps paying for it")


def test_the_shallow_job_sample_is_fetched_as_one_flat_wave(monkeypatch):
    """LEVER 2. The per-run job listing used to be pooled PER WORKFLOW. It must now be
    ONE wave spanning every workflow's shallow sample — otherwise the pool spends its
    life partly idle."""
    with monkeypatch.context() as m:
        _, c = _collect_with(m, serial=False)

    shallow_a = {cr._run_jobs_endpoint("o/r", 100 + i) for i in range(10)}
    shallow_b = {cr._run_jobs_endpoint("o/r", 200 + i) for i in range(10)}
    flat = [w for w in c.waves
            if shallow_a <= set(w) and shallow_b <= set(w)]
    assert flat, "the shallow job sample was not fetched as a single cross-workflow wave"


def test_the_run_list_family_is_hoisted_out_of_the_per_workflow_loop(monkeypatch):
    """LEVER 1. Both workflows' volume probe + success run-list must be issued in one
    wave BEFORE any per-workflow bookkeeping, not one workflow at a time."""
    with monkeypatch.context() as m:
        _, c = _collect_with(m, serial=False)

    def _lists(wave):
        return {e for e in wave if re.match(r"repos/o/r/actions/workflows/\d+/runs\?", e)}

    hoisted = [w for w in c.waves
               if len({re.match(r"repos/o/r/actions/workflows/(\d+)/runs\?", e).group(1)
                       for e in _lists(w)}) >= 2]
    assert hoisted, "the run-list family was not fanned out across workflows"


def test_deepen_rounds_are_never_parallelised_across_rounds(monkeypatch):
    """ARCHITECTURE §2.1's convergence guarantee is a FEEDBACK loop: round N+1's ranking
    is computed from round N's corrected p50s. Overlapping the rounds would rank against
    a half-deepened sample and could settle on a different top region — so the rounds
    must stay strictly serial, even though the workflows WITHIN a round may fan out.

    Scenario (see `_RepoFake`): A's shallow p50 (1000s) beats B's (600s), so round 1
    deepens A alone. Deepening CORRECTS A to 510s, which lifts B into the top region —
    so B is deepened in round 2. If the two rounds had been fused into one wave, B's
    deeper runs would appear alongside A's; they must not."""
    m = monkeypatch
    m.setattr(cr, "_DEEPEN_TOP_CHECKS", 2)     # force the two-round convergence above
    out, c = _collect_with(m, serial=False)

    # Both workflows were in fact deepened, in two rounds (else this test proves nothing).
    ds = out["data_sources"]
    assert ds["deepened_workflows"] == 2
    assert set(ds["full_depth_workflows"]) == {".github/workflows/a.yml",
                                               ".github/workflows/b.yml"}

    deep_a = {cr._run_jobs_endpoint("o/r", 110 + i) for i in range(10)}   # A's runs 11-20
    deep_b = {cr._run_jobs_endpoint("o/r", 210 + i) for i in range(10)}   # B's runs 11-20

    waves_with_a = [i for i, w in enumerate(c.waves) if deep_a & set(w)]
    waves_with_b = [i for i, w in enumerate(c.waves) if deep_b & set(w)]
    assert waves_with_a and waves_with_b

    # No wave may carry BOTH rounds' deep fetches — that would be a fused round.
    for w in c.waves:
        assert not (deep_a & set(w) and deep_b & set(w)), (
            "a deepen wave fetched two rounds' workflows at once — the rounds were "
            "fused, so round 2 ranked against a sample round 1 had not yet corrected")
    # And round 2's wave must come strictly after round 1's.
    assert max(waves_with_a) < min(waves_with_b)

    # The convergence outcome itself must be unchanged.
    assert ds["deepen_converged"] is True


def test_deepen_still_converges_to_the_same_answer_as_the_serial_path(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(cr, "_DEEPEN_TOP_CHECKS", 2)
        parallel, _ = _collect_with(m, serial=False)
    with monkeypatch.context() as m:
        m.setattr(cr, "_DEEPEN_TOP_CHECKS", 2)
        serial, _ = _collect_with(m, serial=True)
    assert (json.dumps(parallel, sort_keys=True)
            == json.dumps(serial, sort_keys=True))


# =============================================================================
# Record mode — the check-then-set on `_recorded_from` must hold the lock
# =============================================================================

class _LockAssertingDict(dict):
    """A dict that fails if it is read or written while `owner._lock` is not held —
    so a check-and-set that escapes the lock is a test failure, not a rare race."""

    def __init__(self, owner):
        super().__init__()
        self._owner = owner

    def _assert_locked(self):
        # `threading.Lock` has no "is held by me", but `acquire(blocking=False)`
        # succeeding proves it was FREE — which is the bug we're guarding against.
        got = self._owner._lock.acquire(blocking=False)
        if got:
            self._owner._lock.release()
            raise AssertionError(
                "_recorded_from touched without holding GhClient._lock — the "
                "collision guard's check-and-set is racy under the fetch pool")

    def get(self, *a, **k):
        self._assert_locked()
        return super().get(*a, **k)

    def setdefault(self, *a, **k):
        self._assert_locked()
        return super().setdefault(*a, **k)

    def __setitem__(self, k, v):
        self._assert_locked()
        return super().__setitem__(k, v)

    def __delitem__(self, k):
        self._assert_locked()
        return super().__delitem__(k)


def test_recorded_from_check_and_set_is_lock_guarded(tmp_path, monkeypatch):
    monkeypatch.delenv("CI_SPEEDUP_GH_FIXTURES", raising=False)
    monkeypatch.setenv("CI_SPEEDUP_GH_RECORD", str(tmp_path))
    c = cr.GhClient()
    c._recorded_from = _LockAssertingDict(c)
    c._record("repos/o/r/actions/runs/1/jobs", "json", '{"jobs": []}')
    c._record("repos/o/r/actions/runs/2/jobs", "json", '{"jobs": []}')
    assert (tmp_path / cr._fixture_name("repos/o/r/actions/runs/1/jobs", "json")).exists()


# NOTE (merge #215↔#212): two former tests here asserted #215's WARN-based, setdefault-
# race-free `_record` (`test_two_threads_recording_COLLIDING_endpoints_warn_exactly_once`
# and `test_record_mode_still_warns_on_a_collision_under_the_lock`). The merge adopts
# main's `_record`, which RAISES on a collision rather than warning (and `_fixture_name`
# now spells the operators `gte`/`lte`, so `created>=X` and `created<=X` no longer collide
# at all — the old premise). Both tests are therefore superseded; the merged raise-based
# behavior is covered by `test_offline_pipeline_e2e.test_record_mode_RAISES_on_a_lossy_
# fixture_name_collision`. Concurrent recording of DISTINCT endpoints is still guarded
# below.


def test_concurrent_recording_does_not_corrupt_the_collision_index(tmp_path, monkeypatch):
    # Record from many threads at once (the shared fetch pool's real shape) and demand
    # the index ends up complete and consistent.
    monkeypatch.delenv("CI_SPEEDUP_GH_FIXTURES", raising=False)
    monkeypatch.setenv("CI_SPEEDUP_GH_RECORD", str(tmp_path))
    c = cr.GhClient()
    endpoints = [f"repos/o/r/actions/runs/{i}/jobs" for i in range(64)]

    def rec(e):
        c._record(e, "json", "{}")

    threads = [threading.Thread(target=rec, args=(e,)) for e in endpoints]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(c._recorded_from) == 64
    assert set(c._recorded_from.values()) == set(endpoints)
