# Merge/rebase conflict resolution - resolve by intent

For an in-progress `git merge`, `git rebase`, or `git cherry-pick` that stopped on conflicts.

## The rule

**Resolve by intent, never by text.** A conflict is two intentions colliding; the resolution must honor both, and the marker text alone rarely tells you what those intentions are. And **always resolve; never `--abort`** - aborting throws away the user's operation and solves nothing.

## Steps

1. **Understand the state.** `git status` - which operation is in progress, which files conflict, which side is "ours"/"theirs" (they swap meaning between merge and rebase - check, don't assume).
2. **Trace each side to primary sources.** For every conflicted hunk, find what each side was *trying to do*: `git log --oneline <ours>..<theirs> -- <file>`, the commit messages, the PR descriptions, linked issues. `git show <sha>` for the full change, not just this hunk.
3. **Resolve by combining intents.** Usually both changes belong in the result. When they genuinely contradict, the newer intent wins only if it knowingly supersedes the older one - if it's unaware of the older change, stop and ask the user. **Never invent behavior** that neither side wrote.
4. **Verify.** Run the repo's checks (build, tests touching the conflicted areas). A conflict resolution that doesn't compile is not resolved.
5. **Finish the operation.** `git add <files>` then `git merge --continue` / `git rebase --continue` / `git cherry-pick --continue`. Don't create a separate "fix conflicts" commit during a merge - the merge commit is the resolution.

## Tells that a resolution is wrong

- One side's change silently vanished (check `git diff <side> -- <file>` after resolving).
- The resolved hunk contains code neither parent had.
- Tests that passed on both parents fail on the result.
