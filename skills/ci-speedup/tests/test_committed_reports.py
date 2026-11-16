"""Guard for the worked-example reports under `reports/`.

DESIGN: the committed `reports/<repo>/blocking-path-speed.md` files are
DOCUMENTATION — illustrative worked examples you can open and read. They are NOT
the test input.

AMENDED 2026-07-08 (PR-G2, owner-decided). This file previously said committed
reports "are allowed to lag the renderer (a renderer improvement never forces a
manual report regen — that friction is what this design removes)". That promise is
withdrawn. It was never enforced either way, and in practice `langfuse` and
`mastra` drifted from the renderer silently while `psf/requests` shipped a skill
commit that a squash-merge had erased. Both were invisible behind a green suite.

The rule now: **a committed report must be exactly what today's renderer produces
from its committed `findings.json`, and must be stamped with a `scripts/` tree that
resolves in this checkout.** So a change to `scripts/` DOES force a re-render — but
re-rendering reads the committed `findings.json` and makes zero GitHub calls, so the
friction is one command, not a data re-collection. In exchange, the spec's §9
staging rule ("sizing changes ship with the refreshed worked examples") becomes
mechanical instead of remembered.

What IS gated:
- verify_report's invariants against a FRESH render of each committed
  `findings.json` (real, messy, repo-shaped data + the CURRENT renderer), so a
  genuine renderer↔verifier drift SURFACES rather than hiding behind an old render;
- the committed bytes themselves — equal to a fresh render, and provenance-clean.

The `findings.json` data-shape invariants live in `test_measured_evidence.py`;
the renderer's own conformance is also covered by the synthetic offline e2e
(`test_offline_pipeline_e2e.py`) and the check unit tests
(`test_verify_report_self.py`).
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_SKILL_DIR = Path(__file__).resolve().parents[1]
_TYPOGRAPHIC_DASHES = ("—", "–", "‒", "―", "−")

# Known pre-existing verify failures, tolerated PER-CHECK (never per-repo) so the
# other ~25 checks stay live on that repo — a whole-repo skip would mask any NEW
# regression there (and let a degenerate render pass). Each entry is also a
# self-expiring tripwire: the loop asserts the named check STILL fails, so when
# the underlying bug is fixed the carve-out goes stale and CI tells you to remove
# it. Currently EMPTY: mastra's "encord §6" spine-drop carve-out was retired once
# the renderer stopped framing a spine-dropped check on the merge-gating path.
_KNOWN_DRIFT: dict[str, set[str]] = {}
# A healthy report fires ~20 non-skipped checks; far below this means the render
# degraded (near-empty) or run_checks silently shrank — a vacuous-pass guard.
_MIN_CHECKS_FIRED = 12
_SPINE_DROPPED_CHECK = "no spine-dropped check is also framed on the merge-gating critical path"
_HEADLINE_CHECK = "headline 'slowest check' names the data layer's critical_path_check"


def _load_verify_report():
    # `verify_report` is not a unique module name (ci-secure ships one too), so load
    # THIS skill's by path under a unique name to avoid a cross-skill import clash.
    path = _SKILL_DIR / "tests" / "verify_report.py"
    name = "ci_speedup_verify_report"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # register first: its @dataclass resolves __module__ here
    spec.loader.exec_module(mod)
    return mod


def _load_blocking_path():
    """Load the renderer by path, under a unique name (same reason as verify_report:
    `blocking_path` is not a unique module name across skills)."""
    path = _SKILL_DIR / "scripts" / "blocking_path.py"
    name = "ci_speedup_blocking_path_for_tests"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _committed_findings() -> list[Path]:
    fs = sorted((_SKILL_DIR / "reports").glob("*/findings.json"))
    if not fs:
        # This public repo ships no committed worked-example corpus (the legacy
        # reports/ dir is not published; fresh examples come from a validation run).
        # The guard is NOT deleted — it runs again the moment a corpus reappears
        # (a generated examples/ report, or in the internal development repo). Skip
        # LOUDLY so the coverage gap is visible, never a silent vacuous pass.
        pytest.skip("no committed report corpora in this repo — corpus guards run "
                    "against generated reports / in the internal development repo")
    return fs


def _render_fresh(findings_path: Path, out_path: Path) -> str:
    """Render `findings.json` with the CURRENT renderer and return the markdown."""
    r = subprocess.run(
        [sys.executable, str(_SKILL_DIR / "scripts" / "blocking_path.py"),
         "--in", str(findings_path), "--out", str(out_path)],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"fresh render failed for {findings_path.parent.name}:\n{r.stderr}"
    report = out_path.read_text(encoding="utf-8")
    # A real report is thousands of chars; a near-empty exit-0 render would let the
    # dash/dead-end scans pass vacuously — assert it's substantial.
    assert len(report) > 2000, (
        f"fresh render of {findings_path.parent.name} is only {len(report)} chars — "
        "degenerate render (would pass content scans vacuously)")
    return report


def _has_modal_chain(findings_path: Path) -> bool:
    """True when the artifact stamps a modal `needs:` chain of >=2 members —
    the shape that renders the ENG-1 chain headline instead of the classic
    slowest-check one (the renderer keys on `chain_summary`, N2)."""
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    cp = data.get("pr_critical_path") if isinstance(data, dict) else {}
    if not isinstance(cp, dict):
        return False
    summary = cp.get("chain_summary")
    return isinstance(summary, dict) and len(summary.get("modal_chain") or []) >= 2


def test_z_spine_dropped_key_list_pinned_to_the_verifier():
    """PR-Z: `_has_spine_dropped_checks` below keys on exactly two dropped_*
    fields. If the verifier ever consults a THIRD `dropped_*` key under
    `pr_critical_path` that this gate doesn't, the corpus-level must-fire
    backstop silently narrows — a report could drop checks via the new key
    with this gate reading 'nothing dropped'. Source-lint the verifier."""
    import re as _re
    vr_src = (Path(__file__).parent / "verify_report.py").read_text(encoding="utf-8")
    consulted = set(_re.findall(r'cp\.get\("(dropped_[a-z_]+)"\)', vr_src))
    assert consulted == {"dropped_non_pr_checks", "dropped_non_required_checks"}, (
        f"verifier consults dropped-keys {sorted(consulted)}; update "
        "_has_spine_dropped_checks (and this pin) in the same change")


def _has_spine_dropped_checks(findings_path: Path) -> bool:
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    cp = data.get("pr_critical_path") if isinstance(data, dict) else {}
    if not isinstance(cp, dict):
        return False
    # Loud schema guard: every committed bundle carries at least one of the two
    # footnote keys (even when empty). If a data-layer rename removed both,
    # this gate and the verifier's identical skip test would go dark silently,
    # corpus-wide.
    assert ("dropped_non_pr_checks" in cp) or ("dropped_non_required_checks" in cp), (
        f"{findings_path.parent.name}: pr_critical_path carries neither "
        "dropped_non_pr_checks nor dropped_non_required_checks — schema drift "
        "would silently disable the spine-dropped must-fire gate")
    dropped = list(cp.get("dropped_non_pr_checks") or [])
    dropped += list(cp.get("dropped_non_required_checks") or [])
    return any(str(item).strip() for item in dropped)


@pytest.fixture(scope="module")
def fresh_reports(tmp_path_factory):
    """Render each committed findings.json ONCE (shared across the tests below) —
    a list of (repo, md_path, report_text)."""
    out_dir = tmp_path_factory.mktemp("fresh_reports")
    out = []
    for fj in _committed_findings():
        repo = fj.parent.name
        md = out_dir / f"{repo}.md"
        out.append((repo, fj, md, _render_fresh(fj, md)))
    return out


# The provenance footer is the ONE line that legitimately differs between a fresh
# render and the committed bytes: it stamps the renderer's own git state, so a dev
# with uncommitted `scripts/` edits renders `-dirty`. Normalize it out of the
# byte-equality comparison; `test_committed_reports_pass_provenance` (below) is what
# actually holds it to account, against the committed file rather than a fresh render.
_PROVENANCE_RE = re.compile(r"\(skill commit `[^`]*`(?:, scripts tree `[^`]*`)?\)")


def _sans_provenance(report: str) -> str:
    return _PROVENANCE_RE.sub("(skill commit `X`, scripts tree `X`)", report)


def test_committed_reports_match_a_fresh_render(fresh_reports):
    """Committed reports are DOCUMENTATION (#140) — the fresh render is the source of
    truth. Nothing enforced that, so `langfuse` and `mastra` silently drifted from the
    renderer for weeks (found 2026-07-08, PR-G2). Provenance aside, a committed report
    must be exactly what today's renderer produces from its committed findings.json."""
    stale = []
    for repo, fj, _md, fresh in fresh_reports:
        committed = (fj.parent / "blocking-path-speed.md").read_text(encoding="utf-8")
        if _sans_provenance(committed) != _sans_provenance(fresh):
            stale.append(repo)
    assert not stale, (
        f"committed report(s) no longer match a fresh render: {stale}. "
        "Re-render them (`blocking_path.py --in <findings.json> --out <report.md>`); "
        "this needs no GitHub calls.")


def test_committed_claims_sidecars_match_a_fresh_render(fresh_reports):
    """Rendering also writes `<report>.md.claims.json` beside the report. When that
    sidecar exists, `verify_report` switches to manifest-first comparison and binds
    each claim's rendered sentence to the report — a strictly stronger check. So the
    sidecar is part of the committed artifact and drifts the same way the report can.
    It is also why a re-render must not leave the sidecars untracked."""
    repo_root = _SKILL_DIR.parents[1]
    stale, missing, produced = [], [], 0
    for repo, fj, md, _fresh in fresh_reports:
        committed = fj.parent / "blocking-path-speed.md.claims.json"
        fresh = md.parent / (md.name + ".claims.json")
        if not fresh.exists():          # renderer emitted none for this corpus
            continue
        produced += 1
        # TRACKED, not merely present: a re-render writes the sidecar into the working
        # tree, so `exists()` passes even when the file was never committed. That is
        # precisely how three sidecars sat untracked while this guard read green.
        tracked = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", str(committed)],
            capture_output=True, text=True).returncode == 0
        if not committed.exists() or not tracked:
            missing.append(repo)
        elif json.loads(committed.read_text()) != json.loads(fresh.read_text()):
            stale.append(repo)
    # Vacuity guard. `if not fresh.exists(): continue` means a renderer that stops
    # emitting sidecars ENTIRELY skips every repo and both asserts below pass on empty
    # lists — the most basic regression this test claims to catch would sail through.
    assert produced == len(fresh_reports), (
        f"only {produced}/{len(fresh_reports)} fresh renders emitted a claims sidecar — "
        "the renderer stopped writing `<report>.md.claims.json`; verify_report's "
        "manifest-first checks would silently downgrade to prose parsing")
    assert not missing, (
        f"fresh render emits a claims sidecar for {missing} but none is COMMITTED — "
        "commit it beside the report; verify_report uses it for manifest-first checks")
    assert not stale, (
        f"committed claims sidecar(s) no longer match a fresh render: {stale}. "
        "Re-render; this needs no GitHub calls.")


