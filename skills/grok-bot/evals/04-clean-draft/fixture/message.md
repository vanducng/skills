**Status:** the export slice is merged and live ([PR 481](https://github.com/example/shop/pull/481)). Price rounding is in build, 41 of 60 tests green, no blocker.

**Decision 1: Should the CSV import wait for staging data?**
A. Wait for staging data (about two days)
B. Build on synthetic data now and re-test on staging
Recommendation: B, because the format is fixed and only the volume is unknown.

Reply with a letter, or in your own words.
