"""Typed claims layer — increment 1 (headline family).

`verify_report.py` (the gate) has historically verified the rendered report by
PARSING the markdown prose back into facts and comparing them to `findings.json`.
That couples every guard to renderer WORDING: a wording change can blind or break
a guard with no test failure until a dogfood run catches it. This module gives the
renderer (`blocking_path.py`) a typed, self-declared alternative for its
judgment-bearing sentences: build a `Claim` object (kind + subject + load-bearing
fields + the exact rendered sentence) instead of an f-string alone, collect them in
a `ClaimSet`, and serialize that set to a `claims.json` manifest next to the
report. The gate can then compare MANIFEST FIELDS to `findings.json` directly —
no prose parsing.

Increment 1 (plan 002a) migrated the headline family and shipped the
manifest-first headline<->stamp comparator in `verify_report.py`. Plan 007 then
migrated the rest of the "slowest check ... waits on" framing family (the
agent-prompt gate line, the pole role labels, the minority-slow notes) and turned
on the two guards that make an unregistered framing sentence unshippable: a
report-level coverage check (every family phrase in the report must be backed by a
registered `Claim`, `verify_report.check_claims_cover_framing_vocabulary`) and a
source-level lint (a `FRAMING_VOCABULARY` phrase in `blocking_path.py` outside a
`Claim(...)` construction fails CI, in `test_verify_report_self.py`). See
`FRAMING_VOCABULARY` below.

This module relocates NO fact computation — `blocking_path.py` still computes
every value; a `Claim` just captures the sentence built from those values, and
`ClaimSet.add()` returns exactly the `rendered` string so a call site can inline
it (`lines.append(claims.add(Claim(...)))`) without changing what gets printed.

Stdlib only (repo convention for `skills/ci-speedup/scripts/`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The closed vocabulary of claim kinds the renderer emits. A kind not in this
# tuple is a programming error in the renderer (not a claim in this family yet) —
# callers should never construct a `Claim` with a kind outside it without also
# updating this tuple and `families_migrated` below.
#   headline_slowest  — the headline "slowest check ... waits on" lead (gate/stamp
#                       comparator applies: subject==stamp, rendered exactly once).
#   pole_role_line    — a per-pole role label ("The slowest check a typical PR
#                       waits on.", the concurrent-behind line, the rare/minority
#                       role). No comparator; the coverage check is its bind.
#   pole_gate_prompt  — the agent-prompt gate line ("Slowest check a typical PR
#                       waits on: ..."). May legitimately render in more than one
#                       prompt block, so its manifest<->prose bind is "appears >=1
#                       time", never exactly-once.
#   minority_slow_note — the minority-slow prose fragment ("... rarely the actual
#                       slowest check a PR waits on ...") and its plural twin.
#   tier2_headline     — the Bottom-line subordinate Tier-2 sentence, or its
#                       modeled-but-unpromoted fallback.
#   tier2_section_lead — the Tier-2 section lead with total credited runner-minutes.
#   tier2_neutrality_line — one R-row's rendered neutrality certificate.
#   headline_chain     — the chain-form headline lead (ENG-1 PR-N2): the gate is
#                       a `needs:` chain; subject = the joined modal-chain member
#                       names; `check_headline_chain_matches_stamp` re-derives
#                       the tuple and p50 from `pr_critical_path.chain_facts`.
KNOWN_KINDS: tuple[str, ...] = (
    "headline_slowest", "pole_role_line", "pole_gate_prompt", "minority_slow_note",
    "tier2_headline", "tier2_section_lead", "tier2_neutrality_line",
    "headline_chain")

# The load-bearing framing phrases of the "slowest check ... waits on" family —
# the single source of truth both guards key on (plan 007):
#   - `verify_report.check_claims_cover_framing_vocabulary` scans the rendered
#     report for every occurrence of each phrase and fails if one isn't backed by
#     a registered `Claim` whose `rendered` contains it.
#   - the source lint in `test_verify_report_self.py` fails if a phrase appears in
#     `blocking_path.py` outside a `Claim(...)` construction.
# Both consumers embed their own copy of these phrases and match CASE-INSENSITIVELY
# (the agent-prompt gate line capitalizes "Slowest ..."); coupling tests pin the
# embedded copies to this tuple so the copies can't drift. The three phrases are
# mutually non-substring (none contains another), so a report occurrence is counted
# under exactly one phrase — "... a typical PR waits on" (the typical-gate lead,
# role label, and prompt line), "... a PR waits on" (the npop=0 role and the
# minority-slow fragment), and "slowest a PR waits on" (the pluralized minority
# note, which omits "check"). `verify_report.py` embeds its own copy as
# `_FRAMING_VOCABULARY` (it imports no engine module); the coupling test
# `test_framing_vocabulary_stays_coupled_to_claims` pins the two tuples equal so
# they can't drift.
FRAMING_VOCABULARY: tuple[str, ...] = (
    "slowest check a typical PR waits on",
    "slowest check a PR waits on",
    "slowest a PR waits on",
    "wall-clock-neutral runner spend",
    "machine-derived proof",
    "modeled bill opportunities remain",
)


@dataclass(frozen=True)
class Claim:
    """One judgment-bearing sentence the renderer asserts about the report.

    `kind` is the closed-vocabulary claim family (`KNOWN_KINDS`). `subject` is
    the check/job name the claim is ABOUT (what the gate compares against a
    stamped field in findings.json — e.g. `critical_path_check`). `fields` holds
    any other load-bearing values the claim carries (durations, counts, ...) for
    future gate comparisons; increment 1's gate doesn't read every field yet.
    `rendered` is the EXACT sentence as it appears in the report — the gate
    asserts this string appears verbatim (once) in the report text, binding the
    manifest to the prose it was minted from."""
    kind: str
    subject: str
    fields: dict[str, Any]
    rendered: str


@dataclass
class ClaimSet:
    """Collects `Claim`s during one `render()` call. `add()` returns
    `claim.rendered` so a call site can do `lines.append(claims.add(Claim(...)))`
    — the manifest and the prose are built from the SAME object, so they agree by
    construction; there is no separate "describe what I just rendered" step that
    could drift from the actual sentence."""
    claims: list[Claim] = field(default_factory=list)
    # The families whose claims a fresh render declares complete. `"headline"` keys
    # the headline<->stamp comparator (002a); `"slowest_gate_framing"` (plan 007)
    # keys the report-level coverage check. Keeping them as SEPARATE tokens is what
    # keeps a 002a-era manifest (declaring only `["headline"]`) from false-failing
    # the coverage check — it activates ONLY when `"slowest_gate_framing"` is present.
    families_migrated: list[str] = field(
        default_factory=lambda: ["headline", "slowest_gate_framing", "runner_minutes"])

    def add(self, claim: Claim) -> str:
        if claim.kind not in KNOWN_KINDS:
            # KNOWN_KINDS is a closed vocabulary (see its docstring): an unknown
            # kind is a renderer bug — a typo, or a new kind wired into the
            # renderer but not registered here (and, if gated, not added to
            # `families_migrated`). Fail loudly at construction rather than
            # silently emit a manifest with an unrecognized kind that nothing
            # catches until plan 007's coverage lint lands.
            raise ValueError(
                f"unknown claim kind {claim.kind!r}; add it to KNOWN_KINDS "
                "(and to families_migrated if the family is gated)")
        self.claims.append(claim)
        return claim.rendered

    def to_json(self) -> dict[str, Any]:
        """Shape written to `<report>.claims.json`. `families_migrated` is the
        forward-compat key: the gate uses it to know which claim KINDS must
        appear, so a manifest from a partially-migrated renderer never causes a
        false failure on a family that hasn't been ported yet."""
        return {
            "claims": [
                {
                    "kind": c.kind,
                    "subject": c.subject,
                    "fields": c.fields,
                    "rendered": c.rendered,
                }
                for c in self.claims
            ],
            "families_migrated": list(self.families_migrated),
        }
