---
name: cnpg
description: >
  Create and operate CloudNativePG (CNPG) Postgres databases on Kubernetes the
  GitOps/Flux way — on managed cloud (GKE + GCS via Workload Identity) OR
  self-hosted (K3s/bare-metal + any S3-compatible store via a credentials
  secret). Covers Cluster + ScheduledBackup manifests, barman WAL archiving,
  pgvector, PITR, prod→dev clones, and the NetworkPolicies a default-deny cluster
  needs. Use when provisioning a new app database, cloning prod into dev, enabling
  pgvector, wiring backups/PITR, writing CNPG NetworkPolicies, or debugging the
  silent "WAL archiving failed → PVC fills → Postgres CrashLoop → app can't read
  data" chain on CloudNativePG.
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# cnpg

Provision and run CloudNativePG (CNPG) Postgres on Kubernetes as GitOps. Every
concrete identifier below is a placeholder — substitute your own:
`<project>`, `<gcp-sa>`, `<backups-bucket>`, `<cluster>`, `<ns>`, `<svc>`,
`<db>`, `<owner>`, `<env>`, `<s3-endpoint>`, `<objstore-secret>`, `<app-ns>`.

**Two platforms, one operator.** The Cluster spec, bootstrap, pgvector, PITR,
clone, and most gotchas are identical everywhere. Only **backup auth** and
**NetworkPolicy** differ:

- **Managed cloud (GKE + GCS):** backup auth = Workload Identity (no keys).
  Steps below default to this.
- **Self-hosted (K3s / bare-metal + S3-compatible store: MinIO, Ceph, R2, B2):**
  backup auth = an access-key Secret; plus a default-deny cluster needs explicit
  NetworkPolicies. See **`references/self-hosted-and-networkpolicy.md`** — read it
  whenever there's no cloud Workload Identity or the cluster enforces default-deny.

## Mental model — two halves that MUST share one string

A CNPG database on GKE is two halves that have to agree on exactly one string,
`<ns>/<cluster>`:

1. **GitOps half (k8s YAML):** a CNPG `Cluster` whose `serviceAccountTemplate`
   annotation points the auto-created **pod KSA** at the GCP backup SA. CNPG
   names that pod KSA after the **cluster** (`<cluster>`) in `<ns>`. Any
   standalone `ServiceAccount` named `cnpg-backup-sa` you find in a folder is a
   **decoy/legacy** resource — CNPG does **not** use it for backup auth.
2. **GCP half (Terraform):** an IAM `workloadIdentityUser` binding whose member
   is `serviceAccount:<project>.svc.id.goog[<ns>/<cluster>]`, plus the GCS
   backups bucket + lifecycle.

Deploy is pure GitOps: commit YAML → a Flux `Kustomization` (`dependsOn:
database-operators`) reconciles → the CNPG operator builds the cluster.
**Terraform (WI binding + bucket) must already be applied**, or the cluster
bootstraps but backups fail silently.

## Step 0 — prerequisites

- CNPG operator reconciled (a `database-operators` Flux Kustomization).
- GKE Workload Identity enabled; a shared per-env backup SA
  `<gcp-sa>@<project>.iam.gserviceaccount.com` exists.
- SOPS age key available to Flux (`decryption.secretRef`).
- (pgvector) the operand image ships the `vector` lib — it is **available, not
  installed**; the non-superuser app role cannot install it (see gotchas).
- (affinity) a dedicated DB node pool with the expected taint + label, else drop
  the `affinity` block.