# NOTE deliberately absent: a "fresh render carries the tree token" test. Any stamp
# regression is by definition a `scripts/` change, which makes the committed reports'
# tokens stale — `test_committed_reports_pass_provenance` goes red on the committed
# bytes in that same PR, and stays red after a re-render (token missing/wrong). A
# dedicated renderer-stamp test duplicated that coverage and carried its own bugs.


def test_renderer_marks_a_dirty_scripts_tree_dirty(tmp_path):
    """`git rev-parse HEAD:scripts` reads the COMMITTED tree. Without the `-dirty`
    suffix, a report rendered from uncommitted code stamps a clean tree it was not
    produced by — and then PASSES provenance. The suffix is the only thing preventing
    that self-vouching, and nothing exercised it: an adversarial mutation that deleted
    the suffix left the whole suite green. Drives the real function against a
    throwaway repo."""
    bp = _load_blocking_path()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "x.py").write_text("clean\n")
    # Isolate from the developer's global git config. On a machine that enforces commit
    # signing (`commit.gpgsign=true`) or installs global hooks, the commit below fails
    # and this test SKIPS — silently disabling the only guard on the `-dirty` suffix.
    iso = ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
           "-c", "user.email=t@t", "-c", "user.name=t"]
    for cmd in (["init", "-q"], ["add", "-A"], [*iso, "commit", "-qm", "base"]):
        r = subprocess.run(["git", "-C", str(tmp_path), *cmd], capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip(f"git unavailable: {r.stderr}")

    clean = bp._skill_scripts_tree_sha(scripts)
    assert clean and not clean.endswith("-dirty"), f"committed tree stamped {clean!r}"

    (scripts / "x.py").write_text("uncommitted edit\n")
    dirty = bp._skill_scripts_tree_sha(scripts)
    assert dirty == f"{clean}-dirty", (
        f"a dirty scripts/ tree must stamp `-dirty`, got {dirty!r} — without it a "
        "report rendered from uncommitted code vouches for itself")

    # Untracked files count too: a new module that never got added still changes what ran.
    (scripts / "x.py").write_text("clean\n")
    (scripts / "sneaky.py").write_text("untracked\n")
    assert bp._skill_scripts_tree_sha(scripts) == f"{clean}-dirty"


def test_scripts_tree_sha_never_raises_when_git_is_unusable(tmp_path, monkeypatch):
    """This runs on EVERY render, in an end user's repo. A `git` on PATH that cannot be
    executed raises PermissionError — an OSError, not a SubprocessError. Catching only
    the latter crashed the whole report render. Found by adversarial review."""
    bp = _load_blocking_path()
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "git").write_text("#!/bin/sh\nexit 0\n")     # present, NOT executable
    monkeypatch.setenv("PATH", str(fake))
    assert bp._skill_scripts_tree_sha(tmp_path) is None   # returns None, does not raise
    # And a plain non-repo directory yields no token rather than an exception.
    monkeypatch.undo()
    assert bp._skill_scripts_tree_sha(tmp_path) is None


