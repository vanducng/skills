# Comment pass (`vd:simplify`, every mode; `--comments` runs only this)

The code should speak for itself. An author defends the comments it wrote, so a reviewer that did not write them decides. Every comment and lint suppression in scope is guilty until the keep list clears it.

## Keep list

Only these survive, each cut to one line (license headers excepted):

1. License or legal headers.
2. Behavior forced by something we cannot change: a vendor API, platform, protocol, spec clause or upstream bug. Link it when a link exists.
3. A doc comment on an exported symbol (JSDoc, GoDoc, docstring): it is the contract callers read. Keep it unless it only repeats the name.
4. Formatter or style-only lint suppressions (`prettier-ignore`, line length).
5. Issue or RFC links explaining a constraint the code cannot express.

Everything else goes: narration, restated code, banners, commented-out code, history ("was X", "added for <ticket>"), task or PR references, "fine for now".

## Steps

1. **Review, not as the author.** Hand the scope and [`comment-reviewer.md`](comment-reviewer.md) to a fresh read-only subagent (pi `subagent` reviewer, Claude Code `Task`, Codex spawn). No subagent tool: run the brief yourself as a separate pass before reading your own reasoning, and say so in the report.
2. **Check the verdicts.** Reject verdicts outside the scope, a keep without a clause, or a kill of a true clause-2 constraint. A `do not remove` or `IMPORTANT` claim stays only if tracing proves it true today: search the repo for what it names ("the worker", a caller, a reader). No match, or it guards an empty or unused function, means refuted. Refuted or still unclear, the comment goes, with the dead code it guarded.
3. **Own-code surprise = fix the code.** A comment warning about our own code ("call X after Y", "must be sorted") is `RESHAPE <symbol>`. Make the trap impossible: rename, fold the two calls into one, take the value as a parameter, use the right type. Then delete the comment. Do it even though it changes behavior: the trap the comment warns about is a bug, and removing it is the point (hard rule 1's exception). Keep the comment, cut to one line, and report the flag open only when the fix needs files outside the scope.
4. **Suppressions.** For each `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`, `# type: ignore`, `//nolint`, look up the rule. If it guards correctness or safety, fix the code it hides and delete the suppression. Style-only rules may stay (clause 4).
5. **Encode real constraints.** A true "do not change/reorder/remove" rule becomes the cheapest in-scope check (test, type, lint) that fails on the forbidden change; then the comment goes. No cheap check: keep it as clause 2 and report it unenforced.
6. **Report** one line per comment, `<comment> - killed | kept (clause N, <clause name>) | reshaped | encoded - because <reason>`, then the counts, `RESHAPE` fixes left open, and constraints left unenforced.

## Commits

Comment deletions go in the `refactor:` commit. A `RESHAPE` or suppression fix that changes behavior (a stale-cache trap removed) is its own `fix:` commit.

## Sweeping existing code

`--comments --all <path>` walks one directory per batch: review, apply, test, commit, next. Stop at the first red test.
