"""Class-level guard for the REQUIRED-STATUS claim class (the §③(c) other half).

The "langfuse" class — the bug the whole faithful-derivation campaign is named
for — is: the skill headlines a check as the thing gating your merge when it
isn't actually merge-blocking. The PRODUCER fix landed earlier (`_pole_provenance`
stamps `required_scoped` only when the spine is required-scoped AND the headlined
pole is itself required-reachable via `_pole_is_required_reachable`; the
ci-harness auto-fixer HALTs on anything else). The decision table and the
reachability separation are unit-tested in `test_structural_findings.py`.

What those unit tests DON'T lock is the two ways the fix can silently rot:

  A. WIRING — the existing wiring guard (`test_evidence_claim_guards.py`
     invariant 5) only asserts `cp["provenance"] = _pole_provenance(...)` is
     CALLED. It does NOT assert the third argument is the real
     `_pole_is_required_reachable(...)` computation. A refactor that passed a
     hardcoded `True` there would re-open the langfuse hole (every narrowed-spine
     pole stamped `required_scoped`, harness consumes without HALT) and stay
     green. This guard pins the argument.

  B. RENDER DISCLOSURE — when the pole is NOT a confirmed required gate (required
     checks unreadable, or the required suite is external/managed and ran on no
     sampled PR), the report must DISCLOSE that — never present an unconfirmed
     pole as a confirmed required/merge-gating check. This drives the renderer's
     `_provenance_block` over each unconfirmed state and asserts the hedge is
     emitted (and is absent on a genuinely-confirmed gate).

Together with the producer unit tests, this closes the required-status claim
class the same way §③(b)/§③(c)-PR-scope closed their classes.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parents[1]
_SCRIPTS = _SKILL_DIR / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import collect_runs as cr  # noqa: E402  (uniquely-named module; no cross-skill clash)
import blocking_path as bp  # noqa: E402


# --------------------------------------------------------------------------- #
# A. WIRING — `required_scoped` must stay gated on the REAL reachability call
# --------------------------------------------------------------------------- #
def _func_name(node: ast.AST) -> str | None:
    """The called function's bare name for an ast.Call func (`f(...)` → 'f',
    `mod.f(...)` → 'f')."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _provenance_stamp_third_arg() -> ast.expr:
    """The AST node for the THIRD positional argument of the
    `cp["provenance"] = _pole_provenance(...)` assignment in collect_runs.py.
    AST (not text/regex) so the check is robust to reformatting, comments, and
    string-literal parens — the regex form was inert on the real call shape (the
    `)` inside `cp.get("gate_kind")` stopped a `[^)]*` scan before the 3rd arg)."""
    tree = ast.parse((_SCRIPTS / "collect_runs.py").read_text(encoding="utf-8"))
    found: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        tgt = node.targets[0] if node.targets else None
        if (isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name)
                and tgt.value.id == "cp"
                and isinstance(tgt.slice, ast.Constant) and tgt.slice.value == "provenance"
                and isinstance(node.value, ast.Call)
                and _func_name(node.value.func) == "_pole_provenance"):
            found.append(node.value)
    assert len(found) == 1, (
        f"expected exactly one `cp['provenance'] = _pole_provenance(...)` stamp in "
        f"collect_runs.py, found {len(found)} — the wiring guard can't locate it")
    call = found[0]
    assert len(call.args) >= 3, (
        "`_pole_provenance(...)` is called with fewer than 3 positional args — the "
        "pole-reachability argument (which keeps `required_scoped` honest) is missing")
    return call.args[2]


def _is_live_reachability_arg(arg: ast.expr) -> bool:
    """The single accept/reject decision the wiring guard enforces: the stamp's
    reachability argument is honest IFF it's a live `_pole_is_required_reachable(...)`
    CALL — not a literal (`True`), a name, a `BoolOp` (`... or True`), or any other
    expression. The real guard AND its self-test both route through this, so the
    self-test can't pass while the real decision is weakened."""
    return isinstance(arg, ast.Call) and _func_name(arg.func) == "_pole_is_required_reachable"


def test_provenance_required_scoped_is_gated_on_real_reachability():
    """The provenance stamp's third argument (pole_required_reachable) must be the
    live `_pole_is_required_reachable(...)` CALL — not a hardcoded `True` / other
    literal — or a narrowed spine would stamp `required_scoped` on an unconfirmed
    pole and re-open the langfuse hole while the suite stays green."""
    arg = _provenance_stamp_third_arg()
    assert _is_live_reachability_arg(arg), (
        "the provenance stamp's 3rd argument is no longer a live "
        "`_pole_is_required_reachable(...)` call (got "
        f"{type(arg).__name__}: {ast.dump(arg)}) — a narrowed spine could stamp "
        "`required_scoped` on a pole that isn't confirmed merge-blocking (the langfuse "
        "hole). NOTE: extracting the call to a local variable also trips this by design "
        "— inline it, or update the guard to follow the binding.")


def test_wiring_guard_decision_accepts_live_call_rejects_literal_and_wrappers():
    """Exercise the guard's ACTUAL decision (`_is_live_reachability_arg`) — not a
    re-implementation — so weakening the real predicate is caught here too. The
    live call is accepted; a hardcoded `True`, a name alias, and a `... or True`
    wrapper are all rejected."""
    def third_arg(code: str) -> ast.expr:
        return ast.parse(code).body[0].value.args[2]
    stamp = 'cp["provenance"] = _pole_provenance(cp.get("gate_kind"), s, %s)'
    assert _is_live_reachability_arg(third_arg(stamp % "_pole_is_required_reachable(x, y, z, w)"))
    for defeated in ("True", "reach_alias", "_pole_is_required_reachable(x, y, z, w) or True"):
        assert not _is_live_reachability_arg(third_arg(stamp % defeated)), defeated