def test_scripts_tree_sha_rejects_non_sha_output_from_a_wrapper_git(tmp_path, monkeypatch):
    """`sha` is whatever `git` printed. Corporate wrappers, aliases and lfs/hook shims
    routinely echo advisory lines to stdout. Without validation the renderer stamped
    that text verbatim into the Data-sources table — stray backticks, pipes and
    newlines break out of the markdown code span and corrupt the row, while asserting
    provenance that describes nothing. Found by adversarial review."""
    bp = _load_blocking_path()
    fake = tmp_path / "bin"
    fake.mkdir()

    def _fake_git(body: str) -> None:
        # `printf '%s\n'`, never `echo "…"` — a backtick inside double quotes is command
        # substitution, which makes the script a syntax error, so git exits non-zero and
        # the function returns None for the WRONG reason. (The first version of this
        # test did exactly that and passed while testing nothing.)
        (fake / "git").write_text(f"#!/bin/sh\n{body}\nexit 0\n")
        (fake / "git").chmod(0o755)

    monkeypatch.setenv("PATH", str(fake))

    # 1. Advisory text instead of a sha (a wrapper/shim git). Exits 0.
    _fake_git("printf '%s\\n' 'Warning: your git is managed by IT'")
    assert bp._skill_scripts_tree_sha(tmp_path) is None

    # 2. A plausible sha PLUS a trailing advisory line. `.strip()` leaves the embedded
    #    newline, which would split the markdown table row in two.
    _fake_git("printf '%s\\n' 'a1b2c3d' 'INJECTED | table | row'")
    assert bp._skill_scripts_tree_sha(tmp_path) is None

    # 3. Hex-looking but with markdown metacharacters appended.
    _fake_git("printf '%s\\n' 'a1b2c3d|pipe'")
    assert bp._skill_scripts_tree_sha(tmp_path) is None

    # 4. Control: a clean short sha IS accepted, so the guard is not vacuously rejecting.
    _fake_git("printf '%s\\n' 'a1b2c3d'")
    assert bp._skill_scripts_tree_sha(tmp_path) == "a1b2c3d-dirty"

    # 5. `git status` FAILS (broken index, hostile hook): dirtiness is unknown, so no
    #    token — never a clean-looking sha for a tree that might be dirty (greptile P1
    #    on the first cut: st.returncode was missing from the null guard, so a failing
    #    status silently stamped clean).
    (fake / "git").write_text(
        "#!/bin/sh\ncase \"$*\" in *status*) exit 1;; esac\n"
        "printf '%s\\n' 'a1b2c3d'\nexit 0\n")
    (fake / "git").chmod(0o755)
    assert bp._skill_scripts_tree_sha(tmp_path) is None


