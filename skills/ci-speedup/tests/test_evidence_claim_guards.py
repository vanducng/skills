"""Class-level guards for ci-speedup detector *claims*.

These are PROPERTY tests, not single-detector regressions. They run the
detectors against adversarial workflow shapes and fail ANY detector — present
or future — whose evidence asserts a workflow-shape fact that isn't true of the
input. They exist because the same meta-bug kept recurring across detectors: a
report claiming something it never checked against the data —

  - OPT32 said a workflow "triggers on pull_request/push" even when it was
    push-only (or PR-only);
  - OPT73 / OPT24 called `needs:`-chained (serial) jobs "concurrent" / "in
    parallel" off their durations alone.

A per-detector regression only nails the one instance; these guards assert the
INVARIANT, so a detector that grows the same falsehood fails in CI instead of on
a real repo during a dogfood run.

Two invariants, with different reach:
  1. No finding's evidence may name a workflow trigger absent from its `on:`.
     Runs `scan.py` over the fixtures and inspects EVERY finding from EVERY
     detector that fires — genuinely surface-wide.
  2. No detector may label a `needs:`-chained job "in parallel". Driven through
     OPT24 as the representative (the assertion is written generically over any
     Role-column finding, but only OPT24 flows through the fixture today). OPT73,
     the other concurrency-claiming detector, has its own regression test in
     test_structural_findings.py.

The three original instances of this class — OPT32's trigger string and OPT73's
+ OPT24's concurrency wording — are all fixed; these guards lock the invariants
in so the next detector to regress is caught here.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_SKILL_DIR = Path(__file__).resolve().parents[1]
_SCRIPTS = _SKILL_DIR / "scripts"
_SCAN_SCRIPT = _SCRIPTS / "scan.py"
sys.path.insert(0, str(_SCRIPTS))

import collect_runs as cr  # noqa: E402  (uniquely-named module; no cross-skill clash)


# --------------------------------------------------------------------------- #
# Invariant 1 — evidence must not name a trigger the workflow doesn't declare
# --------------------------------------------------------------------------- #

_ALL_TRIGGERS = ("pull_request", "push", "schedule", "workflow_dispatch",
                 "workflow_call", "merge_group")

# A single workflow body rich enough to fire several static detectors (unpinned
# actions, full-history checkout, no concurrency group), reused under each
# single-trigger `on:` block so the present/absent trigger set is unambiguous.
_GUARD_BODY = (
    "jobs:\n"
    "  build:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - uses: actions/checkout@v3\n"
    "        with:\n"
    "          fetch-depth: 0\n"
    "      - uses: actions/setup-node@v3\n"
    "      - run: npm ci && npm run build\n"
    "  test:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - uses: actions/checkout@v3\n"
    "      - run: npm test\n"
)

_TRIGGER_FIXTURES = {
    "push": "on:\n  push:\n    branches: [main]\n",
    "pull_request": "on:\n  pull_request:\n",
    "schedule": "on:\n  schedule:\n    - cron: '0 0 * * *'\n",
    "workflow_dispatch": "on:\n  workflow_dispatch:\n",
}


def _have_yaml() -> bool:
    return subprocess.run(
        [sys.executable, "-c", "import yaml"], capture_output=True, text=True,
    ).returncode == 0


def _scan(root: Path) -> dict:
    if not _have_yaml():
        pytest.skip("PyYAML not installed in the test runner")
    result = subprocess.run(
        [sys.executable, str(_SCAN_SCRIPT), "--root", str(root)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("present", sorted(_TRIGGER_FIXTURES))
def test_no_finding_claims_an_absent_trigger(tmp_path: Path, present: str):
    """Scan a workflow that declares exactly ONE trigger; no finding's evidence
    may name any of the OTHER triggers as a fact about this workflow. That is
    only possible when a detector hardcodes a trigger string instead of deriving
    it from the parsed `on:` block (the OPT32 class)."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "ci.yml").write_text(
        "name: CI\n" + _TRIGGER_FIXTURES[present] + _GUARD_BODY, encoding="utf-8")
    data = _scan(tmp_path)
    # Non-vacuous sentinel: the fixture is built to fire detectors, so an empty
    # scan means detector gating drifted and this guard is silently enforcing
    # nothing — fail loudly instead of passing on zero findings.
    assert data["findings"], (
        f"`{present}`-only fixture produced no findings — the trigger guard would "
        "pass vacuously; refresh _GUARD_BODY so it exercises real detectors")
    absent = [t for t in _ALL_TRIGGERS if t != present]
    offenders: list[str] = []
    for f in data["findings"]:
        # Check both the static `evidence` and any measured-evidence summary — a
        # trigger claim could live in either prose field.
        text = (f.get("evidence") or "") + " " + (
            (f.get("measured_evidence") or {}).get("summary") or "")
        for t in absent:
            if re.search(rf"\b{re.escape(t)}\b", text):
                offenders.append(
                    f"{f['pattern']} names absent trigger `{t}` — text: {text[:140]}")
    assert not offenders, (
        f"a `{present}`-only workflow produced evidence naming triggers it does "
        f"not declare (claim not derived from `on:`):\n  " + "\n  ".join(offenders))


