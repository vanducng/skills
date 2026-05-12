# Playbook — Infra (CI/CD + Terraform + K8s)

Load this when the failure is in a CI pipeline, Terraform plan/apply, K8s deployment, or related infra surface (secrets, networking, image build).

## First-look checklist

- **Read the actual log, not the status badge.** GH Actions: `gh run view <id> --log-failed`. K8s: `kubectl logs --previous`. Terraform: full `apply` output, not just the summary.
- **Which env?** Lower env first; reproduce there before touching prod.
- **What changed?** Git diff on the workflow / `.tf` / Helm values / kustomize overlays; also check provider/action version bumps.
- **Drift?** `terraform plan -refresh-only`; `kubectl diff -f manifest.yaml`; compare deployed image SHA against the latest build.

## CI/CD (GitHub Actions) — fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| Workflow fails on dependency install | Lockfile drift / cache poisoning / registry outage | Reproduce locally with the same lockfile; bust the action cache; pin or unpin deliberately. |
| Tests pass locally, fail in CI | Env var missing / different OS / time zone / DB version | Add the missing env, or match versions in CI to local. Don't `continue-on-error` to dodge. |
| Flaky test in CI | Real race / shared fixture / network flake | Reproduce with `--repeat-each` or stress runner. If genuinely flake, fix root cause; quarantining is temporary, not a fix. |
| Deploy job fails after build | Missing secret / wrong env / permission boundary | Confirm secret exists in the env's scope; confirm OIDC/IAM trust matches. Don't broaden IAM as the first move. |
| `gh-action@vX` regression | Upstream action bumped a transitive dep | Pin to the prior SHA (not just tag) while you fix forward. |
| Matrix has a hole | Newly added arch/OS without setup | Add setup steps OR remove the matrix entry; don't ship a workflow that silently skips a leg. |

**CI verification:**
```
gh run rerun --failed <run-id>           # rerun only failed jobs
gh run watch <run-id>
gh run view <run-id> --log-failed | less
```
Verify in a separate "test" branch before merging the workflow change.

## Terraform / IaC — fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| `plan` shows unexpected drift | Console change / out-of-band script / provider upgrade | Decide: reconcile to code (`apply`) vs reconcile code to reality (`import` or update HCL). Document choice in commit. |
| `apply` errors mid-resource | Dependency cycle / partial create / quota | Targeted apply (`-target`) to break the cycle, then untargeted apply. Use sparingly — leaves state messy. |
| Provider auth fails | Expired creds / role assumption failed / region mismatch | Verify creds locally before changing IAM. Check assumed-role chain. |
| `for_each` collection changed | Underlying map changed shape, plan wants destroy+create | Add a `moved {}` block to migrate state without destroy. |
| State lock stuck | Crashed apply / lost lease | Verify nobody is mid-apply; `force-unlock` only with the exact lock ID, never blindly. |
| Workspace mismatch | Wrong workspace selected | Confirm `terraform workspace show` matches intent BEFORE plan/apply. |
| SOPS-decrypted value drifts | Secret rotated outside infra repo | Re-encrypt with the current age key (`SOPS_AGE_KEY_FILE=.secrets/age-key.txt sops -e -i ...`). |

**Hard rules:**
- Never run `terraform destroy` or `state rm` under `--auto`. Require explicit user confirmation, always.
- Always preview with `plan` before `apply`. Save the plan (`-out tfplan`) and apply *that exact plan* to avoid race-condition surprises.
- Production after staging — never the other way around.

**Terraform verification:**
```
terraform validate
terraform plan -refresh-only            # expect: clean
terraform plan -out tfplan && terraform show tfplan
# apply in lower env first, watch outputs
```

## K8s — fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| `CrashLoopBackOff` | App panics on startup / missing config / bad probe | `kubectl logs --previous`; fix the app or the config map / env. Don't disable the probe. |
| `ImagePullBackOff` | Wrong tag / registry auth / image deleted | Verify image exists; check imagePullSecret in correct namespace. |
| `OOMKilled` | Real memory leak OR limit too tight | Profile app first; raising limits without understanding is masking. |
| Pod stuck `Pending` | No node satisfies requests / PVC unbound / taint | `kubectl describe pod` → scheduler events tell you which constraint failed. |
| `NetworkPolicy` denies traffic | Policy too tight or selector mismatch | Confirm with `kubectl exec` from source pod; fix policy at the source, not by punching a wildcard hole. |
| Secret rotation didn't take effect | Pod cached old secret at boot | Restart the deployment (`kubectl rollout restart deploy/<name>`). For mounted secrets, the kubelet refreshes async; restart is the simple verifier. |
| Service routes to wrong pods | Selector mismatch after label change | `kubectl get endpoints <svc>` — empty endpoints = selector wrong. |
| `kubectl apply` works, app misbehaves | Hot-reload didn't trigger / config map change but no rollout | Annotate deployment to force rollout (`kubectl rollout restart`). Add a checksum annotation in Helm chart to fix forever. |

**K8s verification:**
```
kubectl get pods -w                           # stable across new pod lifecycle?
kubectl logs deploy/<name> --tail=200
kubectl logs deploy/<name> --previous          # confirm no crash loop
kubectl get events --sort-by=.lastTimestamp | tail -30
kubectl describe deploy/<name> | grep -A 5 Conditions
```
Then exercise the workload (request, job, consumer) — running ≠ working.

## Cross-cutting

- **Lower env first.** Even for "obvious" fixes. Especially when the fix touches IAM, network policy, or storage.
- **Blast radius:** for any infra fix, state explicitly what's being changed (env, account, namespace, region) in the commit message.
- **Secrets:** never paste decrypted SOPS contents into reports, commits, or PR descriptions. Reference the file path only.
- **Reversibility:** before `terraform apply` or `kubectl apply`, know the rollback. For Helm, `helm rollback`. For raw kubectl, the previous manifest.

## Done criteria (infra-specific)

- [ ] Reproduced fix in lower env first; output captured.
- [ ] Plan / diff reviewed; nothing unexpected.
- [ ] Rolled out to prod with explicit confirmation; verification commands rerun against prod.
- [ ] Drift check clean (`terraform plan -refresh-only` or `kubectl diff`).
- [ ] CI guardrail added if config drift was the cause (lint, policy check, schema validate).
- [ ] No `--force-unlock`, `state rm`, `destroy`, or `kubectl edit` left undocumented.
- [ ] Secrets unchanged in plaintext anywhere outside SOPS / Secret Manager.