# ---- PR-P1 contract: the section lead accounts for 100% of positive-saving findings.
#
# The decision table (per finding with positive runner_min_saving, not advisory /
# tier2-superseded / wait-pattern):
#   promoted (source-backed R-row)          -> the "K neutral findings" count
#   measured + certificate + not backed     -> "without source rows"        (B)
#   measured + no certificate               -> "certificate-deferred"       (C)
#   modeled                                 -> "modeled"                    (D)
#   OPT73 (the ONE structural pattern with a credited runner-minute saving,
#     per _is_pole_structural's contract)   -> "structural shared-step"     (E)
#   anything else                           -> "other": rendered visibly, and the
#                                              verifier FAILS (unaccountable)
# Invariant: K + B + C + D + E == every positive-saving eligible finding, and
# other == 0. The old "+J unmeasured item(s)" counter violated all of this: it
# called C and E "unmeasured", and counted B nowhere at all (G1; the audit's own
# composition of the +6 was wrong too — re-derived from the corpus 2026-07-09).
# Scope: stamped artifacts only — the tier2 lead never renders on pre-stamp
# corpora (better-auth/langfuse/mastra), whose findings carry no sizing_basis.


def test_requests_lead_accounts_for_all_positive_savings(fresh_reports):
    """PR-P1 acceptance, on the real demo corpus (exit criterion item 1).

    On requests, post-PR-S2 (R1 WIDE attribution): 9 promoted — the four OPT64s
    (f22-f25) that PR-P1's B-bucket used to count as "without source rows" now
    bind to the workflow's full prior-attempt row set and promote (D3-rev1's
    binding condition, discharged). Remaining unpromoted: C=1 (f27, OPT47: the
    repo's largest measured lever, certificate PARKED per §12/OD1-S1); D=4
    (f2,f8,f9,f14: modeled); E=1 (f34, OPT73: the structural shared-step lever,
    832.8 min/mo credited, on-path here)."""
    report = next(rep for repo, _fj, _md, rep in fresh_reports if repo == "requests")
    assert "unmeasured item(s) remain in Also noticed" not in report, (
        "the old mislabeling counter still renders — C-class findings are not "
        "'unmeasured' and B-class was counted nowhere")
    assert ("not promoted: 1 measured item(s) (1 certificate-deferred) · "
            "4 modeled item(s) · "
            "1 structural shared-step item(s); see Also noticed") in report
    assert "without source rows" not in report, (
        "the B-bucket must be EMPTY on requests after PR-S2's wide binding — "
        "a reappearing demotion means the OPT64 source binding regressed")
    # Appendix reason class: OPT47's group must say the certificate is deferred.
    assert "certificate is deferred" in report, "OPT47 appendix note missing"
    # The four OPT64s now render as R-rows carrying their certificate class.
    assert "post_completion_waste" in report, (
        "promoted OPT64 rows must render the stamped certificate class")