def test_pole_provenance_required_scoped_requires_both_conditions():
    """Decision-table invariant (composition contract): `required_scoped` is
    returned IFF the gate isn't the PR-floor fallback AND the spine is
    required-scoped AND the pole is required-reachable. Any single condition
    false → never `required_scoped`. (Complements the per-condition unit tests by
    asserting the full truth table at once, so a future re-ordering can't let a
    two-of-three case through.)"""
    p = cr._pole_provenance
    for gate_kind in (None, "branch_protection", "pr_floor_fallback"):
        for spine in (True, False):
            for reachable in (True, False):
                got = p(gate_kind, spine, reachable)
                expect_scoped = (gate_kind != "pr_floor_fallback"
                                 and spine and reachable)
                if expect_scoped:
                    assert got == "required_scoped", (gate_kind, spine, reachable, got)
                else:
                    assert got != "required_scoped", (
                        f"{(gate_kind, spine, reachable)} wrongly stamped required_scoped")


def test_pole_required_reachable_rejects_unpinnable_and_independent_keeps():
    """A pole is required-reachable ONLY when it's a required check or a job the
    required work `needs:`. A file-backed check that's kept on the spine but is
    neither (an independent sibling, or an unpinnable cat-3 keep) must be rejected
    — that rejection is what stops it being stamped `required_scoped`. This drives
    the live helper over the langfuse shape so a future loosening of reachability
    that re-admits such a pole fails here."""
    job_graph = {".github/workflows/ci.yml": {
        "build": {"name": "build", "needs": []},
        "test": {"name": "test", "needs": ["build"]},   # required `needs:` build
        "indep": {"name": "indep", "needs": []},        # independent sibling
    }}
    crit_by_wf = {".github/workflows/ci.yml": {
        "job_p50": {"build": 100.0, "test": 300.0, "indep": 400.0}}}
    req = frozenset({"test"})
    R = cr._pole_is_required_reachable
    assert R("test", req, job_graph, crit_by_wf) is True    # the required check itself
    assert R("build", req, job_graph, crit_by_wf) is True   # required work needs: it
    assert R("indep", req, job_graph, crit_by_wf) is False  # independent → not merge-blocking
    assert R("ghost", req, job_graph, crit_by_wf) is False  # cat-3: maps to no job node → not reachable
    # The composition the langfuse fix depends on: an independent pole on a
    # required-scoped spine must NOT end up `required_scoped`.
    assert cr._pole_provenance(
        None, True, R("indep", req, job_graph, crit_by_wf)) == "unresolved"


# --------------------------------------------------------------------------- #
# B. RENDER DISCLOSURE — an unconfirmed gate must be disclosed, never asserted
# --------------------------------------------------------------------------- #
def _provenance_lines(cp: dict) -> str:
    """Run the renderer's provenance block over a minimal doc carrying `cp`, and
    return its text. Only the required-suite fields drive the branches under test."""
    doc = {
        "scanned_at": "2026-06-01T00:00:00Z",
        "data_sources": {"runs_sampled": 20, "jobs_sampled": 40,
                         "workflows_analyzed": 3},
        "pr_critical_path": cp,
    }
    return "\n".join(bp._provenance_block(doc, "o/r", "2026-06-01"))


_CONFIRMED_REQUIRED_HEDGE = "confirmed required"      # "...not a *confirmed required* check"
_NO_FILE_BACKED_GATE = "No file-backed required gate"


def test_unreadable_required_checks_are_disclosed_not_asserted():
    """Required checks unreadable (no admin / branch-protection 404): the report
    must say 'gate' means the slowest observed check, NOT a confirmed required one."""
    cp = {"sampled_pr_count": 12, "sample_target": 20, "sample_complete": True,
          "required_suite_scoped": False, "required_suite_unsatisfiable": False}
    text = _provenance_lines(cp)
    assert _CONFIRMED_REQUIRED_HEDGE in text, (
        "required checks were unreadable, but the provenance block does not disclose "
        "that the 'gate' is the slowest OBSERVED check rather than a confirmed required "
        "one — an unconfirmed pole presented as a confirmed required gate (langfuse class)")


def test_external_only_required_suite_is_disclosed_as_pr_floor():
    """Required suite readable but external/managed and ran on no sampled PR: the
    report must disclose there's no file-backed required gate (the spine is the
    PR-floor), not headline a file-backed check as the required gate."""
    cp = {"sampled_pr_count": 12, "sample_target": 20, "sample_complete": True,
          "required_suite_scoped": False, "required_suite_unsatisfiable": True}
    text = _provenance_lines(cp)
    assert _NO_FILE_BACKED_GATE in text, (
        "the required suite is external-only (no file-backed gate), but the provenance "
        "block doesn't disclose the spine is the measured PR-floor — a file-backed check "
        "would read as the confirmed required gate")


def test_confirmed_required_gate_emits_no_false_hedge():
    """Positive control: a genuinely required-scoped gate must NOT emit either
    'unreadable' or 'no file-backed gate' hedge — the disclosure is reserved for
    the unconfirmed states, so it stays meaningful."""
    cp = {"sampled_pr_count": 18, "sample_target": 20, "sample_complete": True,
          "required_suite_scoped": True, "required_suite_unsatisfiable": False}
    text = _provenance_lines(cp)
    assert _CONFIRMED_REQUIRED_HEDGE not in text, text
    assert _NO_FILE_BACKED_GATE not in text, text
    # Non-vacuity: the block must actually have rendered content (the gate line).
    assert "Which checks gate" in text
