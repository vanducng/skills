# Idempotent operations

Design every mutating step so it converges to the same end state no matter how many times it runs or where the last run died. Controllers, CI jobs, and GitOps reconcilers all run at-least-once. If leftover state changes the next outcome, every retry is an incident.

Ask of each step: what happens if this runs twice? What if the previous run crashed halfway? If the answer is "it depends on leftovers," add a reconcile path.

## Converge to state, do not replay steps

Declare the desired object. Let the tool create, update, or no-op. Do not script a create-only path and hope the object is missing.

```bash
# Kubernetes: apply is reconcile; create fails on the second run
kubectl apply -f manifests/deploy.yaml
# not: kubectl create -f manifests/deploy.yaml

# Helm: install-or-upgrade, one chart, one release name
helm upgrade --install myapp ./chart -n prod --create-namespace

# Terraform: plan is the diff against state; apply is the converge
terraform plan -out=tfplan && terraform apply tfplan

# GitOps: git is desired state; Argo CD / Flux keep looping until match
# Prefer Application / Kustomization CRs in git over one-shot CLI creates
```

Ansible-style desired state is the same idea: `state: present`, not "run these shell lines in order." Docker Compose `up` converges services to the compose file; it is not a transcript of first-boot commands.

Server-side apply (`kubectl apply --server-side`) and Terraform state both treat identity as stable. Name the object once. Do not generate a new name per run.

## The retry reality

GitHub Actions reruns the job. A runner dies mid-step. A K8s controller requeues. Flux reapplies every interval. Design each step so the second execution lands on the same bytes and the same cluster/API objects.

```yaml
# Bad: create-only; second run fails or forks a second release
- run: helm install myapp ./chart -n prod

# Good: same release name, same values, second run is a no-op or in-place upgrade
- run: helm upgrade --install myapp ./chart -n prod -f values/prod.yaml
```

Treat "already exists" as success when the existing object matches the desired spec. Treat mismatch as update, not as skip.

## Patterns

| Pattern | When | Sketch |
| --- | --- | --- |
| Create-or-get | Named cluster objects, cloud resources with a stable ID | `kubectl apply`; `gcloud ... --quiet` with a fixed name; Terraform resource address |
| Upsert | ConfigMaps, secrets, Helm values, HTTP PUT of a known key | Replace the whole document; do not append |
| Idempotency key | Payments, webhooks, vendor APIs, deploy notifications | Send `Idempotency-Key: <deploy-sha>`; store the response; replay the stored result |
| Guarded migration | Schema and data backfills | `CREATE ... IF NOT EXISTS`; ledger table `schema_migrations` (version applied once) |
| Tag-once image build | CI image publish | Tag `:gitsha` and `:1.2.3`; skip push if the digest already exists for that tag |
| Queue consumer + dedupe | Webhooks, deploy events, job queues | Persist `event_id`; ack only after the side effect is recorded |

```sql
-- Guarded DDL: second run is a no-op
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO schema_migrations (version) VALUES ('20260408_add_orders_idx')
ON CONFLICT (version) DO NOTHING;
```

```bash
# Tag-once: content-addressed tag, refuse to overwrite a different digest
digest=$(docker buildx build --push -q -t ghcr.io/org/app:${GIT_SHA} .)
# If the tag already points at this digest, the registry push is a no-op.
```

```bash
# Webhook / notify: key is the deploy identity, not "now"
curl -sS -X POST "$HOOK_URL" \
  -H "Idempotency-Key: deploy-${GIT_SHA}" \
  -d "{\"sha\":\"${GIT_SHA}\",\"env\":\"prod\"}"
```

## Partial-failure recovery

A step that wrote half its work must be safe to start over. The second run inspects what exists and finishes the remainder.

Compounding steps are the failure mode: append a line, increment a counter, send mail, `helm install` a new release name, `docker tag` with `date +%s`. Put those behind a ledger check or an idempotency key.

```bash
# Bad: second run sends a second page
curl -X POST "$PAGER" -d "deployed $GIT_SHA"

# Good: record first, notify only if the insert is new
if register_deploy "$GIT_SHA"; then
  curl -X POST "$PAGER" -d "deployed $GIT_SHA"
fi
```

Terraform lock files and Helm release secrets are the ledger for those tools. Do not delete them to "unstick" a run unless you understand the leftover resources.

## The test

1. Run the job or apply twice. Cluster objects, image tags, and migration ledger must be byte/state identical.
2. Kill the job after each mutating substep (image push, apply, migrate, notify). Re-run. End state must match a clean full run.
3. If any answer is "it depends on leftovers," add create-or-get, a key, or a ledger before merging.

```bash
# Cheap local check: apply, apply again, empty diff
kubectl apply -f manifests/ && kubectl apply -f manifests/ --dry-run=server
terraform plan -detailed-exitcode   # exit 0 = no drift after apply
```

## Anti-patterns

| Anti-pattern | Why it breaks | Do this instead |
| --- | --- | --- |
| `cmd \|\| true` | Hides non-convergence; green CI, wrong cluster | Handle "already exists" explicitly; fail on real errors |
| Delete-then-create | Window with no object; name reuse races; lost identity | Update in place (`apply`, `helm upgrade`, Terraform update) |
| Non-deterministic names | `myapp-$RANDOM`, timestamps in metadata | Stable names; version in labels/annotations, not in the object name |
| Timestamps baked into spec | Every apply is a diff; GitOps never syncs clean | Omit `creationTimestamp` from checked-in YAML; no `date` in ConfigMaps |
| `kubectl create` / `helm install` in CI | Second run fails or forks | `kubectl apply` / `helm upgrade --install` |
| Unpinned `:latest` | Same command, different image | Digest or immutable git-sha tag |

`|| true` is not idempotency. It is swallowing the signal that the step did not converge.

Adapted from cursor/plugins pstack principle-make-operations-idempotent (MIT).