def test_committed_reports_pass_provenance():
    """The skill code that produced each committed report must be inspectable HERE.

    Previously `run_checks(..., skill_repo=None)` made this check report `skipped`,
    which counts as a pass — so the committed `psf/requests` report rode a green suite
    while its recorded skill commit (`60b1cea`) had been squashed out of history by
    #179 and could never resolve on `main`. A check that silently degrades to
    "skipped" is not a check. This runs it against the real checkout.

    Reads the COMMITTED bytes, not a fresh render: a fresh render stamps the dev's
    current git state, so it would pass vacuously (and fail spuriously on a dirty tree).
    """
    vr = _load_verify_report()
    repo_root = _SKILL_DIR.parents[1]
    if not (repo_root / ".git").exists():          # installed copy / tarball: nothing to compare
        pytest.skip("not a git checkout")
    failures = []
    for fj in _committed_findings():
        md = fj.parent / "blocking-path-speed.md"
        c = vr.check_skill_commit_provenance(md.read_text(encoding="utf-8"), repo_root)
        if c.skipped:
            failures.append(f"{fj.parent.name}: provenance SKIPPED against a real checkout "
                            "— the check degraded instead of running")
        elif not c.ok:
            failures.append(f"{fj.parent.name}: {c.detail}")
    assert not failures, "committed report provenance:\n  " + "\n  ".join(failures)


def test_fresh_render_has_no_typographic_dashes(fresh_reports):
    # The renderer's `_strip_emdashes` boundary must keep output ASCII-only. Tested
    # on a FRESH render so it catches a renderer regression, not a frozen snapshot.
    offenders = []
    for repo, _fj, _md, report in fresh_reports:
        found = sorted({g for g in _TYPOGRAPHIC_DASHES if g in report})
        if found:
            offenders.append(f"{repo} ({''.join(found)})")
    assert not offenders, f"typographic dash in fresh render(s): {offenders}"


