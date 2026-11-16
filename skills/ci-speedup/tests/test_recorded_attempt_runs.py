"""The `filter=latest` derivation, checked against RECORDED REAL GitHub payloads.

`collect_runs._latest_attempt_jobs` claims it can reproduce REST's server-side
`filter=latest` from the `filter=all` payload the pipeline already has, and the
pipeline drops a gh call per attempt-run on the strength of that claim. A test whose
expectation RE-IMPLEMENTS the derivation's own predicate cannot falsify that claim —
it passes for every input, including a wrong implementation. So the oracle here is a
payload GitHub's server actually produced.

`fixtures/gh_recorded/` holds, for two real runs, the response to BOTH
`GET /repos/{repo}/actions/runs/{id}/jobs?per_page=100&filter=all` and the same call
with `filter=latest`, plus the run object. Recorded live on 2026-07-11 with `gh api`.
The only edit is that each job's `steps` array is dropped (it is large and no code on
this path reads it); every other field is verbatim, including the `run_attempt`,
`id`, `status`, `conclusion` and timestamps the derivation and OPT64 consume.

The two runs are chosen to pin the two things that can go wrong:

  * dbt-labs/dbt-core run 29147972600 — a PARTIAL re-run ("Re-run failed jobs"), 3
    attempts, 24 jobs per attempt, 72 total, page NOT truncated. This settles the
    question the derivation actually rests on. GitHub materializes the FULL job graph
    into every attempt: a job that was NOT re-executed still appears under the new
    attempt with a NEW job id, the NEW `run_attempt`, and its ORIGINAL timestamps
    (`aggregate-release-data` runs 09:35:24 -> 09:35:42 and carries those exact
    timestamps in attempts 1, 2 AND 3). There is no such thing as a carried-over job
    that still says `run_attempt: 1` while the run says 2 — so `filter=latest` really
    is "the jobs stamped with the run's attempt", on partial re-runs as on re-run-all.

  * dbt-labs/dbt-core run 29121623799 — attempt 2, 228 jobs across attempts. The
    `filter=all` page is TRUNCATED at 100 and every one of those 100 jobs is from
    attempt 1. A derivation that trusts the payload here returns ZERO latest-attempt
    jobs while REST returns 114 — and every job on the page carries `run_attempt`, so
    a "missing basis" guard does not trip. That empty set silently disables OPT64 on
    exactly the big-matrix repos where re-run waste costs the most.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parents[1]
_SCRIPTS = _SKILL_DIR / "scripts"
_RECORDED = Path(__file__).resolve().parent / "fixtures" / "gh_recorded"

sys.path.insert(0, str(_SCRIPTS))
import collect_runs as cr  # noqa: E402

# A PARTIAL re-run (3 attempts, 72 jobs, page complete) and a TRUNCATED big-matrix
# attempt-run (attempt 2, 228 jobs, page 1 = 100 jobs all from attempt 1).
_PARTIAL_RERUN = "dbt-core_run29147972600"
_TRUNCATED = "dbt-core_run29121623799"


def _recorded_doc(stem: str, kind: str) -> dict:
    """A recorded payload, WHOLE — `total_count` included. This is what the fetchers see,
    and `total_count` is what tells a full page apart from a truncated one."""
    return json.loads((_RECORDED / f"{stem}_{kind}.json").read_text(encoding="utf-8"))


def _recorded(stem: str, kind: str):
    """A recorded payload shaped as the pipeline consumes it: the run object, or the
    jobs list tagged with its truncation via `collect_runs._jobs_payload`. NB post-#212
    the production fetchers PAGINATE to completion and return `truncated=False`; the
    single-page `_jobs_payload` shape is kept here to exercise the truncation guards
    in isolation against real recorded payloads."""
    doc = _recorded_doc(stem, kind)
    return doc if kind == "run" else cr._jobs_payload(doc)


def _identity(jobs) -> list[tuple]:
    """The job fields the pipeline actually consumes, in payload order — what "the same
    set of jobs" means for a comparison against a server response."""
    return [(j.get("id"), j.get("name"), j.get("run_attempt"), j.get("status"),
             j.get("conclusion"), j.get("started_at"), j.get("completed_at"))
            for j in jobs]


# --- the recordings are what this file says they are -------------------------
# If a future maintainer re-records these fixtures against a run that no longer has the
# shape the tests below depend on, the tests would go green for the wrong reason. Pin
# the shape first, so the corpus can't silently stop testing anything.