- (cloud) ship Terraform via PR off `origin/main`. Terragrunt auth = personal ADC
  or `GOOGLE_OAUTH_ACCESS_TOKEN` (no SA key needed; SA keys often can't read tfstate).
- (self-hosted) an S3-compatible object store reachable from the cluster + an
  encrypted credentials Secret; a `storageClass` that exists (e.g. `local-path`,
  `longhorn`); and if the cluster is default-deny, the NetworkPolicies from the
  reference. Know your CNI (Cilium → `CiliumNetworkPolicy`; Calico → vanilla).

## Step 1 — backup auth

**Self-hosted (S3-compatible):** skip the Terraform/Workload-Identity below —
create an encrypted access-key Secret and use `s3Credentials` + `endpointURL` in
the barman config. Full manifests in `references/self-hosted-and-networkpolicy.md`.

**Managed cloud (GKE + GCS), Terraform BEFORE Flux:**
Append the new cluster's pod KSA to the shared backup SA
(`terraform/gcp/<env>/service-accounts/service-accounts.yaml`):

```yaml
service_accounts:
  <gcp-sa>:
    display_name: "<Env> CloudNativePG Backup Service Account"
    project_roles:
      - "roles/storage.admin"        # objectAdmin LACKS storage.buckets.get → barman fails; use admin or a bucket-level binding
    workload_identity_bindings:
      - "cnpg-system/cnpg-backup"
      - "<ns>/<cluster>"             # ← ADD THIS. Member = <namespace>/<cluster>, NOT cnpg-backup-sa
```

Renders to member `serviceAccount:<project>.svc.id.goog[<ns>/<cluster>]`, role
`roles/iam.workloadIdentityUser`.

Backups bucket (`terraform/gcp/<env>/gcs/buckets.yaml`):

```yaml
backups:
  name: <backups-bucket>
  location: US
  lifecycle_rules:
    - action: { type: Delete }
      condition: { age: 30 }         # BACKSTOP only — MUST exceed barman retentionPolicy or PITR breaks
  versioning: false                  # prod: true
  uniform_bucket_level_access: true
  force_destroy: true                # dev only; prod: false
  iam_bindings:
    - { service_account: <gcp-sa>, role: roles/storage.admin }
```

One shared backups bucket per env; each cluster isolates under its own
`cnpg/<svc>` prefix. Apply the SA dir, then the GCS dir.

## Step 2 — the app DB folder `fluxcd/databases/<env>/<svc>/`

`kustomization.yaml` in dependency order (namespace + secret first, then
cluster, then extensions + backup):

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml          # <ns>; labels app.kubernetes.io/part-of: databases
  - secrets.enc.yaml        # SOPS-encrypted app credentials (username/password) — referenced by initdb.secret.name
  - database.yaml           # the Cluster CR
  - database-vector.yaml    # pgvector Database CR (only if needed)
  - scheduled-backup.yaml   # ScheduledBackup CR
```

## Step 3 — the Cluster + ScheduledBackup

`database.yaml`:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: <cluster>
  namespace: <ns>
  labels:
    app.kubernetes.io/name: <cluster>
    app.kubernetes.io/component: database
    app.kubernetes.io/part-of: databases
  annotations:
    cnpg.io/skipEmptyWalArchiveCheck: "enabled"   # let cluster start before first WAL is archived
spec:
  instances: 1                                      # 2 in prod (1 primary + 1 replica → failover)
  imageName: ghcr.io/cloudnative-pg/postgresql:16.4 # pin major+minor; bump deliberately (image swap = DB restart)
  storage:
    size: 40Gi                                      # WAL lands here too — undersize + stuck WAL = PVC full → CrashLoop
    storageClass: standard                          # premium-rwo (SSD) in prod
    resizeInUseVolumes: true                        # allow online expansion
  postgresql:
    parameters:
      max_connections: "100"
      shared_buffers: "256MB"
      effective_cache_size: "768MB"                 # ~75% of mem limit; scale in prod
      maintenance_work_mem: "128MB"
      checkpoint_completion_target: "0.9"
      wal_buffers: "16MB"
      random_page_cost: "1.1"                       # SSD-friendly
      work_mem: "4MB"
      wal_compression: "on"
  bootstrap:
    initdb:                                         # fresh cluster; use bootstrap.recovery to clone a backup (see Reuse)
      database: <db>
      owner: <owner>
      secret:
        name: <svc>-app-credentials                 # SOPS-managed, listed in kustomization
      dataChecksums: true                           # init-only; cannot toggle later without re-bootstrap
      postInitApplicationSQL:
        - CREATE EXTENSION IF NOT EXISTS vector      # superuser at init; drop if no pgvector
  serviceAccountTemplate:
    metadata:
      annotations:
        iam.gke.io/gcp-service-account: <gcp-sa>@<project>.iam.gserviceaccount.com  # THE WI link
  monitoring:
    customQueriesConfigMap: []                       # enables the CNPG metrics exporter sidecar
  resources:
    requests: { memory: "512Mi", cpu: "100m" }
    limits:   { memory: "1Gi",   cpu: "500m" }       # keep PG mem params below this or OOM
  backup:                                            # INLINE model — being deprecated; prefer the plugin (see note below)
    barmanObjectStore:
      destinationPath: "gs://<backups-bucket>/cnpg/<svc>"   # PARENT prefix only — CNPG appends the serverName; don't double-nest <cluster>/<cluster>
      googleCredentials:
        gkeEnvironment: true                         # GKE Workload Identity (no key file).
      # SELF-HOSTED S3-compatible instead of googleCredentials:
      #   endpointURL: <s3-endpoint>                 # https://<acct>.r2.cloudflarestorage.com | http://minio.minio.svc:9000
      #   s3Credentials:
      #     accessKeyId:     { name: <objstore-secret>, key: ACCESS_KEY_ID }
      #     secretAccessKey: { name: <objstore-secret>, key: SECRET_ACCESS_KEY }
      wal:  { compression: gzip, maxParallel: 2 }
      data: { compression: gzip, jobs: 2 }
    retentionPolicy: "7d"                            # "30d" in prod; barman is the authority on deletion
  primaryUpdateStrategy: unsupervised
  affinity:                                          # pin to dedicated DB node pool (omit if none)
    tolerations:
      - { key: "database-node", operator: "Equal", value: "dedicated", effect: "NoSchedule" }
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: node-restriction.kubernetes.io/database
                operator: In
                values: ["dedicated"]
```

`scheduled-backup.yaml`:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: <cluster>-daily
  namespace: <ns>
  labels: { app.kubernetes.io/name: <cluster>, app.kubernetes.io/component: backup }
spec:
  schedule: "0 3 * * *"          # CNPG cron = 6 fields; daily 03:00
  backupOwnerReference: self
  cluster: { name: <cluster> }
  method: barmanObjectStore
  immediate: true                # take one backup right after creation
  suspend: false
```

> **Plugin vs inline backup config.** CNPG is moving Barman Cloud support out of
> core into a **plugin**. Inline `spec.backup.barmanObjectStore` (above) still
> works but is **deprecated** (slated for removal ~CNPG 1.28). On a fresh cluster
> prefer the plugin: an `ObjectStore` CRD (`barmancloud.cnpg.io/v1`) + a
> `spec.plugins: [{ name: barman-cloud.cloudnative-pg.io, isWALArchiver: true,
> parameters: { barmanObjectName: ... } }]` reference. Full plugin manifests (and
> the S3 variant) are in `references/self-hosted-and-networkpolicy.md`.

## Step 4 — pgvector (belt-and-suspenders, only if needed)

Layer 1 is the `postInitApplicationSQL` above (race-free at initdb, before the
app connects). Layer 2 is a continuously-reconciled `Database` CR
(`database-vector.yaml`) that self-heals drift on an existing cluster:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Database
metadata: { name: <cluster>-vector, namespace: <ns> }
spec:
  cluster: { name: <cluster> }
  name: <db>
  owner: <owner>
  ensure: present
  databaseReclaimPolicy: retain   # deleting this CR NEVER drops the database
  extensions:
    - { name: vector, ensure: present }
```

## Step 5 — the Flux Kustomization (one per noisy DB, for fault isolation)

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata: { name: databases-<svc>, namespace: flux-system }
spec:
  interval: 10m0s
  path: ./fluxcd/databases/<env>/<svc>
  prune: true
  sourceRef: { kind: GitRepository, name: flux-system }
  dependsOn:
    - name: database-operators           # CNPG operator/CRDs must exist first
  decryption:
    provider: sops
    secretRef: { name: sops-age-key }    # secrets.enc.yaml is SOPS-encrypted
```

Give a busy DB its **own** Kustomization **and** omit it from any shared
`databases` Kustomization resource list — never both (double ownership conflicts).

## Step 6 — deploy

1. Write the SOPS-encrypted `secrets.enc.yaml` (keys `initdb.secret.name` expects).
2. Apply Terraform (Step 1) so backups authenticate on day one.
3. Commit all YAML + the Flux Kustomization, PR off `origin/main`, merge.
4. `flux reconcile kustomization databases-<svc>`.
5. Verify (below).

## NetworkPolicy (default-deny clusters — usually self-hosted)

If the cluster enforces default-deny, CNPG silently breaks without explicit
allows. Match the resource KIND to the CNI (Cilium → `CiliumNetworkPolicy`;
Calico/standard → vanilla `NetworkPolicy`). For instance pods
(`cnpg.io/podRole: instance`) allow, at minimum:

- **Ingress:** kubelet/host probes · same-namespace (replication) · `<app-ns>` →
  `5432` · monitoring → `9187` · `cnpg-system` operator.
- **Egress:** object store (`443` or store port) for barman · DNS `kube-system:53`
  · kube-apiserver · same-namespace · **the service CIDR** (e.g. K3s default
  `10.43.0.0/16`) when the CNI is Cilium with eBPF kube-proxy replacement —
  ClusterIP services aren't pods, so this is required or in-cluster lookups fail.

Full Cilium + vanilla manifests, the operator policy, and the host-firewall
caveat are in `references/self-hosted-and-networkpolicy.md`.

## Gotchas — hard-won, worth noting

- **Bind the `<cluster>` pod KSA, not the decoy `cnpg-backup-sa`.** The WI member
  must be `<ns>/<cluster>` (the cluster-named pod KSA CNPG auto-creates). WI needs
  BOTH halves: the KSA annotation AND the reverse `workloadIdentityUser` binding —
  a present annotation with a missing binding still yields 403. Verify the real
  `spec.serviceAccountName` on the live pod before trusting any SA manifest name.
  *Top footgun.*
- **WAL-archive failure is a silent disk-exhaustion bomb.** Symptom chain: barman
  exit 4 → `ContinuousArchiving=False` → WAL piles on the PVC → CrashLoop → app
  shows a generic "can't read data" error. When a CNPG-backed app suddenly can't
  read, check `kubectl get cluster <cluster> -n <ns>` (ContinuousArchiving +
  disk) **before** debugging the app. Audit ALL clusters together — the root cause
  is usually the shared SA/binding.
- **GCS lifecycle must be a loose backstop strictly LONGER than barman retention.**
  barman keeps an anchor base backup OLDER than the window (daily backups → ~N+1d)
  plus its WALs; a `Delete @ Nd` lifecycle races ahead and deletes the anchor →
  broken PITR + phantom catalog entries. Let barman own deletion for live clusters;
  size the GCS rule only to reap orphans from deleted clusters. Trimming this bucket
  "for cost" is false economy.
- **pgvector must be installed by a superuser, declaratively — never the app role.**
  The app role isn't superuser and `vector` isn't trusted, so an app-role
  `CREATE EXTENSION vector` (e.g. in a migration) fails "must be superuser" and
  crash-loops the backend. Use `postInitApplicationSQL` (fresh clusters) and/or a
  `Database` CR with `ensure: present` (existing clusters). Then app-role
  `CREATE EXTENSION IF NOT EXISTS` no-ops cleanly.
- **The git `bootstrap` stanza MUST match the live cluster's method; it's
  create-time-only.** The webhook rejects "Only one bootstrap method can be
  specified at a time" if git says `initdb` but the cluster was `recovery`-
  bootstrapped (or vice versa). To switch, delete + recreate. Take a manual backup
  first.
- **Give each app's DB its own Flux Kustomization — never share an atomic one.**
  A shared Kustomization applies atomically, so ONE drifted/webhook-rejected
  sibling Cluster blocks EVERY other DB — including a brand-new cluster that can
  then never apply.
- **`destinationPath` is the PARENT prefix only.** CNPG/barman auto-appends the
  serverName; writing `.../cnpg/<svc>/<cluster>` yields a double-nested
  `.../<cluster>/<cluster>/` that breaks discovery/restore. On a legitimate
  re-create over a path holding the cluster's own prior WALs, set the
  `skipEmptyWalArchiveCheck` annotation (confirm it's the same cluster's data first).
- **CNPG hard-refuses to start under low disk** ("Detected low-disk space
  condition") → CrashLoopBackOff, not a warning. Size the PVC for WAL
  (≥ several × `max_wal_size`) + data + backup headroom; enable
  `resizeInUseVolumes`. Codify any manual PVC expansion back into git or GitOps
  reverts it. Repeated disk-fill = fix WAL archiving/retention, don't just keep
  doubling storage.
- **WAL-archive alerts must be cluster-agnostic (label-based).** Because the
  failure is silent, alert on it: `CNPGWalArchivingFailing` (last archive failed
  more recently than it succeeded) + `CNPGWalReadyBacklogHigh` (>100 ready
  segments). Scope by `and on (namespace,pod) cnpg_collector_up` — a
  hardcoded/nonexistent namespace selector is a DEAD alert that never fires with
  green dashboards. Confirm >0 series live (`promtool` + real metric names).
- **`podMonitor`/`serviceMonitor: true` requires the Prometheus Operator CRDs.**
  A standalone (non-operator) Prometheus has none, so the chart's PodMonitor apply
  fails silently on EVERY reconcile. Match the toggle to whether the CRDs exist;
  scrape via static config otherwise.
- **Default-deny NetworkPolicy silently breaks CNPG (self-hosted).** On a
  default-deny cluster, missing allows look like a broken DB, not a network issue:
  no object-store egress → WAL archiving fails (the silent disk bomb); no DNS →
  can't resolve services; no same-namespace → replicas can't reach the primary.
  With Cilium's eBPF kube-proxy replacement you ALSO must allow egress to the
  service CIDR (ClusterIP isn't a pod). Match the policy KIND to the CNI. After
  adding policies and seeing archiving fail, suspect a missing egress allow first.
- **Backup config: plugin is current, inline is deprecated.** Newer CNPG moves
  Barman Cloud into a plugin (`ObjectStore` CRD + `spec.plugins`); inline
  `spec.backup.barmanObjectStore` is slated for removal (~1.28) — a deprecation
  warning fires on every reconcile. A dangling/mistyped `barmanObjectName` (plugin)
  or a missing `ObjectStore` silently blocks the cluster. Pick ONE model per cluster.
- **`alembic upgrade head` runs at boot** — a migration fault crash-loops the pod,
  and CI using `create_all` won't catch it. Use unique descriptive revision IDs
  (≤32 chars; sequential ones collide → "multiple heads"), add a
  `test_alembic_single_head` guard, and verify
  `git merge-base --is-ancestor <fix> <tag>` before releasing.
- **`instances: 1` has no failover.** Any primary pod recreation (node event,
  eviction) is a brief (~7s) connection-refused window → app 5xx. Transient DB
  errors correlated with a fresh DB pod (0 restarts, recent transition) are this,
  not an app bug. Scale instances for HA.

## Verification

```bash
# Cluster healthy + archiving on
kubectl get cluster <cluster> -n <ns>      # expect "Cluster in healthy state"
kubectl get cluster <cluster> -n <ns> -o jsonpath='{.status.conditions[?(@.type=="ContinuousArchiving")].status}{"\n"}'  # True

# Pods + first backup
kubectl get pods -n <ns> -l postgresql=<cluster>      # Running/Ready (1 dev, 2 prod)
kubectl get scheduledbackup,backup -n <ns>            # immediate backup → completed

# Archive auth test in-pod — VALID WAL name + real exit code (never /dev/null; ~1 min for WI propagation)
kubectl exec -n <ns> <cluster>-1 -- bash -c \
  'barman-cloud-wal-archive --test gs://<backups-bucket>/cnpg/<svc> <cluster> 000000010000000000000001; echo EXIT=${PIPESTATUS[0]}'  # EXIT=0

# ContinuousArchiving is sticky — force a fresh segment to flip it + drain backlog
kubectl exec -n <ns> <cluster>-1 -- psql -U postgres -c 'SELECT pg_switch_wal();'

# pgvector + connectivity + objects in GCS
kubectl exec -n <ns> <cluster>-1 -- psql -U postgres -d <db> -c '\dx'        # vector listed
kubectl exec -n <ns> <cluster>-1 -- psql -U <owner> -d <db> -c 'SELECT 1;'
gcloud storage ls gs://<backups-bucket>/cnpg/<svc>/                          # base backup + WAL objects
```

Self-hosted has no WI token test; check the `ContinuousArchiving` condition + the
instance logs for `403`/`AccessDenied`/endpoint errors, and list objects with
`aws s3 ls s3://<backups-bucket>/<svc>/ --endpoint-url <s3-endpoint>` (or `mc ls`).
See the reference for details.

## Reuse — clone prod→dev and re-clone

- **Clone prod → dev with data:** use `bootstrap.recovery` (not `initdb`) with
  `externalClusters` pointing at the prod backups prefix
  (`gs://<backups-bucket>/cnpg/<svc>`), and grant the dev backup SA cross-env read
  on the prod prefix. Declare `recovery` in **git** (Flux-owned) — a manual
  `kubectl` restore over a git `initdb` is what causes the two-bootstrap-methods
  conflict.
- **Re-clone (refresh dev from prod):** `bootstrap` is create-time-only and
  immutable — DELETE and RECREATE the Cluster (editing bootstrap in place does
  nothing). Back up first if it holds anything you care about.
- **Recovery can't outrun WI/IAM propagation:** if the binding letting the dev
  restore read the prod backup isn't live yet, recovery fails — in dev, fall back
  to a fresh `initdb` rather than blocking.
- **Another app DB in the same env:** copy `fluxcd/databases/<env>/<svc>/` to
  `<svc2>`, swap names, append the new `<ns2>/<cluster2>` WI binding to the
  **shared** `<gcp-sa>`, reuse the shared bucket under a new `cnpg/<svc2>` prefix,
  and give it its OWN Flux Kustomization.
- **Promote dev → prod tuning:** `instances: 2`, `storageClass: premium-rwo`,
  `effective_cache_size` ~75% of the larger limit, `retentionPolicy: 30d` (with a
  longer GCS backstop), bucket `versioning: true` + `force_destroy: false`.
