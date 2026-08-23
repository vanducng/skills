# Deploy verify - image and rollout checks

Use these when a pipeline's `done_when` is "the new image is live", not as a closed ultracook vocabulary. Confirm the exact flags against current tool docs before running.

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

## CI green

```bash
gh pr checks --watch
# exit 8 from `gh pr checks` is pending, not failure - wait or re-run
gh run list --branch "$BRANCH" --limit 1
```

Keep these as shell `done_when` lines on a ship/verify stage. Do not invent conductor verifier types for them.