# --------------------------------------------------------------------------- #
# Invariant 2 — a `needs:`-chained job must never be described as concurrent
# --------------------------------------------------------------------------- #

def _job(name: str, dur_s: int, job_id: int) -> dict:
    return {
        "name": name,
        "started_at": "2026-05-29T10:00:00Z",
        "completed_at": f"2026-05-29T10:{dur_s // 60:02d}:{dur_s % 60:02d}Z",
        "run_id": 111,
        "html_url": f"https://github.com/o/r/actions/runs/111/job/{job_id}",
    }


def test_no_detector_labels_a_needs_chained_job_concurrent():
    """A job wired downstream via `needs:` runs serially, so a detector that
    renders a per-job "Role" must not call it parallel/concurrent. This is driven
    through OPT24's long-pole table as the representative; the assertion is written
    generically over any finding carrying a Role column, so it ports to other
    Role-column detectors once they are added to this fixture (today only OPT24
    flows through it — a future detector needing a different workflow shape would
    need its own fixture here). OPT73's own concurrency wording has a dedicated
    regression test in test_structural_findings.py and does not flow through this
    fixture."""
    runs = [[_job("test", 440, 1000 + r), _job("deploy", 60, 2000 + r)]
            for r in range(3)]
    doc = {"jobs": {
        "test": {"runs-on": "ubuntu-latest"},
        "deploy": {"needs": ["test"], "runs-on": "ubuntu-latest"},  # serial, after test
    }}
    findings = cr._detect_opt24_long_test_no_sharding("ci.yml", runs, 0, wf_doc=doc)
    assert findings, "fixture should produce an OPT24 long-test finding"
    offenders: list[str] = []
    checked_role_column = False
    for f in findings:
        tbl = (f.get("measured_evidence") or {}).get("table") or {}
        headers = tbl.get("headers") or []
        if "Role" not in headers:
            continue
        checked_role_column = True
        role_idx = headers.index("Role")
        for row in tbl.get("rows") or []:
            job, role = row[0], (row[role_idx] or "").lower()
            # `deploy` is `needs:`-chained to the long pole — it runs AFTER it.
            if "deploy" in job and ("in parallel" in role or "concurrent" in role):
                offenders.append(f"{f['pattern']} labels needs-chained {job} `{role}`")
    # Non-vacuous sentinel: if the "Role" header is ever renamed the loop above
    # would skip every row and pass while enforcing nothing — fail loudly instead.
    assert checked_role_column, (
        "no finding carried a `Role` column — the concurrency guard inspected "
        "nothing; the OPT24 table header may have been renamed")
    assert not offenders, (
        "a `needs:`-chained job was labeled as running concurrently:\n  "
        + "\n  ".join(offenders))