def test_the_partial_rerun_recording_really_is_a_partial_rerun():
    run = _recorded(_PARTIAL_RERUN, "run")
    all_jobs = _recorded(_PARTIAL_RERUN, "jobs_filter_all")
    assert run["run_attempt"] == 3
    assert len(all_jobs) == 72 < cr._JOBS_PAGE_SIZE, "page must be COMPLETE, not truncated"
    assert sorted({j["run_attempt"] for j in all_jobs}) == [1, 2, 3]

    # The signature of a PARTIAL re-run: a job that appears under the later attempts
    # with its ORIGINAL timestamps — it was never re-executed, only carried forward.
    by_attempt = {j["run_attempt"]: j for j in all_jobs
                  if j["name"] == "aggregate-release-data"}
    assert set(by_attempt) == {1, 2, 3}
    assert (by_attempt[1]["started_at"] == by_attempt[2]["started_at"]
            == by_attempt[3]["started_at"]), (
        "the carried-over job's timestamps differ across attempts — this recording is a "
        "re-run-ALL, not the partial re-run the derivation's correctness turns on")
    # ...and GitHub gave each carried-forward copy its own job id, re-stamped with the
    # new attempt. THIS is why the derivation works: there is no carried-over job left
    # behind at `run_attempt: 1` for `filter=latest` to include and the derivation to miss.
    assert len({by_attempt[1]["id"], by_attempt[2]["id"], by_attempt[3]["id"]}) == 3


def test_the_truncated_recording_really_is_truncated():
    run = _recorded(_TRUNCATED, "run")
    all_jobs = _recorded(_TRUNCATED, "jobs_filter_all")
    latest_jobs = _recorded(_TRUNCATED, "jobs_filter_latest")
    assert run["run_attempt"] == 2
    assert len(all_jobs) == cr._JOBS_PAGE_SIZE, "the filter=all page must be FULL"
    # The trap: the whole page is prior-attempt jobs (filter=all is oldest-attempt-first
    # and the endpoint is not paginated), yet every job HAS a run_attempt — so a
    # "missing basis" guard sails straight past it.
    assert {j["run_attempt"] for j in all_jobs} == {1}
    assert all(j.get("run_attempt") is not None for j in all_jobs)
    # ...while the server's own filter=latest answer is emphatically not empty.
    assert len(latest_jobs) == cr._JOBS_PAGE_SIZE
    assert {j["run_attempt"] for j in latest_jobs} == {2}


# --- the derivation, against the server's own answer -------------------------

def test_derived_latest_equals_the_recorded_filter_latest_on_a_partial_rerun():
    """The load-bearing claim: the derivation reproduces REST's `filter=latest`.

    The expectation is the RECORDED `filter=latest` response — not a re-statement of
    the derivation's predicate. If `_latest_attempt_jobs` ever selects a different set
    (wrong attempt key, prior-attempt leakage, dropped carried-over jobs), this is what
    catches it."""
    run = _recorded(_PARTIAL_RERUN, "run")
    all_jobs = _recorded(_PARTIAL_RERUN, "jobs_filter_all")
    rest_latest = _recorded(_PARTIAL_RERUN, "jobs_filter_latest")

    derived = cr._latest_attempt_jobs(run, all_jobs)
    assert derived is not None, (
        "a complete 72-job payload of a 3-attempt run is decidable — the derivation "
        "must not punt it to a second fetch")
    assert _identity(derived) == _identity(rest_latest), (
        "the derived latest-attempt job set is NOT what REST's server-side "
        "`filter=latest` returned for this run")
    # And it is a real filter: two thirds of the payload are prior-attempt jobs.
    assert len(derived) == 24 and len(all_jobs) == 72

    # The prior-attempt subtraction OPT64 sizes is unaffected by deriving rather than
    # fetching — same inputs, same 48 prior-attempt jobs.
    prior = cr._prior_attempt_jobs(run, all_jobs, derived)
    assert len(prior) == 48
    assert {j["run_attempt"] for j in prior} == {1, 2}


