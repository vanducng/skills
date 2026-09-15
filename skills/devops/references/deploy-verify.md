# Deploy verify - image and rollout checks

Use these when a pipeline's `done_when` is "the new image is live", not as a closed ultracook vocabulary. Confirm the exact flags against current tool docs before running.

## Bind evidence to the deployed revision

Record the merged commit, successful deployment run, artifact tag/digest, and live environment identity. Match the CI run's `headSha` to the merge, then the running artifact to that run. A newer local commit or dirty worktree is not deployed because an earlier PR merged. Do not select a deployment by branch name or latest-run position alone.

```bash
gh pr view "$PR" --repo "$REPO" --json state,headRefOid,mergeCommit
gh run view "$RUN_ID" --repo "$REPO" --json headSha,status,conclusion,jobs,url
```

Keep local, staging, and production verification separate. A local container with staging credentials proves neither the deployed artifact nor its runtime permissions. Local tests use isolated databases and test recipients, never staging/production notification targets. For remote smoke tests, verify the live identity first and restore temporary pause/activation changes afterward.

## Image matches

Prove the running workload is the image you just built.

```bash
# Kubernetes: compare the pod image to the expected tag or digest
kubectl -n "$NS" get deploy "$NAME" -o jsonpath='{..image}'
kubectl -n "$NS" get pods -l app="$NAME" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.spec.containers[*].image}{"\n"}{end}'

# Docker Compose
docker compose images
```

`done_when` example: `kubectl get deploy api -o jsonpath='{..image}'` equals `ghcr.io/acme/api@sha256:…`.

## Rollout status

```bash
kubectl -n "$NS" rollout status deploy/"$NAME" --timeout=180s
kubectl -n "$NS" rollout status sts/"$NAME" --timeout=180s
```

Exit 0 means the new replica set is available. Exit non-zero is not a "retry deploy" signal until you have read `kubectl describe` / events.

## Verify the workload and its output

A healthy rollout is not end-to-end success. Verify the exact workload run, terminal task states and complete logs, then the persisted data or user-visible output. A skipped task or replay of an existing checkpoint has not exercised fresh extraction or publication. Report that gap instead of treating exit 0 as fresh evidence; do not delete checkpoints to force it.

For data pipelines, compare at the same grain and reporting cutoff, and prove the test snapshot contains the required source rows before judging output differences. For notifications, inspect the actual channel, mentions, root message, detail replies, and link destinations in the rendered client, not only the API response. Do not enable recurring execution until the previous publisher and upstream-readiness gates are cleared.

## CI green

```bash
gh pr checks --watch
# exit 8 from `gh pr checks` is pending, not failure - wait or re-run
gh run list --branch "$BRANCH" --limit 1
```

Keep these as shell `done_when` lines on a ship/verify stage. Do not invent conductor verifier types for them.
