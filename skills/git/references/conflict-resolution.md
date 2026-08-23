# Conflict resolution

Use when a rebase or merge stops on conflicts. The `vd:git` workflows call this; do not invent a side protocol.

## Rules

1. **Read both sides before editing.** `git log` / `git blame` on each hunk. The conflict markers are not a coin flip.
2. **Prefer the intent, not the latest timestamp.** A newer hunk can still be the wrong product decision.
3. **Do not resolve generated files by hand.** Re-run the generator (`prisma generate`, `buf generate`, `go generate`) and take that output.
4. **Keep commits bisectable.** Do not squash a conflict resolution into an unrelated feature hunk if the merge is the story.
5. **Stop on semantic collisions.** Two sides that both compile but disagree on behavior are a product question - ask, do not silently pick.

## Mechanical loop

```bash
git status
# for each unmerged path:
#   read the file, keep the combined intent, drop conflict markers
git add <path>
git rebase --continue   # or git merge --continue
```

After the last conflict: run the relevant tests before pushing. A green compile is not a resolved merge.

## When to abort

- The other side deleted a file you heavily edited and you cannot see why
- Conflict spans a migration and a rewrite of the same table
- You cannot explain the resolution in one sentence

Abort (`git rebase --abort` / `git merge --abort`), then ask. A bad resolution is worse than a late one.
