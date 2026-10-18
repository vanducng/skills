# Live verification

Read when a diff changes a query, a selection or ranking rule, a data contract, or what a downstream
consumer (model prompt, report, alert, card) receives. Goal: replace "may cause issues" with a number
from the real system.

## Ground rules

- Read-only during a review: SELECTs, API GETs, dry runs. No DDL, writes or posts against shared or
  production targets. The only exception is step 3 of the end-to-end run, with the user's go-ahead.
- Use the project's own query tool and saved connections (discover them from the repo or the user's
  config). Never paste credentials into commands, comments or output.
- Bound every probe: a date window, one tenant or client, a LIMIT.
- Cite results as counts and dates. Never quote personal data from samples (names, phones, emails);
  describe the shape instead.

## Probes

| Question | Probe |
|---|---|
| Grain: does the new join fan out? | `count(*)` vs `count(distinct key)` over a recent window |
| Coverage: does every row find its match? | share of rows with a null joined key, per day; today vs yesterday shows refresh lag |
| Contract: do hardcoded values exist upstream? | distinct values of every column the code compares against, vs the producer's accepted values or schema |
| Rule output: what does the new rule select? | replicate the rule in SQL (a `CASE` in the code's order), count per bucket per day, compare with numbers the PR states |
| Cap and priority: who wins under the limit? | rank by the code's sort key and count what fits the cap on the busiest day |
| Access: will the runtime identity still read it after the next rebuild? | grants on the source; declared in the producer's config (survives rebuilds) or hand-applied (lost) |
| Freshness: is the data there when the job runs? | producer refresh cadence vs the consumer's schedule |
| Evidence reachability: does the consumer see what the label is based on? | sample 3-5 selected records and read exactly what the consumer receives |

The last probe catches what diffs hide best: a selection that ranks records by signals the downstream
reader never gets, so it can only echo the label or ignore it.

## End-to-end run

For a re-review, or when the user asks to confirm the change works:

1. Isolated checkout (`vd:worktree`), install, run the unit tests.
2. Dry run first, pointed at the non-prod target the project already uses for local runs.
3. Writes need the user's go-ahead, never happen under `--auto`, and stay as small as possible. Local
   and dev targets are often shared: if the run needs a changed view or migration, apply only that
   file, only to that target, and restore the previous version afterwards. Post only to a dev or test
   destination the user names.
4. Log each record's ID, selection reason and outcome (labels, categories) to a session temp dir, so
   the result is judged on content, not on the exit code. Not raw field values: they carry personal
   data. Delete the log when the review is done.
5. Reconcile the output against the source of truth with read-only queries: totals, per-bucket counts,
   what the cap kept.
6. Report what passed, what the run found, and anything still wrong, then give the verdict.