def test_derived_latest_is_UNKNOWN_not_empty_on_a_truncated_page():
    """The false-negative class the truncation guard closes.

    Without it, the derivation returns `[]` here — a real, confident-looking answer
    that says "this run's latest attempt ran no jobs". `_dominant_prior_failing_job`
    builds its `latest_keys` from that set and withholds when it is empty, so OPT64
    can NEVER fire on a >100-job attempt-run: re-run waste goes silently unreported on
    precisely the big-matrix repos where it is most expensive.

    The honest answer is UNKNOWN (None), which routes the run to the explicit
    `filter=latest` fetch — the one the server answers with 114 jobs, not 0."""
    run = _recorded(_TRUNCATED, "run")
    all_jobs = _recorded(_TRUNCATED, "jobs_filter_all")
    rest_latest = _recorded(_TRUNCATED, "jobs_filter_latest")

    assert cr._latest_attempt_jobs(run, all_jobs) is None, (
        "a TRUNCATED filter=all page must be UNKNOWN, not an answer")

    # Concretely: what the unguarded derivation would have produced, and what the
    # server actually says. These are not the same fact, and the gap is the bug.
    naive = [j for j in all_jobs if j.get("run_attempt") == run.get("run_attempt")]
    assert naive == []
    assert len(rest_latest) > 0

    # ...and because it is None, `_attempt_job_samples` re-fetches, and OPT64's gate
    # (a non-empty latest set) is reachable again.
    fetched: list[int] = []

    def _fake_latest_fetch(_client, _repo, run_id):
        fetched.append(run_id)
        return rest_latest

    orig = cr._fetch_run_jobs_latest_attempt
    cr._fetch_run_jobs_latest_attempt = _fake_latest_fetch
    try:
        samples, failures = cr._attempt_job_samples(
            object(), "dbt-labs/dbt-core", [(run, all_jobs)])
    finally:
        cr._fetch_run_jobs_latest_attempt = orig

    assert fetched == [run["id"]], "the truncated run must fall back to the REST fetch"
    assert failures == 0
    assert len(samples) == 1
    _run, _all, latest = samples[0]
    assert _identity(latest) == _identity(rest_latest)
    # The gate that was structurally unreachable before: latest_keys is now non-empty.
    assert {cr._attempt_job_key(j) for j in latest if cr._attempt_job_key(j)}


def test_a_truncated_run_yields_NO_prior_attempt_set_not_a_short_one():
    """The other half of the truncation rule, and the one round 1 left open.

    On this recorded run, BOTH payloads are truncated: `filter=all` returns 100 of 228,
    `filter=latest` returns 100 of 114. So neither the prior-attempt set NOR the latest
    key set can be built. The failure mode that matters is not that OPT64 goes quiet —
    it is that OPT64 speaks CONFIDENTLY off a short sample:

      * the derived prior set is 100 of the 114 real attempt-1 jobs, so re-run waste is
        sized against a partial set;
      * `_dominant_prior_failing_job` runs a "unique top failing job" contest over that
        partial set, so a job can WIN it only because the true dominant job is among the
        14 the page cut off — a WRONG root cause, attributed with full confidence;
      * `latest_keys` is likewise short, so a prior failing job that IS in the latest
        attempt can look absent and be withheld.

    Every job on both pages carries `run_attempt`, so a "missing basis" guard does not
    trip. The oracle here is the recorded server payload's own `total_count`, not a
    restatement of the guard: REST says 228 and 114; the pages hold 100 and 100."""
    run = _recorded(_TRUNCATED, "run")
    all_jobs = _recorded(_TRUNCATED, "jobs_filter_all")
    rest_latest = _recorded(_TRUNCATED, "jobs_filter_latest")

    # The server itself says both pages are short — that is the whole basis.
    assert _recorded_doc(_TRUNCATED, "jobs_filter_all")["total_count"] == 228
    assert _recorded_doc(_TRUNCATED, "jobs_filter_latest")["total_count"] == 114
    assert all_jobs.truncated and rest_latest.truncated
    assert len(all_jobs) == len(rest_latest) == cr._JOBS_PAGE_SIZE

    # What the unguarded code produced: a 100-job "prior attempt" set — every job on the
    # page, because page 1 is entirely attempt 1 — presented as complete. It is not:
    # attempt 1 alone really had 114 jobs.
    naive = [j for j in all_jobs if j.get("run_attempt") < run["run_attempt"]]
    assert len(naive) == 100

    assert cr._prior_attempt_jobs(run, all_jobs, rest_latest) == [], (
        "a truncated payload yielded a CONFIDENT prior-attempt set — OPT64 would size "
        "re-run waste against 100 of 114 attempt-1 jobs and could crown the wrong "
        "dominant failing job")

    # ...and OPT64 therefore emits nothing for this run: UNKNOWN, not a wrong number.
    assert cr._detect_opt64_rerun_attempt_waste(
        ".github/workflows/main.yml", [(run, all_jobs, rest_latest)],
        100, 100, 0) == []

    # The COMPLETE recording is unaffected — the guard fires on truncation, not on size.
    ok_run = _recorded(_PARTIAL_RERUN, "run")
    ok_all = _recorded(_PARTIAL_RERUN, "jobs_filter_all")
    ok_latest = _recorded(_PARTIAL_RERUN, "jobs_filter_latest")
    assert not ok_all.truncated and not ok_latest.truncated
    assert len(cr._prior_attempt_jobs(ok_run, ok_all, ok_latest)) == 48


