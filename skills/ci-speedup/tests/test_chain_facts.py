"""ENG-1 PR-N1 contract: per-PR chain timing facts (decision table, written red-first).

The wall-clock spine's gate model assumes every check on a PR runs
concurrently; GitHub serializes jobs wired with `needs:`. PR-N1 stamps the
per-PR chain TIMING facts (`pr_critical_path.chain_facts`) without changing
any gate/render behavior. This file is the plan's §3 N1 decision table
(`maintainers/ci-speedup/specs/eng1-needs-aware-wall-clock.md`) as failing
tests first — the graph cells are where PR-G2-class bugs live.

| cell | input state | required behavior |
| 1 | no `needs:` anywhere | chain = slowest check; equals today's argmax |
| 2 | linear chain | chain = predecessor + dependent, sum of CAPPED spans |
| 3 | `needs:` onto a matrix job | edge binds all legs; slowest leg carries the node |
| 4 | fileless / unresolvable check | parallel peer (its own single-member path) |
| 5 | check name ↔ job-id mismatch | resolved via the existing display-name/template mapping |
| 6 | skipped/absent predecessor | contributes its observed span — 0 when absent |
| 7 | unresolvable graph | a CYCLE fails open for THAT workflow + stamped reason; a parse-failed workflow has no graph entry (checks become cell-4 peers, nothing to stamp); reusable-caller children collapse to the slowest child on the caller node (as-built narrowing, recorded in the plan) |
| 8 | same check name in two workflows | keyed (workflow, job) — no cross-workflow node merge |
| 9 | multi-parent fan-in (`needs: [a, b]`) | starts after the LAST parent; longest path wins; co-longest both counted |
| 10 | unobserved DEPENDENT extends the top path | zero-weight, member-identical — the same physical wait, never a second counted path |

Makespan (OD-E1): latest-attempt check-run intervals, per-check span-capped —
raw-timestamp arithmetic is banned (the 80s-job/1871s-check-run inflation).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import collect_runs as cr  # noqa: E402


def _crit(wf_jobs: dict[str, dict[str, float]]) -> dict[str, dict]:
    """crit_by_wf shaped for `_map_check_to_job`: {wf: {"job_p50": {...}}}."""
    return {wf: {"job_p50": dict(jobs)} for wf, jobs in wf_jobs.items()}


def _facts(checks, caps, graph, crit):
    return cr._chain_facts_for_pr(checks, caps, graph, crit)


# --- cell 1 — no needs anywhere: chain == today's argmax ----------------------

def test_cell1_no_needs_equals_slowest_check():
    graph = {"ci.yml": {"a": {"needs": []}, "b": {"needs": []}}}
    crit = _crit({"ci.yml": {"a": 100.0, "b": 60.0}})
    f = _facts({"a": 100.0, "b": 60.0}, {}, graph, crit)
    assert f["chain"] == ["a"]
    assert f["chain_s"] == 100.0
    assert f["member_spans_s"] == {"a": 100.0}
    assert f["co_longest_n"] == 1
    assert f["fallback"] is None


# --- cell 2 — linear chain, capped spans --------------------------------------

def test_cell2_linear_chain_sums_capped_spans():
    graph = {"ci.yml": {"compile": {"needs": []}, "test": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 38.0, "test": 66.0}})
    f = _facts({"compile": 38.0, "test": 66.0}, {}, graph, crit)
    assert f["chain"] == ["compile", "test"]
    assert f["chain_s"] == 104.0
    assert f["member_spans_s"] == {"compile": 38.0, "test": 66.0}

    # The cap de-inflates a member's span exactly like the pole/populations
    # pipeline (same `_pole_caps` values) — never the raw check-run span.
    f = _facts({"compile": 38.0, "test": 300.0}, {"test": 66.0}, graph, crit)
    assert f["member_spans_s"]["test"] == 66.0
    assert f["chain_s"] == 104.0


# --- cell 3 — needs onto a matrix job: slowest leg carries the node -----------

def test_cell3_needs_onto_matrix_waits_for_slowest_leg():
    graph = {"ci.yml": {
        "unit": {"needs": [], "name": "unit", "matrix": {"part": ["x", "y"]}},
        "pack": {"needs": ["unit"], "name": "pack"},
    }}
    crit = _crit({"ci.yml": {"unit (x)": 30.0, "unit (y)": 45.0, "pack": 20.0}})
    f = _facts({"unit (x)": 30.0, "unit (y)": 45.0, "pack": 20.0}, {}, graph, crit)
    assert f["chain"] == ["unit (y)", "pack"], (
        "fan-in waits for the LAST leg — the slowest leg carries the matrix node")
    assert f["chain_s"] == 65.0


# --- cell 4 — fileless / unresolvable check stays a parallel peer -------------

def test_cell4_fileless_check_is_its_own_path():
    graph = {"ci.yml": {"compile": {"needs": []}, "test": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 30.0, "test": 25.0}})
    # The external check outweighs the 55s chain: it must win as a singleton.
    f = _facts({"compile": 30.0, "test": 25.0, "External Bot": 90.0}, {}, graph, crit)
    assert f["chain"] == ["External Bot"]
    assert f["chain_s"] == 90.0
    # And when the chain outweighs it, the chain wins.
    f = _facts({"compile": 30.0, "test": 25.0, "External Bot": 40.0}, {}, graph, crit)
    assert f["chain"] == ["compile", "test"]


# --- cell 5 — display-name resolution (check name != job id) ------------------

def test_cell5_display_name_resolves_to_job_id():
    graph = {"ci.yml": {
        "c": {"needs": [], "name": "Compile Step"},
        "t": {"needs": ["c"], "name": "Test Suite"},
    }}
    crit = _crit({"ci.yml": {"Compile Step": 30.0, "Test Suite": 70.0}})
    f = _facts({"Compile Step": 30.0, "Test Suite": 70.0}, {}, graph, crit)
    assert f["chain"] == ["Compile Step", "Test Suite"]
    assert f["chain_s"] == 100.0


# --- cell 6 — absent predecessor contributes zero -----------------------------

def test_cell6_absent_predecessor_contributes_zero():
    graph = {"ci.yml": {"compile": {"needs": []}, "test": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 38.0, "test": 66.0}})
    f = _facts({"test": 66.0}, {}, graph, crit)
    assert f["chain"] == ["test"], "an unobserved predecessor is not invented"
    assert f["chain_s"] == 66.0


# --- cell 7 — cycle fails open for THAT workflow, with a stamped reason -------

def test_cell7_cycle_falls_open_with_reason():
    graph = {
        "bad.yml": {"a": {"needs": ["b"]}, "b": {"needs": ["a"]}},
        "ok.yml": {"x": {"needs": []}, "y": {"needs": ["x"]}},
    }
    crit = _crit({"bad.yml": {"a": 50.0, "b": 40.0},
                  "ok.yml": {"x": 10.0, "y": 20.0}})
    f = _facts({"a": 50.0, "b": 40.0, "x": 10.0, "y": 20.0}, {}, graph, crit)
    # bad.yml reverts to today's model (its checks compete as singletons) and
    # the reason is stamped; ok.yml still chains.
    assert f["fallback"] == {"bad.yml": "needs cycle"}
    assert f["chain"] == ["a"], "cycle workflow's checks compete as singletons"
    assert f["chain_s"] == 50.0


# --- cell 8 — same check name in two workflows never merges nodes -------------

def test_cell8_same_name_two_workflows_keyed_per_workflow():
    graph = {
        "one.yml": {"build": {"needs": []}},
        "two.yml": {"setup": {"needs": []}, "build": {"needs": ["setup"]}},
    }
    # The sampled-timing anchor picks the slowest exact match (one.yml); the
    # other workflow's `setup` edge must not leak onto it.
    crit = _crit({"one.yml": {"build": 80.0}, "two.yml": {"build": 30.0, "setup": 10.0}})
    f = _facts({"build": 80.0}, {}, graph, crit)
    assert f["chain"] == ["build"]
    assert f["chain_s"] == 80.0


# --- cell 9 — multi-parent fan-in: last parent gates, longest path wins -------

def test_cell9_multi_parent_fan_in_longest_path_wins():
    graph = {"ci.yml": {
        "a": {"needs": []}, "b": {"needs": []}, "c": {"needs": ["a", "b"]},
    }}
    crit = _crit({"ci.yml": {"a": 40.0, "b": 25.0, "c": 30.0}})
    f = _facts({"a": 40.0, "b": 25.0, "c": 30.0}, {}, graph, crit)
    assert f["chain"] == ["a", "c"]
    assert f["chain_s"] == 70.0
    assert f["co_longest_n"] == 1


def test_cell9_co_longest_paths_are_both_counted():
    graph = {"ci.yml": {
        "a": {"needs": []}, "b": {"needs": []}, "c": {"needs": ["a", "b"]},
    }}
    crit = _crit({"ci.yml": {"a": 25.0, "b": 25.0, "c": 30.0}})
    f = _facts({"a": 25.0, "b": 25.0, "c": 30.0}, {}, graph, crit)
    assert f["chain_s"] == 55.0
    assert f["co_longest_n"] == 2, (
        "co-longest competing paths are BOTH counted — the same both-counted "
        "principle _pole_frequencies applies to co-slowest checks")
    assert f["chain"] in (["a", "c"], ["b", "c"])  # deterministic representative
    assert f["chain"] == ["a", "c"], "ties break deterministically (lexicographic)"


# --- cell 10 — an unobserved DEPENDENT is not a distinct competing path --------

def test_cell10_unobserved_dependent_does_not_duplicate_the_path():
    # The deepgram flagship shape: `publish: needs [compile, test]` never runs
    # on a PR. Its zero-weight extension of the top path has IDENTICAL members
    # — the same physical wait, not a competing path. co_longest_n must be 1.
    graph = {"ci.yml": {
        "compile": {"needs": []},
        "test": {"needs": ["compile"]},
        "publish": {"needs": ["compile", "test"]},
    }}
    crit = _crit({"ci.yml": {"compile": 38.0, "test": 66.0}})
    f = _facts({"compile": 38.0, "test": 66.0}, {}, graph, crit)
    assert f["chain"] == ["compile", "test"]
    assert f["chain_s"] == 104.0
    assert f["co_longest_n"] == 1, (
        "an unobserved dependent extended the top path by zero and got "
        "counted as a second physical path")


def test_cell10_genuine_tie_plus_unobserved_dependent_counts_two_not_four():
    graph = {"ci.yml": {
        "a": {"needs": []}, "b": {"needs": []}, "c": {"needs": ["a", "b"]},
        "deploy": {"needs": ["c"]},   # unobserved zero-weight extension
    }}
    crit = _crit({"ci.yml": {"a": 25.0, "b": 25.0, "c": 30.0}})
    f = _facts({"a": 25.0, "b": 25.0, "c": 30.0}, {}, graph, crit)
    assert f["chain_s"] == 55.0
    assert f["co_longest_n"] == 2, (
        "the a/b tie is two physical paths; the unobserved deploy extension "
        "must not double them to four")


def test_cell10_unobserved_parent_tie_is_one_path():
    # a → y (unobserved), c needs [a, y]: both parent legs resolve to the same
    # observed members ([a]) — one physical path, not a tie of two.
    graph = {"ci.yml": {
        "a": {"needs": []}, "y": {"needs": ["a"]}, "c": {"needs": ["a", "y"]},
    }}
    crit = _crit({"ci.yml": {"a": 40.0, "c": 30.0}})
    f = _facts({"a": 40.0, "c": 30.0}, {}, graph, crit)
    assert f["chain"] == ["a", "c"]
    assert f["chain_s"] == 70.0
    assert f["co_longest_n"] == 1


# --- degenerate input ----------------------------------------------------------

def test_no_positive_spans_returns_none():
    assert _facts({}, {}, {}, {}) is None
    assert _facts({"a": 0.0}, {}, {}, {}) is None


def test_no_graph_at_all_is_cell1():
    f = _facts({"a": 100.0, "b": 60.0}, {}, None, {})
    assert f["chain"] == ["a"] and f["chain_s"] == 100.0 and f["fallback"] is None


# --- makespan: latest-attempt intervals, span-capped ---------------------------

def test_makespan_spans_min_start_to_max_end():
    iv = {"a": ("2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"),
          "b": ("2026-01-01T00:00:30Z", "2026-01-01T00:02:10Z")}
    assert cr._pr_makespan(iv, {}) == 130.0


def test_makespan_caps_each_interval_before_the_span():
    # The 80s-job/1871s-check-run inflation: the interval is clamped to the
    # check's cap BEFORE the makespan is taken — raw-timestamp arithmetic banned.
    iv = {"a": ("2026-01-01T00:00:00Z", "2026-01-01T00:31:11Z")}
    assert cr._pr_makespan(iv, {"a": 80.0}) == 80.0


def test_makespan_empty_is_none():
    assert cr._pr_makespan({}, {}) is None


# --- ENG-1 PR-N2: runner-up path + chain summary (contract-first) --------------
# N2's headline win derives from "a member's own span, bounded by the
# next-longest competing path" — that bound is `runner_up_s`, the second-best
# DISTINCT-member path score (0.0 when nothing competes). `_chain_summary`
# reduces the per-PR facts to the render-consumable aggregate the verifier
# re-derives.

def test_runner_up_is_the_next_longest_competing_path():
    graph = {"ci.yml": {"compile": {"needs": []}, "test": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 30.0, "test": 25.0}})
    f = _facts({"compile": 30.0, "test": 25.0, "External Bot": 40.0}, {}, graph, crit)
    assert f["chain"] == ["compile", "test"] and f["chain_s"] == 55.0
    assert f["runner_up_s"] == 40.0, "the external peer is the competing path"
    assert f["chain_win_s"] == 15.0, "per-PR win = chain_s - runner_up_s"


def test_runner_up_is_the_zeroed_graph_wait_on_diamonds():
    # Fan-in diamond (pass-A probe): b needs [a, x]. The runner-up is the wait
    # WITH THE CHAIN MEMBERS ZEROED — the whole-chain bound. Zeroing a and b
    # leaves the x path at 30 (x's own span; b contributes nothing), NOT the
    # 40s external peer alone and NEVER a stale full x->b path.
    graph = {"ci.yml": {"a": {"needs": []}, "x": {"needs": []},
                        "b": {"needs": ["a", "x"]}}}
    crit = _crit({"ci.yml": {"a": 38.0, "x": 30.0, "b": 66.0}})
    f = _facts({"a": 38.0, "x": 30.0, "b": 66.0}, {}, graph, crit)
    assert f["chain"] == ["a", "b"] and f["chain_s"] == 104.0
    assert f["runner_up_s"] == 30.0
    assert f["chain_win_s"] == 74.0
    # With a slower external peer, the peer is the remaining wait instead.
    f = _facts({"a": 38.0, "x": 30.0, "b": 66.0, "External Bot": 40.0}, {}, graph, crit)
    assert f["runner_up_s"] == 40.0


def test_runner_up_zeroes_shared_members_of_competing_paths():
    # A competitor sharing a chain member (compile->lint beside compile->test):
    # zeroing the chain's members leaves only lint's own span as the bound.
    graph = {"ci.yml": {"compile": {"needs": []},
                        "test": {"needs": ["compile"]},
                        "lint": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 38.0, "test": 66.0, "lint": 30.0}})
    f = _facts({"compile": 38.0, "test": 66.0, "lint": 30.0}, {}, graph, crit)
    assert f["chain"] == ["compile", "test"] and f["chain_s"] == 104.0
    assert f["runner_up_s"] == 30.0, "compile is zeroed - only lint's own span remains"


def test_runner_up_floored_at_population_p50_of_competing_pole():
    # #45 electron: a SINGLE sampled PR whose competing path (`win-rspec`) ran
    # 4640s — BELOW its 4761s population p50 (`caps`) — must not inflate the win.
    # The runner-up floors at the population p50 leg, so the win comes out
    # 5056-4761 = 295s (4m55s), never the single-PR 5056-4640 = 416s (the ~6m56s
    # claim). This p50 runner-up floor moves the win toward — not all the way to —
    # the ~3m29s the report's own OPT25 co-occurrence finding on the same job
    # implies (that tighter co-occurrence floor is a separate downstream bound).
    graph = {"ci.yml": {"build": {"needs": []}, "test": {"needs": ["build"]}}}
    crit = _crit({"ci.yml": {"build": 1000.0, "test": 4056.0}})
    caps = {"win-rspec": 4761.0}
    f = _facts({"build": 1000.0, "test": 4056.0, "win-rspec": 4640.0}, caps, graph, crit)
    assert f["chain"] == ["build", "test"] and f["chain_s"] == 5056.0
    assert f["runner_up_s"] == 4761.0, "runner-up floored UP to the population p50 leg"
    assert f["chain_win_s"] == 295.0, "win = chain_s - floored runner-up (never 416)"


def test_runner_up_floor_never_raises_the_win_without_caps():
    # The floor only ever RAISES the runner-up (lowers the win); with no caps
    # (the caps={} chainless/legacy path) it is a strict no-op — byte-stable.
    graph = {"ci.yml": {"compile": {"needs": []}, "test": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 30.0, "test": 25.0}})
    f = _facts({"compile": 30.0, "test": 25.0, "External Bot": 40.0}, {}, graph, crit)
    assert f["runner_up_s"] == 40.0 and f["chain_win_s"] == 15.0


def test_runner_up_floor_excludes_zeroed_chain_members_on_a_diamond():
    # #45 fan-in diamond, WITH populated caps (the real pipeline always passes
    # them). b needs [a, x]; chain [a, b], chain_s 104. The competing path [x, b]
    # reaches the chain leaf `b` via `x`, so its members list still carries `b`
    # (span zeroed). The p50 floor must draw ONLY on the surviving path's own legs
    # (x=30), NOT re-introduce caps[b]=66 — the p50 of the very node being fixed —
    # which would self-floor the competitor and understate the win 74 -> 38.
    graph = {"ci.yml": {"a": {"needs": []}, "x": {"needs": []},
                        "b": {"needs": ["a", "x"]}}}
    crit = _crit({"ci.yml": {"a": 38.0, "x": 30.0, "b": 66.0}})
    caps = {"a": 38.0, "x": 30.0, "b": 66.0}   # b is the zeroed chain leaf
    f = _facts({"a": 38.0, "x": 30.0, "b": 66.0}, caps, graph, crit)
    assert f["chain"] == ["a", "b"] and f["chain_s"] == 104.0
    assert f["runner_up_s"] == 30.0, "floor draws on x's own leg (30), never zeroed b's cap (66)"
    assert f["chain_win_s"] == 74.0, "win = 104 - 30, not the self-floored 104 - 66 = 38"


def test_runner_up_zero_when_nothing_competes():
    graph = {"ci.yml": {"compile": {"needs": []}, "test": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 38.0, "test": 66.0}})
    f = _facts({"compile": 38.0, "test": 66.0}, {}, graph, crit)
    assert f["runner_up_s"] == 0.0


def test_runner_up_ignores_member_identical_extensions():
    # The cell-10 duplicate is the SAME physical wait — it must not masquerade
    # as a competing runner-up either.
    graph = {"ci.yml": {
        "compile": {"needs": []},
        "test": {"needs": ["compile"]},
        "publish": {"needs": ["compile", "test"]},
    }}
    crit = _crit({"ci.yml": {"compile": 38.0, "test": 66.0}})
    f = _facts({"compile": 38.0, "test": 66.0}, {}, graph, crit)
    assert f["runner_up_s"] == 0.0


def test_chain_summary_reduces_the_per_pr_facts():
    facts = [
        {"sha": "a", "chain": ["prep", "verify"], "chain_s": 220.0,
         "member_spans_s": {"prep": 120.0, "verify": 100.0},
         "co_longest_n": 1, "runner_up_s": 197.0, "chain_win_s": 23.0,
         "fallback": None, "makespan_s": 222.0},
        {"sha": "b", "chain": ["prep", "verify"], "chain_s": 224.0,
         "member_spans_s": {"prep": 122.0, "verify": 102.0},
         "co_longest_n": 1, "runner_up_s": 195.0, "chain_win_s": 29.0,
         "fallback": None, "makespan_s": 226.0},
        {"sha": "c", "chain": ["CI / test"], "chain_s": 197.0,
         "member_spans_s": {"CI / test": 197.0},
         "co_longest_n": 1, "runner_up_s": 190.0, "chain_win_s": 7.0,
         "fallback": None, "makespan_s": None},
    ]
    s = cr._chain_summary(facts)
    assert s["n"] == 3
    assert s["chain_p50_s"] == 220.0
    assert s["modal_chain"] == ["prep", "verify"]
    assert s["modal_n"] == 2
    assert s["runner_up_p50_s"] == 195.0
    assert s["chain_win_p50_s"] == 23.0, "median of the PER-PR wins"
    assert s["makespan_p50_s"] == 224.0  # median of the two non-None makespans
    # Signed divergence: (chain_p50 - makespan_p50) / makespan_p50, in percent.
    assert abs(s["divergence_pct"] - (220.0 - 224.0) / 224.0 * 100) < 0.01


def test_chain_summary_win_is_median_of_per_pr_wins_not_difference_of_medians():
    # Pass-A probe: chain and runner-up lengths correlate on real repos, so
    # p50(chain) - p50(runner_up) can overstate the honest win 10x. The stamp
    # must carry the median of the PER-PR differences.
    facts = [
        {"chain": ["a", "b"], "chain_s": 100.0, "runner_up_s": 95.0,
         "chain_win_s": 5.0, "makespan_s": None},
        {"chain": ["a", "b"], "chain_s": 200.0, "runner_up_s": 100.0,
         "chain_win_s": 100.0, "makespan_s": None},
        {"chain": ["a", "b"], "chain_s": 300.0, "runner_up_s": 290.0,
         "chain_win_s": 10.0, "makespan_s": None},
    ]
    s = cr._chain_summary(facts)
    assert s["chain_win_p50_s"] == 10.0
    assert s["chain_p50_s"] - s["runner_up_p50_s"] == 100.0  # the dishonest number


def test_chain_summary_modal_tie_breaks_lexicographic_and_empty_is_none():
    assert cr._chain_summary([]) is None
    facts = [
        {"chain": ["b"], "chain_s": 10.0, "makespan_s": None, "runner_up_s": 0.0},
        {"chain": ["a"], "chain_s": 10.0, "makespan_s": None, "runner_up_s": 0.0},
    ]
    s = cr._chain_summary(facts)
    assert s["modal_chain"] == ["a"] and s["modal_n"] == 1
    assert s["makespan_p50_s"] is None and s["divergence_pct"] is None


# --- PR-N2 requirement (i) revert guard (pass-A finding 2) ----------------------

def test_stamp_scopes_both_legs_to_the_spine():
    # A dropped push-only rider is the longest check on the PR AND carries the
    # widest interval. Reverting the spine filter (either leg) turns this red.
    graph = {"ci.yml": {"compile": {"needs": []}, "test": {"needs": ["compile"]}}}
    crit = _crit({"ci.yml": {"compile": 38.0, "test": 66.0}})
    per_sha = [{"compile": 38.0, "test": 66.0, "nightly-rider": 900.0}]
    intervals = {"s0": {
        "compile": ("2026-01-01T00:00:00Z", "2026-01-01T00:00:38Z"),
        "test": ("2026-01-01T00:00:40Z", "2026-01-01T00:01:46Z"),
        "nightly-rider": ("2026-01-01T00:00:00Z", "2026-01-01T00:15:00Z"),
    }}
    facts = cr._stamp_chain_facts(
        ["s0"], per_sha, {"compile", "test"}, {}, graph, crit, intervals)
    assert len(facts) == 1
    f = facts[0]
    assert f["chain"] == ["compile", "test"], (
        "a spine-dropped rider entered the chain — requirement (i) reverted")
    assert "nightly-rider" not in f["member_spans_s"]
    assert f["makespan_s"] == 106.0, (
        "the rider inflated the makespan — the divergence legs are no longer "
        f"the same population (got {f['makespan_s']})")


# --- PR-N3: OPT21 chain-fact evidence citation (red/green; found missing by ---
# --- N3's adversarial pass — the e2e corpus keeps OPT21 deliberately quiet) ---

def _opt21_fixture():
    wf = ".github/workflows/ci.yml"
    graph = {wf: {
        "compile": {"name": "compile", "needs": [], "reusable": False, "matrix": False},
        "test": {"name": "test", "needs": ["compile"], "reusable": False, "matrix": False}}}
    crit = _crit({wf: {"compile": 38.0, "test": 66.0}})
    summary = {"modal_chain": ["compile", "test"], "chain_p50_s": 104.0}
    findings = [
        {"pattern": "OPT21", "workflow_file": wf, "evidence": "needs: compile on test"},
        {"pattern": "OPT21", "workflow_file": ".github/workflows/other.yml",
         "evidence": "unrelated edge"},
        {"pattern": "OPT46", "workflow_file": wf, "evidence": "not an OPT21"},
    ]
    return wf, graph, crit, summary, findings


def test_opt21_on_chain_workflow_gains_the_chain_note():
    _wf, graph, crit, summary, findings = _opt21_fixture()
    cr._cite_chain_in_opt21_evidence(findings, summary, graph, crit)
    assert "hosts the measured gate chain (compile -> test)" in findings[0]["evidence"]
    # Sizing untouched — evidence annotation only.
    assert findings[0]["evidence"].startswith("needs: compile on test")
    # Other-workflow OPT21 and non-OPT21 findings stay unannotated.
    assert "gate chain" not in findings[1]["evidence"]
    assert "gate chain" not in findings[2]["evidence"]


def test_opt21_chain_note_is_idempotent():
    _wf, graph, crit, summary, findings = _opt21_fixture()
    cr._cite_chain_in_opt21_evidence(findings, summary, graph, crit)
    once = findings[0]["evidence"]
    cr._cite_chain_in_opt21_evidence(findings, summary, graph, crit)
    assert findings[0]["evidence"] == once, "the note must never be appended twice"


def test_opt21_chain_note_noops_without_a_modal_chain():
    _wf, graph, crit, _summary, findings = _opt21_fixture()
    for summary in (None, {}, {"modal_chain": ["test"]}):
        cr._cite_chain_in_opt21_evidence(findings, summary, graph, crit)
    assert findings[0]["evidence"] == "needs: compile on test"


def test_opt21_chain_note_noops_when_chain_workflow_is_unresolvable():
    _wf, graph, crit, summary, findings = _opt21_fixture()
    summary = dict(summary, modal_chain=["compile", "External Bot"])
    cr._cite_chain_in_opt21_evidence(findings, summary, graph, crit)
    assert findings[0]["evidence"] == "needs: compile on test"