# --------------------------------------------------------------------------- #
# Invariant 3 — a single-job finding must anchor INSIDE that job's block
# --------------------------------------------------------------------------- #
# The line-anchor analog of the claim guards: a finding scoped to one job points
# the reader at a line number. If the detector locates that line with a
# file-global substring search for a non-unique needle (`needs:`, `setup-node`,
# `max-parallel: 1`, `fail-fast: false`, `language`, a short job name), it lands
# on the FIRST match in the file — which, in a multi-job workflow, is usually a
# DIFFERENT job. This is the wrong-job hazard shared by every `_line_of_in_job`
# caller (OPT28/OPT33/OPT29/OPT21/OPT27/OPT39/OPT23/OPT35/OPT5). The fix is
# `_line_of_in_job` (which now returns 0 rather than a file-global match when the
# job block or needle can't be located); this guard fails any detector
# that emits a single-job finding on one of the fixtures below if it regresses
# to a file-global anchor. Each fixture has two near-identical jobs (`early`,
# `late`) so the LATER job exposes the bug — its in-block match differs from the
# file-global first match (which lands in `early`). Detectors keyed to other
# workflow shapes need their own fixture added here (and OPT39, which needs a
# `language` matrix, is covered by its per-detector test in test_scan_detectors).
_ANCHOR_FIXTURES = {
    # OPT21 (orphan `needs:`) + OPT27 (duplicate `setup-node`) on both jobs.
    "orphan-needs+dup-setup-node": """name: CI
on: pull_request
jobs:
  early:
    runs-on: ubuntu-latest
    needs: [seed]
    steps:
      - uses: actions/setup-node@v3
      - uses: actions/setup-node@v3
      - run: docker compose up
  late:
    runs-on: ubuntu-latest
    needs: [seed]
    steps:
      - uses: actions/setup-node@v3
      - uses: actions/setup-node@v3
      - run: docker compose up
  seed:
    runs-on: ubuntu-latest
    steps:
      - run: echo seed
""",
    # OPT23 (`max-parallel: 1`) + OPT35 (`fail-fast: false` on a shard matrix).
    "matrix-serialized+no-failfast": """name: CI
on: pull_request
jobs:
  early:
    runs-on: ubuntu-latest
    strategy:
      max-parallel: 1
      fail-fast: false
      matrix:
        shard: [1, 2]
    steps:
      - run: echo ${{ matrix.shard }}
  late:
    runs-on: ubuntu-latest
    strategy:
      max-parallel: 1
      fail-fast: false
      matrix:
        shard: [1, 2]
    steps:
      - run: echo ${{ matrix.shard }}
""",
    # OPT1/OPT2 (playwright install, unused + uncached), OPT9 (eslint no cache flag),
    # OPT17 (sleep-based readiness in a docker-service job) — all per-job, none of
    # which trips the fixtures above, so they exercise the newly job-scoped anchors.
    "playwright+eslint+sleep": """name: CI
on: pull_request
jobs:
  early:
    runs-on: ubuntu-latest
    services:
      db:
        image: postgres
    steps:
      - run: npx eslint .
      - run: npx playwright install
      - run: docker compose up
      - run: sleep 15
  late:
    runs-on: ubuntu-latest
    services:
      db:
        image: postgres
    steps:
      - run: npx eslint .
      - run: npx playwright install
      - run: docker compose up
      - run: sleep 15
""",
    # OPT5 (pnpm store not cached) on both jobs.
    "pnpm-no-cache": """name: CI
on: pull_request
jobs:
  early:
    runs-on: ubuntu-latest
    steps:
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
      - run: pnpm install
  late:
    runs-on: ubuntu-latest
    steps:
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
      - run: pnpm install
""",
}


def _job_blocks(content: str) -> dict:
    """{job_key: (first_line, last_line)} 1-based, spanning each job's text from
    its header to the line before the next job header at the same indent (mirrors
    `_line_of_in_job`, including its dynamic job-indent detection)."""
    lines = content.splitlines()
    jobs_at = next((i for i, ln in enumerate(lines)
                    if re.match(r"^jobs:\s*(#.*)?$", ln)), None)
    if jobs_at is None:
        return {}
    indent = next((len(m.group(1))
                   for ln in lines[jobs_at + 1:]
                   if ln.strip() and not ln.lstrip().startswith("#")
                   and (m := re.match(r"^(\s+)\S", ln))), None)
    if not indent:
        return {}
    hdr = re.compile(rf"^\s{{{indent}}}([A-Za-z0-9_.-]+):\s*(#.*)?$")
    heads = [(i, m.group(1)) for i, ln in enumerate(lines)
             if (m := hdr.match(ln)) and i > jobs_at]
    blocks = {}
    for k, (i, name) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        blocks[name] = (i + 1, end)
    return blocks