def test_the_truncation_guard_cannot_drift_from_the_per_page_it_guards():
    """`_JOBS_PAGE_SIZE` is the page size AND the fallback truncation threshold, so the
    jobs URLs must INTERPOLATE it rather than re-type `100`.

    With the literal hardcoded in the URL, dropping `per_page` to 50 would leave
    `len(jobs) >= _JOBS_PAGE_SIZE` comparing against 100: the guard silently stops
    firing on every truncated page while still LOOKING correct, and the confident-off-a-
    short-sample false negative comes straight back. The oracle is the URL the fetcher
    actually asks for."""
    asked: list[str] = []

    class _Recorder:
        queries = errors = 0

        def json(self, endpoint, allow_missing=False):
            asked.append(endpoint)
            return {"total_count": 0, "jobs": []}

    client = _Recorder()
    cr._fetch_run_jobs(client, "o/r", 1)
    cr._fetch_run_jobs_all_attempts(client, "o/r", 1)
    cr._fetch_run_jobs_latest_attempt(client, "o/r", 1)

    assert len(asked) == 3
    for endpoint in asked:
        assert f"per_page={cr._JOBS_PAGE_SIZE}" in endpoint, (
            f"the jobs fetch asks for a page size the truncation guard does not know "
            f"about: {endpoint}")


def test_a_complete_payload_costs_no_second_fetch():
    """The saving is real, and conditional on decidability: the complete (partial-rerun)
    payload is derived with ZERO extra calls, while the truncated one pays for one. Both
    behaviours in one place, so neither can drift into the other unnoticed."""
    calls: list[int] = []

    def _counting_fetch(_client, _repo, run_id):
        calls.append(run_id)
        return _recorded(_TRUNCATED, "jobs_filter_latest")

    complete_run = _recorded(_PARTIAL_RERUN, "run")
    complete_all = _recorded(_PARTIAL_RERUN, "jobs_filter_all")
    trunc_run = _recorded(_TRUNCATED, "run")
    trunc_all = _recorded(_TRUNCATED, "jobs_filter_all")

    orig = cr._fetch_run_jobs_latest_attempt
    cr._fetch_run_jobs_latest_attempt = _counting_fetch
    try:
        samples, failures = cr._attempt_job_samples(
            object(), "dbt-labs/dbt-core",
            [(complete_run, complete_all), (trunc_run, trunc_all)])
    finally:
        cr._fetch_run_jobs_latest_attempt = orig

    assert failures == 0
    assert calls == [trunc_run["id"]], (
        "exactly one second fetch: the decidable payload must not pay for one, and the "
        f"truncated one must (got {calls})")
    # Input order preserved, both runs present.
    assert [s[0]["id"] for s in samples] == [complete_run["id"], trunc_run["id"]]


# --- the success-sample derivation, against the server's own status=success filter ----

def test_derived_success_sample_matches_the_real_status_success_endpoint():
    """`_success_runs_from_all_status` claims the `status=success` page is derivable from
    the all-status page, and the pipeline drops a run-list query per workflow on it.

    Checked against a REAL pair recorded from better-auth/better-auth's `adapter-tests`
    workflow (id 206130094) on 2026-07-11: the unfiltered 100-run page, and the response
    to the same query with `status=success&per_page=20`. Both are projected to the run
    fields the pipeline reads (the raw all-status page is 1.3 MB), identically on both
    sides — so the comparison of ids and order is faithful.

    The offline e2e pins the same property against the synthetic corpus; this pins it
    against a real busy workflow, where the page holds 43 non-successes for the filter
    to remove and the ordering is GitHub's, not a fixture author's."""
    all_status = json.loads(
        (_RECORDED / "better-auth_wf206130094_runs_all_status.json").read_text(
            encoding="utf-8"))["workflow_runs"]
    rest_success = json.loads(
        (_RECORDED / "better-auth_wf206130094_runs_status_success.json").read_text(
            encoding="utf-8"))["workflow_runs"]

    assert len(all_status) == 100 and len(rest_success) == 20
    non_success = [r for r in all_status
                   if not (r["status"] == "completed" and r["conclusion"] == "success")]
    assert len(non_success) == 43, (
        "the recorded page must hold real non-successes, or this oracle would pass on a "
        "derivation that did no filtering at all")

    derived = cr._success_runs_from_all_status(all_status, 20)
    assert [r["id"] for r in derived] == [r["id"] for r in rest_success], (
        "the derived success sample is not the run set REST's server-side "
        "`status=success` filter returned for this workflow")
    assert derived == rest_success
