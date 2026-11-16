"""Regression: the non-universal-slowest headline must not blame the LOWER typical merge
floor on the slowest check's PRESENCE when that check is present on a MAJORITY of sampled PRs.

The nx `main-linux` bug: the headline read "`main-linux` is the slowest check a typical PR
waits on (~46m 33s), but it ran on only 19/20 sampled PRs, so a typical PR finishes in 10m 32s."
Presence at 19/20 (95%) cannot lower a median wait from 46m to 10m — the median PR RUNS the check.
The real driver is a duration / population skew: the check's conditional p50 (measured over a wider
run-sample) overstates what a typical PR waits, while the population-weighted median of the per-PR
maxima is far lower. The `elif gate_is_slowest:` non-universal-disclosure branch hard-coded the
presence-causal "ran on only N/npop, so" template regardless of presence, producing the
non-sequitur.

CLASS fix: `verify_report.check_headline_presence_causal_only_when_minority` re-derives present/npop
from the per-PR `populations` ground truth and FAILS any form-1 (name-first) presence-causal headline
whose named check is present on a MAJORITY (> npop * _RARE_PRESENCE_FRAC). The engine now emits that
presence-causal framing only for a genuinely MINORITY-present check (where a typical PR skips it), and
a duration-skew framing otherwise.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bp():
    return _load(_SKILL_DIR / "scripts" / "blocking_path.py", "ci_speedup_bp_presence_causal")


def _vr():
    return _load(_SKILL_DIR / "tests" / "verify_report.py", "ci_speedup_vr_presence_causal")


def _nx_majority_doc():
    """nx `main-linux` shape: slowest typical check, ALSO the frequency gate, present on a
    MAJORITY (19/20). Its conditional p50 (checks[].p50_s = 2793s) is measured over a wider
    run-sample than the per-PR populations (~668s each), so the population-weighted floor is far
    lower — floor_lowered — WITHOUT presence being the cause."""
    ml = "main-linux"
    checks = [
        {"name": ml, "p50_s": 2793.0, "present_on": 19, "workflow_file": "ci.yml"},
        {"name": "lint", "p50_s": 100.0, "present_on": 20, "workflow_file": "ci.yml"},
    ]
    pops = ([[0.05, [[ml, 668.0], ["lint", 100.0]]] for _ in range(19)]
            + [[0.05, [["lint", 100.0]]] for _ in range(1)])
    return {"pr_critical_path": {
        "critical_path_check": ml, "critical_path_s": 2793.0,
        "checks": checks, "check_present_n_pr": 20, "populations": [list(p) for p in pops],
        "poles": [{"check": ml, "p50_s": 2793.0, "workflow_file": "ci.yml", "job": ml}],
    }, "findings": []}


def _headline_line(report: str) -> str:
    for line in report.splitlines():
        if "slowest check a typical PR waits on" in line:
            return line
    return ""


def test_majority_present_headline_drops_the_presence_non_sequitur():
    bp = _bp()
    out = bp.render(_nx_majority_doc())
    head = _headline_line(out)
    assert head, "the non-universal-slowest headline must render"
    # The BUG (pre-fix): "...but it ran on only 19/20 sampled PRs, so a typical PR finishes in...".
    assert "ran on only 19/20 sampled PRs, so a typical PR finishes in" not in out, (
        "a 19/20 (majority) presence must NOT be blamed for lowering the typical merge floor — "
        f"got: {head!r}")
    # The FIX: attribute the drop to the conditional-p50 overstatement (population skew).
    assert "is a conditional p50 that overstates the typical wait" in head, (
        f"expected the duration/population-skew framing; got: {head!r}")
    # The stamp-binding phrase is preserved (so check_headline_slowest_matches_stamp still binds).
    assert "`main-linux` is the slowest check a typical PR waits on" in head


def test_minority_present_headline_keeps_the_faithful_presence_framing():
    # 3 mutually-exclusive path-gated checks: X (slowest, 2793s) gates 9 PRs, Y (2000s) 6, Z (1500s)
    # 5. X is the frequency gate (9 > 6 > 5) AND slowest, so gate_is_slowest holds — but X is present
    # on only 9/20 (a MINORITY), so a typical PR genuinely SKIPS it. The presence-causal framing is
    # FAITHFUL here and must be retained. `pole_n` is stamped so X stays typical (pole-frequency
    # floor) despite minority presence.
    bp = _bp()
    x, y, z = "web-e2e", "api-e2e", "docs-build"
    checks = [
        {"name": x, "p50_s": 2793.0, "present_on": 9, "pole_n": 9, "workflow_file": "web.yml"},
        {"name": y, "p50_s": 2000.0, "present_on": 6, "pole_n": 6, "workflow_file": "api.yml"},
        {"name": z, "p50_s": 1500.0, "present_on": 5, "pole_n": 5, "workflow_file": "docs.yml"},
    ]
    pops = ([[0.05, [[x, 2793.0]]] for _ in range(9)]
            + [[0.05, [[y, 2000.0]]] for _ in range(6)]
            + [[0.05, [[z, 1500.0]]] for _ in range(5)])
    doc = {"pr_critical_path": {
        "critical_path_check": x, "critical_path_s": 2793.0,
        "checks": checks, "check_present_n_pr": 20, "populations": [list(p) for p in pops],
        "poles": [
            {"check": x, "p50_s": 2793.0, "workflow_file": "web.yml", "job": x},
            {"check": y, "p50_s": 2000.0, "workflow_file": "api.yml", "job": y},
            {"check": z, "p50_s": 1500.0, "workflow_file": "docs.yml", "job": z},
        ],
    }, "findings": []}
    out = bp.render(doc)
    head = _headline_line(out)
    # Minority-present slowest gate → the presence-causal "ran on only N/npop, so" framing is honest.
    assert f"`{x}` is the slowest check a typical PR waits on" in head, head
    assert "but it ran on only 9/20 sampled PRs, so a typical PR finishes in" in head, head


def test_exact_half_presence_boundary_is_minority_both_sides(tmp_path):
    # The `<`/`<=` seam. The engine renders the presence-causal form at MINORITY presence
    # (`present <= npop*_RARE_PRESENCE_FRAC`, i.e. `<=`) and the checker FAILs only at STRICT majority
    # (`present > npop*_VR_RARE_PRESENCE_FRAC`, i.e. `>`). At EXACTLY npop/2 (10/20) the two must be
    # complementary: engine still emits the presence clause, and the checker still PASSES it (10 is not
    # `> 10`). This pins the boundary against a `<`→`<` / `<=`→`<=` drift on either side that would
    # either drop the honest presence clause or false-FAIL an exactly-half-present headline.
    bp = _bp()
    vr = _vr()
    x, y, z = "web-e2e", "api-e2e", "docs-build"
    # X poles 10 PRs (exactly half), Y 6, Z 4 → X is the frequency gate AND slowest, floor lowered.
    checks = [
        {"name": x, "p50_s": 2793.0, "present_on": 10, "pole_n": 10, "workflow_file": "web.yml"},
        {"name": y, "p50_s": 2000.0, "present_on": 6, "pole_n": 6, "workflow_file": "api.yml"},
        {"name": z, "p50_s": 1500.0, "present_on": 4, "pole_n": 4, "workflow_file": "docs.yml"},
    ]
    pops = ([[0.05, [[x, 2793.0]]] for _ in range(10)]
            + [[0.05, [[y, 2000.0]]] for _ in range(6)]
            + [[0.05, [[z, 1500.0]]] for _ in range(4)])
    doc = {"pr_critical_path": {
        "critical_path_check": x, "critical_path_s": 2793.0,
        "checks": checks, "check_present_n_pr": 20, "populations": [list(p) for p in pops],
        "poles": [
            {"check": x, "p50_s": 2793.0, "workflow_file": "web.yml", "job": x},
            {"check": y, "p50_s": 2000.0, "workflow_file": "api.yml", "job": y},
            {"check": z, "p50_s": 1500.0, "workflow_file": "docs.yml", "job": z},
        ],
    }, "findings": []}
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(doc), encoding="utf-8")
    out = bp.render(doc)
    head = _headline_line(out)
    # Engine side: exactly-half is still MINORITY (`<=`) → the presence-causal clause renders.
    assert "but it ran on only 10/20 sampled PRs, so a typical PR finishes in" in head, head
    # Checker side: exactly-half is NOT a strict majority (`>`) → the presence-causal guard PASSES.
    chk = vr.check_headline_presence_causal_only_when_minority(out, findings)
    assert chk.ok is True and not chk.skipped, chk.detail


def test_invariant_fails_the_presence_non_sequitur_report(tmp_path):
    # The CLASS invariant catches the bug straight from the data: given the nx findings (main-linux
    # present 19/20) and a report carrying the OLD presence-causal headline, the check must FAIL.
    vr = _vr()
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(_nx_majority_doc()), encoding="utf-8")
    buggy = (
        "# CI report\n\n"
        "**11m 08s until all checks finish** - `main-linux` is the slowest check a typical PR "
        "waits on (~46m 33s), but it ran on only 19/20 sampled PRs, so a typical PR finishes in "
        "11m 08s.\n\n## Long pole 1: `ci.yml`\n")
    chk = vr.check_headline_presence_causal_only_when_minority(buggy, findings)
    assert chk.ok is False and not chk.skipped, chk.detail
    assert "MAJORITY" in chk.detail

    # And the CURRENT engine's render of the same findings passes the invariant (no presence-causal
    # template rendered → nothing to contradict).
    bp = _bp()
    fixed = bp.render(_nx_majority_doc())
    chk_fixed = vr.check_headline_presence_causal_only_when_minority(fixed, findings)
    assert chk_fixed.ok is True, chk_fixed.detail


def test_invariant_passes_a_genuine_minority_presence_report(tmp_path):
    # A presence-causal headline naming a MINORITY-present check (8/20) is faithful → the invariant
    # PASSES (never a false positive on the honest case).
    vr = _vr()
    bench = "nightly-bench"
    pops = ([[0.05, [[bench, 2793.0], ["lint", 100.0]]] for _ in range(8)]
            + [[0.05, [["lint", 100.0]]] for _ in range(12)])
    doc = {"pr_critical_path": {
        "critical_path_check": bench, "critical_path_s": 2793.0,
        "checks": [
            {"name": bench, "p50_s": 2793.0, "present_on": 8, "workflow_file": "bench.yml"},
            {"name": "lint", "p50_s": 100.0, "present_on": 20, "workflow_file": "ci.yml"},
        ],
        "check_present_n_pr": 20, "populations": [list(p) for p in pops],
        "poles": [{"check": bench, "p50_s": 2793.0, "workflow_file": "bench.yml", "job": bench}],
    }, "findings": []}
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(doc), encoding="utf-8")
    report = (
        "# CI report\n\n"
        f"**11m 08s until all checks finish** - `{bench}` is the slowest check a typical PR "
        "waits on (~46m 33s), but it ran on only 8/20 sampled PRs, so a typical PR finishes in "
        "11m 08s.\n\n## Long pole 1: `bench.yml`\n")
    chk = vr.check_headline_presence_causal_only_when_minority(report, findings)
    assert chk.ok is True and not chk.skipped, chk.detail


def test_majority_render_satisfies_the_floor_reconciliation_sibling(tmp_path):
    # Cross-invariant regression. The `elif gate_is_slowest:` branch fires only when the floor was
    # LOWERED, so the sibling `check_headline_floor_presence_reconciled` (which requires the lowered
    # floor be DISCLOSED) also runs on this headline. The majority sub-branch DROPS the presence
    # clause — so the two headline guards must agree it is still a valid reconciliation, via the
    # conditional-p50-overstatement disclosure. Before the floor-reconciliation check learned to
    # accept that form, the fixed majority render (nx `main-linux` 19/20) SKIPped the presence-causal
    # guard but FAILed floor-reconciliation on the identical report — a self-contradiction between the
    # two guards that no test caught. Drive the ENGINE's real majority render through BOTH: neither
    # may FAIL.
    bp = _bp()
    vr = _vr()
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(_nx_majority_doc()), encoding="utf-8")
    out = bp.render(_nx_majority_doc())
    causal = vr.check_headline_presence_causal_only_when_minority(out, findings)
    reconciled = vr.check_headline_floor_presence_reconciled(out, findings)
    assert causal.ok is True, causal.detail
    # floor-reconciliation actively reconciles here (floor WAS lowered) — a real PASS, not a SKIP.
    assert reconciled.ok is True and not reconciled.skipped, reconciled.detail


def test_minority_render_still_satisfies_floor_reconciliation_via_presence(tmp_path):
    # The other side of the cross-invariant contract: a MINORITY-present floor-lowered form-1 headline
    # keeps the presence clause, which BOTH guards accept. Uses the same 3-mutually-exclusive-gate
    # shape as `test_minority_present_headline_keeps_the_faithful_presence_framing` (X present 9/20,
    # still the frequency gate AND slowest → form-1 minority sub-branch, floor lowered to the 2000s
    # population median). Re-derives from the engine so a wording drift in the render or either guard
    # surfaces here.
    bp = _bp()
    vr = _vr()
    x, y, z = "web-e2e", "api-e2e", "docs-build"
    checks = [
        {"name": x, "p50_s": 2793.0, "present_on": 9, "pole_n": 9, "workflow_file": "web.yml"},
        {"name": y, "p50_s": 2000.0, "present_on": 6, "pole_n": 6, "workflow_file": "api.yml"},
        {"name": z, "p50_s": 1500.0, "present_on": 5, "pole_n": 5, "workflow_file": "docs.yml"},
    ]
    pops = ([[0.05, [[x, 2793.0]]] for _ in range(9)]
            + [[0.05, [[y, 2000.0]]] for _ in range(6)]
            + [[0.05, [[z, 1500.0]]] for _ in range(5)])
    doc = {"pr_critical_path": {
        "critical_path_check": x, "critical_path_s": 2793.0,
        "checks": checks, "check_present_n_pr": 20, "populations": [list(p) for p in pops],
        "poles": [
            {"check": x, "p50_s": 2793.0, "workflow_file": "web.yml", "job": x},
            {"check": y, "p50_s": 2000.0, "workflow_file": "api.yml", "job": y},
            {"check": z, "p50_s": 1500.0, "workflow_file": "docs.yml", "job": z},
        ],
    }, "findings": []}
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(doc), encoding="utf-8")
    out = bp.render(doc)
    head = _headline_line(out)
    # Minority → the presence-causal clause is faithful and rendered.
    assert "ran on only 9/20 sampled PRs, so a typical PR finishes in" in head, head
    causal = vr.check_headline_presence_causal_only_when_minority(out, findings)
    reconciled = vr.check_headline_floor_presence_reconciled(out, findings)
    assert causal.ok is True and not causal.skipped, causal.detail
    assert reconciled.ok is True and not reconciled.skipped, reconciled.detail