@pytest.mark.parametrize("label", sorted(_ANCHOR_FIXTURES))
def test_single_job_finding_anchors_inside_its_own_block(tmp_path: Path, label: str):
    """Every finding scoped to exactly one job must put its `line` inside that
    job's block — never on a file-global first match in a different job."""
    content = _ANCHOR_FIXTURES[label]
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "ci.yml").write_text(content, encoding="utf-8")
    data = _scan(tmp_path)
    blocks = _job_blocks(content)
    offenders, checked_late = [], False
    for f in data["findings"]:
        jobs = f.get("affected_jobs") or []
        if len(jobs) != 1:
            continue                       # workflow-level finding — not job-anchored
        job = jobs[0]
        span = blocks.get(job)
        if span is None:
            continue
        if job == "late":
            checked_late = True            # the second job exposes the hazard
        # `line or 0` also flags a finding that couldn't locate any line (0): a
        # job-scoped finding with no anchor is itself a defect, not a pass.
        line = f.get("line") or 0
        if not (span[0] <= line <= span[1]):
            offenders.append(
                f"{f['pattern']} (job `{job}`) anchored at line {line}, outside "
                f"its block {span} — file-global needle hit another job")
    # Non-vacuous sentinel: the LATER job must produce a checkable per-job finding
    # (only it can expose the bug), else a gating change could make this guard
    # pass trivially.
    assert checked_late, (
        f"[{label}] no single-job finding fired on `late` — the anchor guard "
        "checked nothing; refresh the fixture so the second job trips a detector")
    assert not offenders, (
        f"[{label}] a single-job finding anchored outside its job's block:\n  "
        + "\n  ".join(offenders))


# --------------------------------------------------------------------------- #
# Invariant 4 — SOURCE GUARD: no detector may anchor via the file-global
# `_line_of`; per-job findings must use `_line_of_in_job`
# --------------------------------------------------------------------------- #
# Invariant 3 (above) is BEHAVIORAL — it only catches detectors that fire on its
# sample fixtures, which is exactly why OPT1/OPT2/OPT9/OPT16/OPT18/OPT31/OPT62/
# OPT63/OPT6/OPT40/OPT17 slipped past it (they don't trip those fixtures). This
# guard closes the class STRUCTURALLY, for every detector at once — present and
# future — by scanning the scanner's source: `_line_of(raw, needle)` returns the
# FIRST file-global match, which in a multi-job workflow is usually a DIFFERENT
# job's line (and, for detectors that set `snippet=_raw_line(...)`, pastes that
# other job's YAML as the evidence). A per-job finding must scope its line to its
# own block via `_line_of_in_job(raw, job_name, needle)`.
#
# The ONLY legitimate file-global `_line_of` anchors are genuinely workflow-level
# findings — a `schedule.cron` that gates every job, or a declarative `yaml_path`
# finding with `affected_jobs=[]` — each tagged with an explicit
# `# anchor:workflow-level` marker on its call line. Any new, unmarked `_line_of(`
# call fails this guard, forcing the author to either job-scope it or consciously
# mark it workflow-level.
_WORKFLOW_LEVEL_MARKER = "anchor:workflow-level"


def _file_global_anchor_offenders(src: str) -> list[str]:
    """Lines in `src` that anchor via the file-global `_line_of(...)` and are not
    allow-listed. Robust to a MIXED line carrying both `_line_of(` and the
    job-scoped `_line_of_in_job(`: we delete the OK helper's calls first, so a bare
    `_line_of(` hiding alongside a job-scoped one (e.g.
    `line = _line_of(raw, x) or _line_of_in_job(raw, job, y)`) is still flagged."""
    offenders = []
    for i, ln in enumerate(src.splitlines(), 1):
        stripped = ln.lstrip()
        if stripped.startswith("#"):
            continue                       # a comment / prose mention, not a call
        probe = ln.replace("_line_of_in_job(", "")  # strip the OK helper's calls
        if "_line_of(" not in probe:
            continue                       # only job-scoped calls (or none) on this line
        if stripped.startswith("def _line_of("):
            continue                       # the helper's own definition
        if _WORKFLOW_LEVEL_MARKER in ln:
            continue                       # explicitly allow-listed workflow-level anchor
        offenders.append(f"scan.py:{i}: {stripped}")
    return offenders


