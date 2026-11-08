# Blast radius beyond the diff

Taken from `vd:scenario --diff`; this becomes its home when scenario drops that mode. Use it on a Standard or Deep review when the change touches a shared contract: the question is what breaks *outside* the diff, and the one fact the change is safe because of, proven by running code.


Default mode enumerates what *could* break in a design. `--diff` answers a sharper question about a concrete change: what does this break somewhere else, and what is the one fact it is safe because of. Listing callers is not the job - grep finds those in a second. The job is the breakage grep does not show.

1. **Read the change** - the diff, the symbols it adds/changes/deletes, and what it now does differently, including the part the diff does not spell out.
2. **Find the one safety fact.** Most scary-looking changes are safe because of a single fact ("this call only drops already-dead cache entries"). Find it; if it holds, most risks die at once. Spend time here, not on a long list of maybes.
3. **Look where grep stops** - the pinned library's own source, execution timing (teardown, microtasks, retries), and what symbol search misses: API response shapes, DB columns, wire formats, feature flags, consumers three hops downstream, other languages reading the same bytes.
4. **Rate each risk honestly** - real likelihood, real cost. Keep confirmed risks; list checked-and-cleared separately. Cite real `file:line`; a search that finds nothing is still an answer; never invent a caller.
5. **Prove the one fact by running code** - a small script or test that calls the real code and fails loud if the fact is false. Paste the output. A writeup that merely sounds right is the trap.

**Certainty ladder** - get every safety fact as far down as is cheap, and say where it stopped:

| Level | Evidence |
|---|---|
| 1 | You said so - worthless alone |
| 2 | You pointed at a real `file:line` (or the library's own source) |
| 3 | You walked the failure path and it cannot reach |
| 4 | You ran a script/test against the real code |
| 5 | You reproduced it in the running app |

A fact stuck below 4 is reported as **unproven**, never rounded up to settled.

**Output shape (`--diff`):** What it does (incl. the non-obvious part) · The one safety fact + its ladder level + proof output · Risks (each: how it breaks, `file:line`, likelihood, cost, how to check) · Cleared · Before you merge (the cheapest test that catches the real bug).

**Save it like the default mode:** write the report to the injected `Reports:` path as `scenario-diff-{date}-{slug}.md` and hand back an openable location (`file:///absolute/path`), not just the basename.

**Boundaries:** landing verdicts stay with `vd:code-review`; codebase-fit stays with `vd:code-review --refactor`; this mode owns beyond-the-diff breakage with runnable proof.

