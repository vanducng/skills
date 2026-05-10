# Infrastructure Debugging

Containers, Kubernetes, IaC, secrets, multi-environment configuration, networking, image / build issues.

## When to use

- Pod / container won't start, restarts, or runs but app is unreachable
- Deploy succeeded but app behaves wrong in one environment (works in dev, broken in staging)
- IaC drift — `terraform plan` shows changes nobody made
- Secret rotation broke something
- Env var present locally, missing in container
- Image pulls fail; build is "slow" or non-reproducible
- Network-policy / service-mesh denial (intermittent or total)
- TLS / cert issues post-renewal

## First triage — answer these before fixing

1. **Which environment** is broken? (dev / staging / prod / a specific overlay)
2. **What's the diff** between the broken env and a working one? Image tag, env vars, ConfigMap, Secret, IAM, replica count, version pin, infra changes
3. **When did it start?** Correlate with a deploy, IaC apply, secret rotation, image build, dependency bump, or cert renewal
4. **Is it the workload, the platform, or the network?** Determines which logs to pull first

## Kubernetes

### Pod won't start

```bash
kubectl describe pod <pod> -n <ns>
kubectl get events -n <ns> --sort-by=.lastTimestamp | tail -50
```

| Status | Common causes |
|---|---|
| `Pending` | Insufficient CPU/mem on nodes; node taints don't match tolerations; `nodeSelector`/`affinity` impossible to satisfy; unbound PVC |
| `ImagePullBackOff` / `ErrImagePull` | Wrong tag; registry creds (`imagePullSecrets`); network/firewall to registry; rate limit |
| `CrashLoopBackOff` | App crashes on start; `kubectl logs --previous`; check entrypoint, env, secret refs |
| `CreateContainerConfigError` | Referenced ConfigMap/Secret/key missing |
| `OOMKilled` | Memory limit too low; leak; wrong limit unit |
| `Init container failure` | Init container fails before main starts |

### Pod running but app not working

```bash
kubectl logs <pod> -n <ns>
kubectl logs <pod> -n <ns> --previous           # if it just crashed
kubectl exec -it <pod> -n <ns> -- sh             # shell in
kubectl port-forward <pod> -n <ns> 8080:8080     # bypass Service to test app directly
```

If `kubectl exec` works but external access doesn't → it's the **network** layer:

| Layer | Check |
|---|---|
| Service | `kubectl get svc <name> -n <ns> -o yaml` — selectors match pod labels? port mapping right? |
| Endpoints | `kubectl get endpoints <name> -n <ns>` — empty means selector miss |
| Ingress / Gateway / HTTPRoute | rules match host/path? backend service correct? |
| NetworkPolicy | does any policy block ingress to this pod? |
| DNS | `kubectl exec <pod> -- nslookup <svc>.<ns>.svc.cluster.local` |

### Probes

Liveness / readiness probes are a frequent false-positive cause of "app keeps restarting":

| Issue | Symptom | Fix |
|---|---|---|
| Liveness too aggressive | Pod restarts mid-startup | Bump `initialDelaySeconds`, use startup probe |
| Readiness wrong endpoint | Service has no endpoints, traffic rejected | Point readiness at an endpoint that returns 200 only when warm |
| Probe timeout < SLA | Pod marked unready under load | `timeoutSeconds`, scaling, app-side concurrency |

## Docker / images

```bash
# Inspect what's actually in the image
docker run --rm --entrypoint sh <image> -c "env; ls -la /app; cat /app/<file>"

# Build from scratch with no cache
docker build --no-cache -t <tag> .

# Layer history (image bloat)
docker history <image>

# What does the image say about user, workdir, entrypoint?
docker inspect <image> | jq '.[0].Config | {User, WorkingDir, Entrypoint, Cmd, Env}'
```

Reproducible-build questions:

- Pinned base tag (not `:latest`)?
- Lockfiles committed (`package-lock`, `pnpm-lock`, `poetry.lock`, `go.sum`, `uv.lock`)?
- Build args / `ARG`s match across environments?
- Multi-stage final stage doesn't accidentally re-resolve deps?

## Multi-environment configuration

The most common silent bug: **env var set in dev, missing or different in staging/prod**.

### Map a variable across environments

Use `vd:scout` for the surface map (see `scout/references/domain-scouting.md` § DevOps). Then trace the precedence — runtime wins:

```
.env file  →  Dockerfile ENV  →  ConfigMap  →  Helm values  →  Deployment env  →  Secret (env or volume)
       (only one of these is what the running container sees)
```

