"""Issue #115 — the chain headline must lead with the OBSERVED wall when the makespan
materially exceeds the chain sum.

A serial `needs:` chain finishes only when its last stage ends, but the observed per-PR wall
also carries the QUEUE GAPS between stages, so the chain sum UNDERSTATES the real wait. On
withastro/astro the bottom line led with a 16m18s chain sum while the report's own Model check
said the measured wall was ~69m04s (divergence -76%) and advised "Budget on the observed wall" —
the headline led with the number its own note told you not to budget on, and the close reused it
verbatim. When |divergence| exceeds the Model-check threshold (25%), the "typical PR waits /
until all checks finish" WALL now leads with the observed makespan and the chain sum is demoted
to attribution. A mild-divergence chain (the common case) is unchanged (byte-identical lead).

Synthetic fixtures mirror the astro shape (a big-makespan / small-chain-sum divergence) without
any third-party data dump; the live astro bundle verified the same flip.

Run: pytest -v skills/ci-speedup/tests/test_headline_makespan_divergence.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import blocking_path as bp  # noqa: E402  (uniquely-named module; no cross-skill clash)

_VERIFY = Path(__file__).resolve().parent / "verify_report.py"


def _vr():
    spec = importlib.util.spec_from_file_location("ci_speedup_verify_report_divergence", _VERIFY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ci_speedup_verify_report_divergence"] = mod
    spec.loader.exec_module(mod)
    return mod


def _doc(makespan_s: float, *, chain_s: float = 900.0, mA: float = 100.0, mB: float = 800.0,
         n: int = 20, chain_win: float = 300.0, runner_up: float = 600.0,
         cluster: bool = False) -> dict:
    """A minimal render doc: a 2-member `needs:` chain (A → B) whose per-PR makespan is
    `makespan_s`. `chain_s` = A + B member spans. The renderer keys on `chain_summary`; the
    verify legs re-derive from `chain_facts`, so both are kept consistent here."""
    facts = [{"sha": f"s{i}", "chain": ["A", "B"], "member_spans_s": {"A": mA, "B": mB},
              "chain_s": chain_s, "co_longest_n": 1, "runner_up_s": runner_up,
              "chain_win_s": chain_win, "makespan_s": makespan_s} for i in range(n)]
    div = round((chain_s - makespan_s) / makespan_s * 100.0, 2)
    findings: list[dict] = []
    if cluster:
        findings.append({
            "id": "c", "pattern": "OPT73", "cluster_floor_lever": True,
            "workflow_file": ".github/workflows/ci.yml", "affected_jobs": ["A", "B"],
            "cluster_legs_concurrent": True,
            "evidence": ("the `Test` step is 90% of the slowest cluster job `B` and recurs "
                         "across 2 concurrent jobs - a cluster-floor lever"),
            "wall_clock_p50_s": 320.0, "runner_min_saving": 100.0, "tier": 1,
            "realization": "direct"})
    return {
        "repo": "o/r", "scanned_at": "2026-06-08T00:00:00Z",
        "data_sources": {"runs_sampled": 100, "jobs_sampled": 300, "workflows_analyzed": 5},
        "pr_critical_path": {
            "sampled_pr_count": n, "sample_target": n, "sample_complete": True,
            "critical_path_check": "B", "critical_path_s": mB,
            "poles": [{"check": "B", "p50_s": mB, "workflow_file": ".github/workflows/ci.yml",
                       "job": "B", "dominant_step": "Test", "dominant_p50_s": mB * 0.9,
                       "steps": [{"step": "Test", "category": "test", "p50_s": mB * 0.9}]}],
            "checks": [{"name": "A", "p50_s": mA, "pole_n": 0},
                       {"name": "B", "p50_s": mB, "pole_n": n}],
            "chain_facts": facts,
            "chain_summary": {"modal_chain": ["A", "B"], "chain_p50_s": chain_s,
                              "chain_win_p50_s": chain_win, "runner_up_p50_s": runner_up,
                              "makespan_p50_s": makespan_s, "divergence_pct": div,
                              "modal_n": n, "n": n},
        },
        "findings": findings,
    }


def _bottom_line(md: str) -> str:
    return next((ln for ln in md.splitlines() if "**Bottom line.**" in ln), "")


def _chain_lead(md: str) -> str:
    return next((ln for ln in md.splitlines() if "until all checks finish" in ln), "")


def _write(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# A. Renderer — the diverging chain leads the wall with the observed makespan.
# --------------------------------------------------------------------------- #
def test_diverging_chain_headline_leads_with_the_observed_wall_not_the_chain_sum():
    # makespan 4000s (66m40s) vs a 900s (15m 0s) chain sum → divergence -77.5%.
    bl = _bottom_line(bp.render(_doc(4000.0)))
    assert "A typical PR waits **66m 40s**" in bl, bl
    assert "observed per-PR wall" in bl
    # The chain sum is demoted to attribution, not the headline wait.
    assert "sums to only 15m 00s of serial work" in bl
    assert "for the `A` → `B` chain to finish" not in bl  # never the chain-sum lead here


def test_diverging_chain_lead_and_model_check_agree_on_the_wall():
    md = bp.render(_doc(4000.0))
    lead = _chain_lead(md)
    assert "**66m 40s until all checks finish**" in lead, lead
    assert "queue gaps between the stages" in lead
    assert "Budget on the 66m 40s wall" in lead
    # The Model check (|divergence| > 25%) still fires and no longer contradicts the lead.
    assert any("Model check" in ln and "Budget on the observed wall" in ln
               for ln in md.splitlines())


def test_diverging_cluster_crown_wait_is_the_wall_but_win_is_unchanged():
    # A diverging chain WITH an on-spine cluster crown: the "typical PR waits" figure is the wall,
    # while the cluster win (~5m20s) stays the first tilde-clock the verifier reads.
    bl = _bottom_line(bp.render(_doc(4000.0, cluster=True)))
    assert "A typical PR waits **66m 40s** for all checks to finish" in bl, bl
    assert "**~5m 20s**" in bl                       # the cluster win, unchanged
    assert bl.index("66m 40s") < bl.index("~5m 20s")  # wall (no tilde) precedes the tilde-win


def test_malformed_divergence_pct_does_not_crash_render_falls_back():
    # Greptile #125 P2: a persisted / externally-supplied findings.json can carry a non-numeric
    # `divergence_pct`. The render must parse it defensively (`_num`, like every other chain_summary
    # field) and fall back to the non-divergent chain-sum lead, never raise.
    doc = _doc(4000.0)   # a shape that WOULD diverge if the value parsed
    doc["pr_critical_path"]["chain_summary"]["divergence_pct"] = "not-a-number"
    bl = _bottom_line(bp.render(doc))   # must not raise
    assert "A typical PR waits **15m 00s** for the `A` → `B` chain to finish" in bl, bl
    assert "observed per-PR wall" not in bl


def test_mild_divergence_chain_headline_is_unchanged_no_regression():
    # makespan 950s vs a 900s chain sum → divergence -5.3%, within threshold: the classic
    # chain-sum lead stands byte-for-byte (the common well-behaved case).
    bl = _bottom_line(bp.render(_doc(950.0)))
    assert "A typical PR waits **15m 00s** for the `A` → `B` chain to finish" in bl, bl
    assert "observed per-PR wall" not in bl


# --------------------------------------------------------------------------- #
# B. Guard — check_headline_wait_is_divergence_correct red/green.
# --------------------------------------------------------------------------- #
def test_guard_passes_when_the_diverging_headline_leads_with_the_wall(tmp_path):
    vr = _vr()
    doc = _doc(4000.0)
    md = bp.render(doc)
    c = vr.check_headline_wait_is_divergence_correct(md, _write(tmp_path, doc), None)
    assert c.ok and not c.skipped, c.detail
    assert "leads with the observed wall" in c.detail


def test_guard_FAILS_when_the_chain_sum_leads_a_diverging_shape(tmp_path):
    # The exact live defect: a diverging shape (makespan 4000s) whose bottom line still led with the
    # 900s chain sum. Feed a hand-built chain-sum-lead report against the diverging findings.
    vr = _vr()
    doc = _doc(4000.0)
    bad = ("> **Bottom line.** A typical PR waits **15m 00s** for the `A` → `B` chain to finish "
           "- the members run in sequence.\n")
    c = vr.check_headline_wait_is_divergence_correct(bad, _write(tmp_path, doc), None)
    assert not c.ok and not c.skipped, c.detail
    assert "measured makespan p50 is 66m 40s" in c.detail
    assert "demote the chain sum to attribution" in c.detail


def test_guard_skips_a_mild_divergence_shape(tmp_path):
    vr = _vr()
    doc = _doc(950.0)   # -5.3% divergence, within threshold
    md = bp.render(doc)
    c = vr.check_headline_wait_is_divergence_correct(md, _write(tmp_path, doc), None)
    assert c.skipped and c.ok, c.detail
    assert "within" in c.detail and "chain-sum lead is honest" in c.detail


def test_guard_skips_a_singleton_chain(tmp_path):
    vr = _vr()
    doc = _doc(4000.0)
    # Collapse to a 1-member modal chain — no chain headline is claimed.
    for f in doc["pr_critical_path"]["chain_facts"]:
        f["chain"] = ["B"]
        f["member_spans_s"] = {"B": 800.0}
        f["chain_s"] = 800.0
    doc["pr_critical_path"]["chain_summary"]["modal_chain"] = ["B"]
    c = vr.check_headline_wait_is_divergence_correct(bp.render(doc), _write(tmp_path, doc), None)
    assert c.skipped and c.ok, c.detail
    assert "no >=2-member modal chain" in c.detail


def test_guard_skips_a_legacy_artifact_without_a_makespan(tmp_path):
    vr = _vr()
    doc = _doc(4000.0)
    for f in doc["pr_critical_path"]["chain_facts"]:
        f.pop("makespan_s", None)
    doc["pr_critical_path"]["chain_summary"]["makespan_p50_s"] = None
    c = vr.check_headline_wait_is_divergence_correct(bp.render(doc), _write(tmp_path, doc), None)
    assert c.skipped and c.ok, c.detail
    assert "no chain_facts makespan stamped" in c.detail
