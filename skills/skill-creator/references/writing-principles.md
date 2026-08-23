# Writing principles for agent skills

A skill is a conditional prompt fragment. It costs context every time it loads. Every line must change what the agent does.

## Two loads

1. **SKILL.md** - routing, hard rules, the happy path, completion criteria. Keep it short enough to follow under pressure.
2. **references/** - playbooks, checklists, stack notes. Load only when the case matches.

If a section is unused on the common path, it does not belong in SKILL.md.

## Leading words

Put the action first. "Run X, then verify Y" beats "This skill is about X." Descriptions must include trigger phrases the user actually types.

## No-op test

For each paragraph: if the agent already does this correctly without the skill, delete it. Restating `git commit -m` teaches nothing and dilutes the rules that matter.

## Positive phrasing

Write the behavior you want. "Update plan status after each phase" beats a long list of "don't forget"s. Use a short anti-pattern table only for failures the model repeats.

## Completion criteria

Prefer "Done when…" that a later session can check (file exists, command exits 0, user said yes) over step ceremony. Ultracook stages are this idea as data: `skill` + `done_when`.

## Anti-staleness

Do not snapshot inventories that will rot (file lists, version tables copied from today's tree). Point at the live environment or the command that discovers it. Long-lived plans use `vd:plan`'s anti-staleness rule; skills should too.

## Length tracks failure risk

Near-empty where the base model already behaves. Heavily gated only where agents predictably fail (debug without a repro, review without evidence, plan without seams). Past ~200 lines, rule-following degrades - split or move depth to references.
