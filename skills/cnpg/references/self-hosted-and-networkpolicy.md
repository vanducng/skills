# Self-hosted CNPG (no cloud Workload Identity) + NetworkPolicy

Companion to the main `cnpg` skill for clusters that are **not** on a managed
cloud with Workload Identity — e.g. K3s / bare-metal / VPS with an
S3-compatible object store (MinIO, Ceph/RGW, SeaweedFS, Backblaze B2,
Cloudflare R2). Placeholders: `<s3-endpoint>`, `<backups-bucket>`,
`<objstore-secret>`, `<cluster>`, `<ns>`, `<svc>`, `<db>`, `<owner>`,
`<app-ns>`, `<service-cidr>`.

## 1. Backup auth = a credentials Secret (not Workload Identity)

There is no `<ns>/<cluster>` IAM binding and no Terraform. barman authenticates
to the object store with an access key from a k8s Secret. Encrypt it (SOPS+age,
sealed-secrets, or your tool) — never commit plaintext.

```yaml
# <objstore-secret>.enc.yaml  (SOPS-encrypted; data/stringData only)
apiVersion: v1
kind: Secret
metadata:
  name: <objstore-secret>          # e.g. cnpg-objstore-credentials
  namespace: <ns>
type: Opaque
stringData:
  ACCESS_KEY_ID: <redacted>
  SECRET_ACCESS_KEY: <redacted>
```

To reuse one credential across DB namespaces, sync it with a reflector
(e.g. emberstack reflector) rather than duplicating the secret:

```yaml
metadata:
  annotations:
    reflector.v1.k8s.emberstack.com/reflection-allowed: "true"
    reflector.v1.k8s.emberstack.com/reflection-allowed-namespaces: <app-ns>
    reflector.v1.k8s.emberstack.com/reflection-auto-enabled: "true"
```

## 2. Two ways to wire barman to S3 — prefer the plugin

CNPG is moving Barman Cloud support **out of core into a plugin**. Inline
`spec.backup.barmanObjectStore` still works but is **deprecated** (slated for
removal ~CNPG 1.28). On a fresh self-hosted cluster, use the plugin.

### 2a. Plugin model (current / recommended)

Install the barman-cloud plugin once (operator-side), then per DB:

```yaml
# objectstore.yaml — the S3 destination, referenced by the Cluster
apiVersion: barmancloud.cnpg.io/v1
kind: ObjectStore
metadata:
  name: <svc>-s3-store
  namespace: <ns>
spec:
  configuration:
    destinationPath: s3://<backups-bucket>/<svc>     # PARENT prefix; CNPG appends serverName
    endpointURL: <s3-endpoint>                        # e.g. https://<acct>.r2.cloudflarestorage.com or http://minio.minio.svc:9000
    s3Credentials:
      accessKeyId:     { name: <objstore-secret>, key: ACCESS_KEY_ID }
      secretAccessKey: { name: <objstore-secret>, key: SECRET_ACCESS_KEY }
    wal:  { compression: gzip }
    data: { compression: gzip }
  retentionPolicy: "7d"
---
# in the Cluster spec, attach the plugin instead of spec.backup:
spec:
  plugins:
    - name: barman-cloud.cloudnative-pg.io
      isWALArchiver: true
      parameters:
        barmanObjectName: <svc>-s3-store
```

### 2b. Inline model (legacy / deprecated — for older operators)

```yaml
spec:
  backup:
    barmanObjectStore:
      destinationPath: s3://<backups-bucket>/<svc>     # PARENT prefix only
      endpointURL: <s3-endpoint>
      s3Credentials:
        accessKeyId:     { name: <objstore-secret>, key: ACCESS_KEY_ID }
        secretAccessKey: { name: <objstore-secret>, key: SECRET_ACCESS_KEY }
      wal:  { compression: gzip, maxParallel: 2 }
      data: { compression: gzip, jobs: 2 }
    retentionPolicy: "7d"
```

## 3. Self-hosted Cluster example (plugin model, local storage)

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: <cluster>
  namespace: <ns>
spec:
  instances: 1
  imageName: ghcr.io/cloudnative-pg/postgresql:18-standard-trixie
  storage:
    size: 5Gi
    storageClass: local-path          # bare-metal default (local-path / longhorn / openebs)
  bootstrap:
    initdb:
      database: <db>
      owner: <owner>
      postInitSQL:                     # NOTE: plugin/newer CNPG uses postInitSQL; some versions postInitApplicationSQL
        - CREATE EXTENSION IF NOT EXISTS vector;
  monitoring:
    enablePodMonitor: true            # needs Prometheus Operator CRDs (see gotcha in SKILL.md)
  resources:
    requests: { memory: "256Mi", cpu: "200m" }
    limits:   { memory: "512Mi", cpu: "2000m" }
  plugins:
    - name: barman-cloud.cloudnative-pg.io
      isWALArchiver: true
      parameters: { barmanObjectName: <svc>-s3-store }