def test_no_detector_anchors_via_file_global_line_of():
    """`_line_of(...)` (the file-global first match) may appear in scan.py ONLY as
    its own definition or on a line explicitly marked `# anchor:workflow-level`.
    Every other anchor must be the job-scoped `_line_of_in_job(...)`."""
    src = _SCAN_SCRIPT.read_text(encoding="utf-8")
    offenders = _file_global_anchor_offenders(src)
    # Non-vacuous sentinel: the allow-listed workflow-level anchors must still be
    # present, else a refactor silently emptied the corpus this guard scans.
    assert _WORKFLOW_LEVEL_MARKER in src, (
        "the workflow-level anchor marker vanished from scan.py — refresh this guard")
    assert not offenders, (
        "a detector anchors via the file-global `_line_of` (first match = often the "
        "WRONG job). Use `_line_of_in_job(raw, job_name, needle)`; if the finding is "
        f"genuinely workflow-level, tag the line `# {_WORKFLOW_LEVEL_MARKER}`:\n  "
        + "\n  ".join(offenders))


def test_source_anchor_guard_catches_mixed_and_clears_legit():
    """The guard's scanning logic, pinned on synthetic lines: a bare `_line_of(`
    is flagged even when the SAME line also carries the job-scoped helper; a
    purely job-scoped line and an explicitly-marked workflow-level line are clean."""
    # a mixed line — the bare `_line_of` is the hazard and must still trip
    assert _file_global_anchor_offenders(
        "        line = _line_of(raw, x) or _line_of_in_job(raw, job_name, y)\n")
    # pure job-scoped → clean
    assert not _file_global_anchor_offenders(
        "        line=_line_of_in_job(raw, job_name, y),\n")
    # explicitly marked workflow-level → allowed
    assert not _file_global_anchor_offenders(
        "        line=_line_of(raw, cron),  # anchor:workflow-level\n")
    # a prose comment mentioning the helper → not a call, clean
    assert not _file_global_anchor_offenders(
        "        # file-global `_line_of(raw, job_name)` substring-matches\n")


# --------------------------------------------------------------------------- #
# Invariant 5 — sizing-cap + provenance-stamp WIRING (a fix that's unit-tested
# but un-wired silently vanishes from real reports)
# --------------------------------------------------------------------------- #
# `_cap_opt19_wall_clock` and `_pole_provenance` are thoroughly unit-tested, but the
# helpers are inert unless `collect()` CALLS them. Deleting either call site left the
# whole suite green (the gap audit confirmed it), so a real report would silently lose
# the OPT19 cap / the cross-repo provenance stamp the ci-harness gate halts on. These
# source-scan guards pin the WIRING, not just the helper.
_COLLECT_SRC = (_SCRIPTS / "collect_runs.py").read_text(encoding="utf-8")


def _executable_lines(src: str) -> str:
    """Source with comment-only AND triple-quoted-docstring lines stripped, so a wiring
    guard can't be satisfied by a mention inside a comment or a docstring (PR #93 review:
    a docstring `_cap_opt19_wall_clock(` would otherwise inflate a naive occurrence count)."""
    out: list[str] = []
    in_doc = False
    for ln in src.splitlines():
        triples = ln.count('"""') + ln.count("'''")
        if in_doc:
            if triples % 2 == 1:
                in_doc = False
            continue
        if ln.lstrip().startswith("#"):
            continue
        if triples % 2 == 1:          # opens a docstring on this line — skip the remainder
            in_doc = True
            continue
        out.append(ln)
    return "\n".join(out)


def test_opt19_wall_clock_cap_is_wired_into_collect():
    # The cap must be CALLED (not just defined) in the sizing loop, or OPT19 ships its
    # uncapped static sleep total to real reports + the ci-harness. Assert the EXACT call
    # site (robust against a docstring/comment mention — PR #93 review).
    exe = _executable_lines(_COLLECT_SRC)
    assert "def _cap_opt19_wall_clock(" in _COLLECT_SRC, "the cap helper must exist"
    assert "_cap_opt19_wall_clock(f, global_long_pole)" in exe, (
        "`_cap_opt19_wall_clock(f, global_long_pole)` must be CALLED in collect()'s sizing "
        "loop, else its cap is unit-tested but never reaches a real report")


def test_pole_provenance_stamp_is_wired_into_collect():
    # `cp["provenance"]` must be assigned from `_pole_provenance(...)` — the field the
    # ci-harness ingest HALTs on. Un-wiring it would blind the cross-repo seam.
    exe = _executable_lines(_COLLECT_SRC)
    assert "def _pole_provenance(" in _COLLECT_SRC
    assert 'cp["provenance"] = _pole_provenance(' in exe, (
        "collect() must stamp `cp['provenance'] = _pole_provenance(...)` — the cross-repo "
        "field the ci-harness gate reads; un-wiring it silently breaks the seam")
