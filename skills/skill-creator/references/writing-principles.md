# Writing for agents - the principles behind every rule in this catalog

Load when authoring or reviewing skill content, `AGENTS.md`, or `CLAUDE.md`. These are the *whys* behind skill-creator's hard rules; apply them as review lenses on any draft.

## The two loads

Every sentence costs twice: **context load** on the model (tokens occupied whether or not they change behavior) and **cognitive load** on the human maintaining it. A line earns its place only by beating both. The mechanism is the **no-op test**: *does this line change what the agent does versus its default behavior?* "Write clean code" is a no-op - the model already tries. "Never `git add -A` in a fan-out phase" changes behavior. Cut no-ops on sight.

## Length tracks failure risk, not importance

Allocate words where the agent predictably fails, not where the topic feels important. Where default behavior is already right, a skill section can be one sentence. Where agents reliably go wrong (guessing instead of reproducing, testing implementation instead of behavior), be gated, checklisted, prescriptive. A uniformly detailed skill is misallocated: it buries the load-bearing rules in even-toned filler.

## The information hierarchy

Place content by how often it's needed:

1. **In-file step** - always needed → in the workflow itself.
2. **In-file reference** - needed most runs → a table/section in `SKILL.md`.
3. **Disclosed reference** - needed some runs → `references/<topic>.md`, linked with a load condition ("load when the work is a migration").

**Progressive disclosure** keeps SKILL.md under ~200 lines without losing depth. **Co-location** keeps each reference next to the skill that owns it - a rule that lives far from where it's applied gets skipped.

## Leading words

Pretrained concepts compress instructions into single tokens: *tracer bullets*, *seams*, *steel-man*, *frontier*, *red before green*, *blast radius*, *Chesterton's fence*. One leading word anchors a whole behavior pattern the model already knows. Use them deliberately and consistently - and define the catalog's own terms once (see `vd:apidesign` `references/deep-modules.md`), then reuse them verbatim. Synonym drift ("component" here, "module" there) makes every rule fuzzier.

## The negation trap

"Don't think of an elephant." Negative instructions plant the pattern they forbid. Prefer prompting the positive: instead of "don't write vague commit messages," write "commit messages name the behavior change." Keep hard prohibitions for genuinely dangerous acts (never force-push, never commit secrets) - and pair each with the safe alternative.

## Completion criteria over adverbs

"Carefully", "thoroughly", "properly" are unfalsifiable. Replace them with checkable done-when conditions: "Done when every referenced file resolves", "No red-capable command, no hypothesizing." The two failure modes are **premature completion** (stopping because it feels done) and **unbounded work** (no stop condition at all); an explicit criterion kills both.

## Environment as truth (anti-staleness)

A document that restates what the environment already declares is a cache that will go stale: dependency versions, CLI flags, file listings, directory trees. Point at the source instead ("versions per `package.json`", "flags per `--help`"). In long-lived artifacts (specs, ADRs, skills), avoid embedding file paths and code snippets that churn; reference sibling artifacts by path/link rather than duplicating their content - single source of truth applies to prose too.

## Pruning is maintenance

Skills accrete sediment: rules for problems that no longer exist, sections duplicated from another skill, examples for a tool version long gone. On every substantive edit, re-run the no-op test over the whole file and delete what fails it. A skill that only ever grows is decaying.