```

Notes vs the cloud recipe: no `serviceAccountTemplate` WI annotation (auth is the
Secret), `storageClass: local-path` instead of `premium-rwo`, `local-path` is
node-bound so a single-instance cluster is pinned to one node (no cross-node
reschedule without replication or a networked storage class).

## 4. NetworkPolicy — REQUIRED on default-deny clusters

If the cluster enforces default-deny (any policy selecting a pod implies
deny-all for it), CNPG **silently breaks** without explicit allows — barman
egress to the object store fails, DNS fails, replicas can't reach the primary.
Match the resource KIND to the CNI:

- **Cilium** (eBPF; common on K3s with kube-proxy replacement) → `CiliumNetworkPolicy`.
- **Calico / others honoring vanilla** → `networking.k8s.io NetworkPolicy`.

### Required flows for CNPG instance pods (`cnpg.io/podRole: instance`)

| Direction | Peer | Port | Why |
|---|---|---|---|
| Ingress | kubelet / host | probes | health checks (else pod marked unready) |
| Ingress | same namespace | all | replica ↔ primary replication |
| Ingress | `<app-ns>` | 5432/TCP | app → DB |
| Ingress | monitoring ns | 9187/TCP | Prometheus scrape (metrics exporter) |
| Ingress | cnpg-system | webhook/all | operator manages the cluster |
| Egress | object store | 443/TCP (or store port) | **barman WAL/base backup** |
| Egress | kube-system (CoreDNS) | 53/UDP+TCP | service-name resolution |
| Egress | kube-apiserver | all | operator/instance API calls |
| Egress | same namespace | all | replication |
| Egress | **`<service-cidr>`** | all | **Cilium eBPF kube-proxy replacement** — ClusterIP services live in a virtual CIDR (K3s default `10.43.0.0/16`), not as pods; without this, in-cluster service access silently fails |

### Cilium example (the load-bearing egress allows)

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata: { name: cnpg-egress, namespace: <ns> }
spec:
  endpointSelector:
    matchLabels: { cnpg.io/podRole: instance }
  egress:
    - toEntities: [world]                       # barman → S3/R2 endpoint
      toPorts: [{ ports: [{ port: "443", protocol: TCP }] }]
    - toEndpoints:                              # DNS
        - matchLabels: { k8s:io.kubernetes.pod.namespace: kube-system }
      toPorts: [{ ports: [{ port: "53", protocol: UDP }, { port: "53", protocol: TCP }] }]
    - toEndpoints: [{}]                         # same-namespace (replication)
    - toCIDR: ["10.43.0.0/16"]                  # <service-cidr> — ClusterIP via eBPF
    - toEntities: [kube-apiserver]
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata: { name: cnpg-ingress, namespace: <ns> }
spec:
  endpointSelector:
    matchLabels: { cnpg.io/podRole: instance }
  ingress:
    - fromEntities: [host, remote-node]                       # kubelet probes
    - fromEndpoints: [{}]                                     # same-namespace replication
    - fromEndpoints:                                          # app → 5432
        - matchLabels: { k8s:io.kubernetes.pod.namespace: <app-ns> }
      toPorts: [{ ports: [{ port: "5432", protocol: TCP }] }]
    - fromEndpoints:                                          # metrics scrape
        - matchLabels: { k8s:io.kubernetes.pod.namespace: monitoring }
      toPorts: [{ ports: [{ port: "9187", protocol: TCP }] }]
    - fromEndpoints:                                          # operator
        - matchLabels: { k8s:io.kubernetes.pod.namespace: cnpg-system }
```

### Vanilla NetworkPolicy example (Calico / standard enforcers)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: cnpg, namespace: <ns> }
spec:
  podSelector: { matchLabels: { cnpg.io/podRole: instance } }
  policyTypes: [Ingress, Egress]
  ingress:
    - from: [{ podSelector: {} }]                                   # same-ns replication
    - from: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: <app-ns> } } }]
      ports: [{ port: 5432, protocol: TCP }]
    - from: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: monitoring } } }]
      ports: [{ port: 9187, protocol: TCP }]
    - from: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: cnpg-system } } }]
  egress:
    - to: [{ podSelector: {} }]                                     # same-ns replication
    - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } }]
      ports: [{ port: 53, protocol: UDP }, { port: 53, protocol: TCP }]
    - to: [{ ipBlock: { cidr: 0.0.0.0/0 } }]                        # barman → object store (tighten to the store CIDR if known)
      ports: [{ port: 443, protocol: TCP }]
```

Also give the **operator** (`cnpg-system`) its own policy: ingress from
kube-apiserver (webhook :9443) + monitoring (:8080); egress to the DB namespaces,
kube-apiserver, DNS, and the service CIDR. And remember the host firewall
(UFW/iptables on bare metal) is a separate layer from k8s NetworkPolicy — both
must allow the traffic (e.g. node ports for the CNI overlay/VXLAN, kubelet :10250).

## 5. Self-hosted verification deltas

- No WI token test. Confirm barman with the Secret: check archiving status
  `kubectl get cluster <cluster> -n <ns> -o jsonpath='{.status.conditions[?(@.type=="ContinuousArchiving")].status}'`
  and look for `403`/`AccessDenied`/endpoint errors in the instance logs.
- Backups land via S3 API: `aws s3 ls s3://<backups-bucket>/<svc>/ --endpoint-url <s3-endpoint>`
  (or `mc ls` for MinIO) instead of `gcloud storage ls`.
- If archiving fails right after adding policies, suspect a missing egress allow
  (object-store :443, DNS :53, or the service CIDR for Cilium) before anything else.