### Helm

```bash
# What did Helm actually render?
helm template <release> <chart> -f values.yaml -f values-<env>.yaml > /tmp/rendered.yaml

# Diff between two environments
helm template r ./chart -f values-staging.yaml > /tmp/s.yaml
helm template r ./chart -f values-prod.yaml > /tmp/p.yaml
diff /tmp/s.yaml /tmp/p.yaml
```

### Kustomize

```bash
kustomize build overlays/staging > /tmp/s.yaml
kustomize build overlays/prod    > /tmp/p.yaml
diff /tmp/s.yaml /tmp/p.yaml
```

### Verify what the container actually sees

```bash
kubectl exec <pod> -n <ns> -- env | sort
kubectl exec <pod> -n <ns> -- cat /etc/<configmap-mount>/<file>
```

If the deployed manifest says `FOO=bar` but `env` inside the container shows `FOO=baz` → something at runtime is overriding (an init container, an entrypoint script, an admission webhook).

## Secrets

| Concern | Practice |
|---|---|
| Decryption | `sops -d` (age key path per repo's `.mise.toml`); never paste decrypted contents into reports / logs / commits |
| Rotation broke things | Compare consumers — every workload referencing the old secret must be restarted to pick up the new value (most don't auto-reload) |
| Missing secret in env | `kubectl describe pod` shows `CreateContainerConfigError`; check `valueFrom: secretKeyRef.name` and `key` |
| Secret in image | Forbidden — rebuild without it, rotate the credential, audit history |
| OIDC / IRSA / Workload Identity | Service account → IAM binding → token issuer; `kubectl describe sa <name>` |

## IaC — Terraform / Pulumi / Helm

### Drift

```bash
terraform plan                         # what does TF want to change?
terraform plan -refresh-only           # what changed in real infra without TF action?
terraform state show <resource>        # current state for one resource
terraform state list | grep <pattern>
```

Common drift sources:

- Manual change in console
- Another stack / workspace owns the same resource
- Provider version bump changed default arguments
- A `count`/`for_each` shifted indices (every downstream resource thinks it's new)

### Provider auth fails

- Local: stale `aws-vault`/`gcloud auth`/`az login` tokens
- CI: OIDC role trust policy missing the new repo / branch / environment
- Cross-account: role chain assume permissions

### Module / pin issues

- Pin module versions (`source = "...//module?ref=v1.2.3"`)
- Provider versions (`required_providers { ... version = "~> 5.0" }`)

## Networking

| Symptom | Where to look |
|---|---|
| `connection refused` | App not listening on the expected port; `0.0.0.0` vs `127.0.0.1` bind |
| `connection timeout` | Network path: SG/NSG/firewall, NetworkPolicy, peering, NAT |
| TLS handshake fails | Cert expired, SNI mismatch, intermediate not bundled, clock drift |
| Intermittent 502/503 | Upstream health check / readiness probe / pool draining |
| DNS resolution fails | CoreDNS health, Pod `dnsPolicy`, Search domains, ExternalName |

```bash
curl -vk -w "TLS: %{time_appconnect}s | total: %{time_total}s\n" https://host/path
openssl s_client -connect host:443 -servername host </dev/null
dig +short host
```

## Cloud-specific quick checks

| Provider | Quick check |
|---|---|
| **AWS** | `aws sts get-caller-identity`; CloudTrail for the failing API call; `aws ecs describe-tasks --cluster <c> --tasks <id>` for ECS task failures |
| **GCP** | `gcloud auth list`; Cloud Logging "Logs Explorer" with `resource.type` filter; `gcloud run services describe <svc>` |
| **Cloudflare** | `wrangler deploy --dry-run`; `wrangler tail <worker>` for live logs; check `wrangler.toml` env routing |
| **Fly.io** | `flyctl logs -a <app>`; `flyctl status -a <app>` |

## After the fix

Apply `defense-in-depth.md` at the layers that actually matter for infra:

- **Layer 1 — entry validation** in IaC: required-vars, type, allowed-values
- **Layer 2 — runtime guard**: K8s `resources.limits`, NetworkPolicy default-deny, PodSecurity admission
- **Layer 3 — environment guard**: prod-only `lifecycle.prevent_destroy`, deletion protection on RDS / Cloud SQL, retention locks
- **Layer 4 — observability**: cloudwatch / cloud logging alerts, K8s events archived, audit log retention

Then `verification.md` — fresh evidence (logs, healthy probe, real request through Ingress) before claiming done.