def test_fresh_render_has_no_coverage_gap_dead_end(fresh_reports):
    # A drilled pole matching no catalog detector must be filled by the phase-4a
    # LLM gap-fill, never left as a "no drill-down available" dead-end.
    offenders = []
    for repo, _fj, _md, report in fresh_reports:
        if "no drill-down available" in report:
            offenders.append(repo)
    assert not offenders, f"fresh render ships a coverage-gap dead-end: {offenders}"


def test_fresh_render_passes_verify_report_invariants(fresh_reports):
    # verify_report over a FRESH render of each committed findings.json (real data,
    # current renderer). Never stale; a real renderer/verifier drift fails here.
    # EVERY repo runs the FULL check set — a repo is never skipped wholesale; only
    # the specific checks in _KNOWN_DRIFT are tolerated (and asserted to still fail).
    vr = _load_verify_report()
    # Phase-0 cross-seam-contradiction checks key on rendered prose. A headline
    # check must always fire — WHICH one depends on the artifact's gate shape
    # (ENG-1): a stamped modal `needs:` chain of >=2 members renders the CHAIN
    # headline (the classic slowest-check check legitimately skips there), so
    # the chain re-derivation check must fire instead. The spine-dropped check
    # must fire only for reports whose findings actually dropped checks from
    # the PR spine; clean reports should skip it rather than inventing a
    # contradiction surface.
    _ALWAYS_MUST_FIRE = {_HEADLINE_CHECK}
    _CHAIN_HEADLINE_CHECK = "chain headline re-derives from the stamped chain facts"
    _CEILING = "pole addressable ceiling within the co-occurrence floor"
    ceiling_fired_anywhere = False
    spine_dropped_fired_anywhere = False
    failures: list[str] = []
    for repo, fj, md, report in fresh_reports:
        known = _KNOWN_DRIFT.get(repo, set())
        fired: set[str] = set()
        failed: set[str] = set()
        for c in vr.run_checks(report, md, fj, skill_repo=None):
            if c.skipped:
                continue
            fired.add(c.name)
            if not c.ok:
                failed.add(c.name)
                if c.name not in known:  # a NEW / non-tolerated failure — surface it
                    failures.append(f"{repo}: {c.name} - {c.detail}")
        # Breadth floor: too few checks fired ⇒ degraded render / shrunk run_checks.
        if len(fired) < _MIN_CHECKS_FIRED:
            failures.append(f"{repo}: only {len(fired)} checks fired (< {_MIN_CHECKS_FIRED}) — "
                            "render degraded or run_checks shrank (vacuous-pass risk)")
        # Self-expiring tripwire: each tolerated check must STILL fail; if it now
        # passes, the underlying bug is fixed → remove the carve-out.
        for k in known:
            if k not in failed:
                failures.append(f"{repo}: _KNOWN_DRIFT carve-out {k!r} is stale — it no longer "
                                "fails, so remove it from _KNOWN_DRIFT")
        if _CEILING in fired:
            ceiling_fired_anywhere = True
        if _SPINE_DROPPED_CHECK in fired:
            spine_dropped_fired_anywhere = True
        must_fire = ({_CHAIN_HEADLINE_CHECK} if _has_modal_chain(fj)
                     else set(_ALWAYS_MUST_FIRE))
        if _has_spine_dropped_checks(fj):
            must_fire.add(_SPINE_DROPPED_CHECK)
        for missing in sorted(must_fire - fired):
            failures.append(f"{repo}: Phase-0 check SKIPPED (renderer/verifier wording "
                            f"drift?): {missing!r}")
    if not ceiling_fired_anywhere:
        failures.append("the #4 ceiling check SKIPPED on EVERY fresh-verified report — its "
                        "regex likely went dark against the current renderer (format drift)")
    if not spine_dropped_fired_anywhere:
        failures.append("the spine-dropped Phase-0 check SKIPPED on EVERY fresh-verified "
                        "report — its trigger data went dark corpus-wide (schema/data-layer "
                        "drift?); at least one committed report must exercise it")
    assert not failures, "fresh-render verify_report invariant failures:\n" + "\n".join(failures)
