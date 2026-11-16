"""Tier-2 (runner-minute) stamp tests — PR-1, data-only.

Covers the PR-1 deliverables that carry correctness risk:
  1. _billable_equiv_min — per-job billable-minute round-up (the minutes basis).
  2. _stamp_tier2_neutrality — the COMPUTED below-floor margin. The plan's
     central correction: today's runner-min-only sizing asserts wall-clock 0
     with a canned note; PR-1 must DERIVE the floor margin and stamp it so
     verify_report can re-derive it. These tests pin that it is computed, not
     canned.
  3. _stamp_sizing_basis — measured-vs-modeled stamp.
  4. Wiring + property guards — the stamps are actually called in collect(), and
     the class-level invariants ("no certified-neutral finding has wall-clock",
     "measured basis carries no heuristic constant") hold swept across findings.

The end-to-end stamping (collect -> findings.json) is proven by
test_offline_pipeline_e2e; here we unit-test the derivations directly.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import collect_runs as cr  # noqa: E402


# =========================================================================
# _billable_equiv_min — per-job billable-minute round-up (minutes only)
# =========================================================================

def test_billable_equiv_min_rounds_up_excludes_skipped_clamps_negative():
    def job(s, c, concl="success"):
        return {"started_at": s, "completed_at": c, "conclusion": concl}
    # 61s -> 2 billed minutes (round UP), 60s -> 1, 1s -> 1.
    assert cr._billable_equiv_min(job("2026-01-01T00:00:00Z", "2026-01-01T00:01:01Z")) == 2
    assert cr._billable_equiv_min(job("2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z")) == 1
    assert cr._billable_equiv_min(job("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z")) == 1
    # skipped bills nothing even with a positive span.
    assert cr._billable_equiv_min(
        job("2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z", "skipped")) == 0
    # negative span (skipped jobs report completed < started) clamps to 0.
    assert cr._billable_equiv_min(
        job("2026-01-01T00:05:00Z", "2026-01-01T00:00:00Z")) == 0


def test_billable_equiv_min_none_on_unparseable_timestamps():
    # Unknown duration -> None (unpriceable), never a silent 0 billed minutes.
    assert cr._billable_equiv_min({"started_at": "nope", "completed_at": "also-nope"}) is None
    assert cr._billable_equiv_min({}) is None
    # skipped is a KNOWN zero even with a valid span.
    assert cr._billable_equiv_min(
        {"conclusion": "skipped", "started_at": "2026-01-01T00:00:00Z",
         "completed_at": "2026-01-01T00:01:00Z"}) == 0


# =========================================================================
# _stamp_tier2_neutrality — the COMPUTED below-floor margin
# =========================================================================

def _crit(job_p50, floor, job_runner=None, runner_scope="ubuntu-latest"):
    return {"job_p50": job_p50, "floor_p50": floor,
            "job_runner": job_runner or {}, "runner_scope": runner_scope}


def test_neutrality_below_floor_margin_is_computed_not_canned():
    # A runner-min-only finding whose affected job (100s) finishes below the
    # cluster floor (300s): the certificate margin must be the COMPUTED
    # floor - job = 200s, with the below_cluster_floor proof and a derivation
    # ref — never a canned "below the cluster floor" string with no number.
    f = {"pattern": "OPT33", "affected_jobs": ["lint"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": 42.0}
    cr._stamp_tier2_neutrality(f, _crit({"lint": 100.0}, 300.0))
    cert = f.get("tier2_neutrality")
    assert cert is not None, "expected a neutrality certificate below the floor"
    assert cert["proof"] == "below_cluster_floor"
    assert cert["margin_s"] == 200.0, "margin must be computed floor - job_p50"
    assert "floor_p50" in cert["ref"] and "job" in cert["ref"]


def test_neutrality_margin_tracks_the_data():
    # Change the inputs -> the margin changes accordingly (proves it's derived
    # from the data, not a constant).
    f = {"pattern": "OPT45", "affected_jobs": ["docs"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": 10.0}
    cr._stamp_tier2_neutrality(f, _crit({"docs": 30.0}, 720.0))
    assert f["tier2_neutrality"]["margin_s"] == 690.0


def test_no_certificate_for_a_wall_clock_lever():
    # Any positive wall-clock => Tier-1 lever => never certified neutral.
    f = {"pattern": "OPT1", "affected_jobs": ["build"],
         "wall_clock_p50_s": 45.0, "runner_min_saving": 100.0}
    cr._stamp_tier2_neutrality(f, _crit({"build": 100.0}, 300.0))
    assert "tier2_neutrality" not in f


def test_no_certificate_without_a_credited_bill_saving():
    # rm None/0 => nothing to certify.
    f = {"pattern": "OPT33", "affected_jobs": ["lint"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": None}
    cr._stamp_tier2_neutrality(f, _crit({"lint": 100.0}, 300.0))
    assert "tier2_neutrality" not in f


def test_no_certificate_when_job_is_the_pole_not_below_floor():
    # own > floor (the job IS a pole) => below_cluster_floor cannot fire and,
    # absent off_spine, no certificate is minted.
    f = {"pattern": "OPT33", "affected_jobs": ["big"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": 42.0}
    cr._stamp_tier2_neutrality(f, _crit({"big": 500.0}, 300.0))
    assert "tier2_neutrality" not in f


def test_off_spine_certificate_is_deferred_in_pr1():
    # off_spine alone is NOT proof of wall-clock-neutrality (a not-required check
    # can still gate an all-checks-green merge), so PR-1 mints no off_spine cert.
    f = {"pattern": "OPT33", "affected_jobs": ["x"], "off_spine": True,
         "wall_clock_p50_s": 0.0, "runner_min_saving": 42.0}
    cr._stamp_tier2_neutrality(f, _crit({}, 0.0, runner_scope="all-runners"))
    assert "tier2_neutrality" not in f


def test_no_false_cert_from_fuzzy_decoy_sibling_job():
    # ADVERSARIAL regression: affected job `test` is a name:-overridden pole
    # (`Unit test` = 900s = the floor-setter's superior), and a fast sibling
    # `test-helpers` (90s) leads with the same word. The FUZZY resolver would
    # bind `test`->`test-helpers` (90 < floor) and mint a false neutral cert on
    # a finding whose real job is the pole. The strict resolver used by the cert
    # refuses the fuzzy match -> no certificate.
    f = {"pattern": "OPT33", "affected_jobs": ["test"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": 10.0}
    crit = _crit({"Unit test": 900.0, "test-helpers": 90.0, "build": 300.0}, 300.0)
    cr._stamp_tier2_neutrality(f, crit)
    assert "tier2_neutrality" not in f


def test_no_cert_for_direct_model_below_floor_fix_can_bleed():
    # A direct/cache/setup fix (OPT5, uncached pnpm) below the floor is NOT
    # certified: the same fix lowers the shared step in every job, incl. the
    # pole, so it is not wall-clock-neutral. Only runner-min-only levers certify.
    f = {"pattern": "OPT5", "affected_jobs": ["lint"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": 20.0}
    cr._stamp_tier2_neutrality(f, _crit({"lint": 100.0}, 300.0))
    assert "tier2_neutrality" not in f


def test_no_cert_for_wall_clock_negative_finding():
    f = {"pattern": "OPT33", "affected_jobs": ["lint"], "wall_clock_negative": True,
         "wall_clock_p50_s": 0.0, "runner_min_saving": 20.0}
    cr._stamp_tier2_neutrality(f, _crit({"lint": 100.0}, 300.0))
    assert "tier2_neutrality" not in f


def test_below_floor_margin_stays_strictly_positive_under_rounding():
    # A sub-0.05 gap must NOT mint a margin_s=0.0 cert (float-precision guard).
    f = {"pattern": "OPT33", "affected_jobs": ["lint"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": 20.0}
    cr._stamp_tier2_neutrality(f, _crit({"lint": 100.0}, 100.04))
    assert "tier2_neutrality" not in f


def test_no_below_floor_certificate_when_job_exactly_equals_floor():
    # own == floor: the job IS the floor-setter, not strictly below it, so
    # below_cluster_floor (which would stamp margin_s=0.0) must NOT fire; absent
    # off_spine, no certificate. Keeps every below_cluster_floor margin > 0.
    f = {"pattern": "OPT33", "affected_jobs": ["lint"],
         "wall_clock_p50_s": 0.0, "runner_min_saving": 42.0}
    cr._stamp_tier2_neutrality(f, _crit({"lint": 300.0}, 300.0))
    assert "tier2_neutrality" not in f


def test_no_certificate_when_wall_clock_is_unknown_none():
    # wall_clock_p50_s == None means UNKNOWN, not zero. Certifying "no wall-clock
    # benefit" off an unmeasured value would assert an underived fact — must be
    # withheld (only an explicit measured 0/0.0 is neutral-eligible).
    f = {"pattern": "OPT33", "affected_jobs": ["lint"],
         "wall_clock_p50_s": None, "runner_min_saving": 42.0}
    cr._stamp_tier2_neutrality(f, _crit({"lint": 100.0}, 300.0))
    assert "tier2_neutrality" not in f


# =========================================================================
# _derive_repo_visibility ladder
# =========================================================================

def test_derive_repo_visibility_ladder():
    assert cr._derive_repo_visibility({"visibility": "private"}) == "private"
    assert cr._derive_repo_visibility({"private": True}) == "private"
    assert cr._derive_repo_visibility({"private": False}) == "public"
    assert cr._derive_repo_visibility({}) is None        # unreadable repo
    assert cr._derive_repo_visibility(None) is None


# =========================================================================
# _stamp_sizing_basis
# =========================================================================

def test_sizing_basis_measured_vs_modeled():
    fm = {"pattern": "OPT24"}   # data-driven detector -> measured
    cr._stamp_sizing_basis(fm)
    assert fm["sizing_basis"] == "measured"
    fh = {"pattern": "OPT33"}   # hit_rate heuristic -> modeled
    cr._stamp_sizing_basis(fh)
    assert fh["sizing_basis"] == "modeled"
    fn = {"pattern": "OPT_UNKNOWN"}   # no sizing model -> unstamped
    cr._stamp_sizing_basis(fn)
    assert "sizing_basis" not in fn


def test_stamp_sizing_basis_never_clobbers_a_detectors_measured_signal():
    # measured_signal is a PRE-EXISTING field the data-driven detectors fill with
    # real evidence. The sizing-basis stamp must add only `sizing_basis` and
    # leave that evidence untouched (regression for the additive-only invariant).
    real = "job `Docs E2E tests` p50 346s over 20 runs, no shard axis observed"
    f = {"pattern": "OPT24", "measured_signal": real}
    cr._stamp_sizing_basis(f)
    assert f["measured_signal"] == real
    assert f["sizing_basis"] == "measured"


def test_stamp_sizing_basis_preserves_detector_set_basis_for_mixed_patterns():
    # OPT36 has both static modeled findings and a measured schedule-burn upgrade.
    # The generic pattern table remains modeled for the static finding, so a
    # detector that proves measured sizing must be able to stamp the per-finding
    # basis without being downgraded later by the generic stamp pass.
    f = {"pattern": "OPT36", "sizing_basis": "measured",
         "measured_signal": "schedule event total_count x mean job-minutes"}
    cr._stamp_sizing_basis(f)
    assert f["sizing_basis"] == "measured"


# =========================================================================
# Wiring guards — the stamps are actually invoked in collect()
# =========================================================================

def test_tier2_stamps_are_wired_into_collect():
    src = inspect.getsource(cr.collect)
    for call in ("_stamp_sizing_basis(",
                 "_stamp_tier2_neutrality(", "_reconcile_tier2_overlap("):
        assert call in src, f"{call} is not wired into collect()"
    # repo visibility + events mirror persisted for re-derivation.
    assert 'findings_doc["repo_visibility"]' in src
    assert 'findings_doc["events_by_wf"]' in src


def test_reconcile_tier2_overlap_leaves_unidentified_rows_unchanged():
    # Old/pre-stamp findings, or measured findings without a concrete sampled
    # run-id overlap basis, stay compatible and unchanged.
    findings = [
        {"sizing_basis": "modeled", "tier2_neutrality": {"proof": "below_cluster_floor"},
         "runner_min_saving": 42.0},
        {"sizing_basis": "measured", "tier2_neutrality": {"proof": "post_completion_waste"},
         "runner_min_saving": 7.0},  # no sampled run IDs
    ]
    before = [f["runner_min_saving"] for f in findings]
    cr._reconcile_tier2_overlap(findings)
    assert [f["runner_min_saving"] for f in findings] == before


def test_reconcile_tier2_overlap_discounts_duplicate_sampled_run_ids():
    findings = [
        {"pattern": "OPT46", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "tier2_neutrality": {"proof": "post_completion_waste"},
         "runner_min_saving": 100.0, "tier2_sample_run_ids": ["1", "2"]},
        {"pattern": "OPT36", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "tier2_neutrality": {"proof": "non_pr_event"},
         "runner_min_saving": 30.0, "tier2_sample_run_ids": ["2", "3"]},
    ]
    cr._reconcile_tier2_overlap(findings)
    assert findings[0]["runner_min_saving"] == 100.0
    assert findings[1]["runner_min_saving"] == 15.0
    assert findings[1]["runner_min_overlap_s"] == 15.0
    assert "1 sampled run id" in findings[1]["tier2_overlap_note"]


def test_reconcile_tier2_overlap_does_not_use_opt64_bare_run_ids():
    findings = [
        {"pattern": "OPT64", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "tier2_neutrality": {"proof": "post_completion_waste"},
         "runner_min_saving": 80.0, "tier2_sample_run_ids": ["run-1", "run-2"]},
        {"pattern": "OPT46", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "tier2_neutrality": {"proof": "post_completion_waste"},
         "runner_min_saving": 20.0, "tier2_sample_run_ids": ["run-2", "run-3"]},
    ]
    cr._reconcile_tier2_overlap(findings)
    assert findings[0]["runner_min_saving"] == 80.0
    assert findings[1]["runner_min_saving"] == 20.0
    assert "runner_min_overlap_s" not in findings[1]


def test_reconcile_tier2_overlap_does_not_use_opt65_bare_run_ids():
    findings = [
        {"pattern": "OPT65", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "tier2_neutrality": {"proof": "below_cluster_floor"},
         "runner_min_saving": 12.0, "tier2_sample_run_ids": ["run-1"]},
        {"pattern": "OPT46", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "tier2_neutrality": {"proof": "post_completion_waste"},
         "runner_min_saving": 20.0, "tier2_sample_run_ids": ["run-1"]},
    ]
    cr._reconcile_tier2_overlap(findings)
    assert findings[0]["runner_min_saving"] == 12.0
    assert findings[1]["runner_min_saving"] == 20.0
    assert "runner_min_overlap_s" not in findings[1]


def test_reconcile_tier2_overlap_keeps_opt35_job_scoped_rows_additive():
    findings = [
        {"pattern": "OPT35", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "affected_jobs": ["unit"],
         "tier2_neutrality": {"proof": "post_completion_waste"},
         "runner_min_saving": 15.0, "tier2_sample_run_ids": ["run-1"]},
        {"pattern": "OPT35", "workflow_file": "ci.yml", "sizing_basis": "measured",
         "affected_jobs": ["e2e"],
         "tier2_neutrality": {"proof": "post_completion_waste"},
         "runner_min_saving": 10.0, "tier2_sample_run_ids": ["run-1"]},
    ]
    cr._reconcile_tier2_overlap(findings)
    assert [f["runner_min_saving"] for f in findings] == [15.0, 10.0]
    assert all("runner_min_overlap_s" not in f for f in findings)


# =========================================================================
# Property guards — swept across a synthetically-stamped finding set
# =========================================================================

def _stamp_all(findings, crit):
    for f in findings:
        cr._stamp_sizing_basis(f)
        cr._stamp_tier2_neutrality(f, crit)
    return findings


def _sample_findings():
    return [
        {"pattern": "OPT33", "affected_jobs": ["lint"], "wall_clock_p50_s": 0.0,
         "runner_min_saving": 42.0},
        {"pattern": "OPT1", "affected_jobs": ["build"], "wall_clock_p50_s": 45.0,
         "runner_min_saving": 100.0},
        {"pattern": "OPT24", "affected_jobs": ["test"], "wall_clock_p50_s": 12.0,
         "runner_min_saving": 8.0},
    ]


def test_property_no_certified_finding_has_positive_wall_clock():
    findings = _stamp_all(_sample_findings(),
                          _crit({"lint": 100.0, "build": 500.0, "test": 400.0}, 300.0,
                                job_runner={"lint": "ubuntu-latest"}))
    for f in findings:
        if f.get("tier2_neutrality"):
            assert f.get("wall_clock_p50_s") in (0, 0.0, None), (
                f"{f['pattern']} carries a neutrality certificate but has "
                f"wall_clock_p50_s={f.get('wall_clock_p50_s')} > 0")


def test_property_measured_basis_carries_no_heuristic_constant():
    # Every 'measured'-stamped finding's pattern must have model=='measured' in
    # _SIZING (no hit_rate / default_s in the chain) — the data-level analog of
    # verify_report's check_tier2_measured_basis.
    findings = _stamp_all(_sample_findings(),
                          _crit({"lint": 100.0, "build": 500.0, "test": 400.0}, 300.0))
    for f in findings:
        if f.get("sizing_basis") == "measured":
            cfg = cr._SIZING.get(f["pattern"], {})
            assert cfg.get("model") == "measured"
            assert "hit_rate" not in cfg and "default_s" not in cfg
