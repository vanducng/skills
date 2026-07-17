# Kubernetes: kubectl, Debugging, Helm, Security

## kubectl essentials

```bash
# Cluster & nodes
kubectl cluster-info
kubectl get nodes && kubectl top nodes
kubectl drain <node> --ignore-daemonsets   # cordon + evict before maintenance
kubectl uncordon <node>

# Pods
kubectl get pods -A -o wide                 # all namespaces, node placement
kubectl describe pod <pod>
kubectl logs -f <pod>                        # follow
kubectl logs --previous <pod>                # last crashed instance
kubectl exec -it <pod> -- /bin/sh

# Apply / rollout
kubectl apply -f manifests/ --dry-run=client -o yaml   # preview first
kubectl apply -f manifests/
kubectl rollout status deploy/myapp
kubectl set image deploy/myapp app=myapp:v2
kubectl rollout undo deploy/myapp            # rollback
kubectl rollout restart deploy/myapp

# Networking
kubectl get svc && kubectl get endpoints <svc>
kubectl port-forward svc/myapp 8080:8080
```

Useful flags: `-n` namespace, `-A` all namespaces, `-o wide|json|yaml`, `-l app=x,tier=y` label selector, `-w` watch, `--field-selector=status.phase=Running`.

## Debugging workflow (get → describe → logs → events)

```bash
kubectl get pods -o wide
kubectl get events -n <ns> --sort-by='.lastTimestamp'
kubectl describe pod <pod>
kubectl logs <pod> --previous -c <container>
```

| Pod state | Cause | Fix |
| --- | --- | --- |
| **Pending** | No schedulable node / resources | `kubectl describe pod` events; check requests vs node capacity, taints |
| **ContainerCreating** | Image pulling, volume mount | Check image URI, PVC binding |
| **ImagePullBackOff** | Bad image ref / auth | Verify tag exists and imagePullSecrets |
| **CrashLoopBackOff** | Container exits repeatedly | `logs --previous`; check command, env, failing liveness probe |
| **OOMKilled (137)** | Exceeded memory limit | Raise `resources.limits.memory` or fix the leak |

Quick moves: `kubectl top pods -A --sort-by=memory`; force-delete a stuck pod `kubectl delete pod <name> --grace-period=0 --force` (last resort); DNS check `kubectl exec -it <pod> -- nslookup kubernetes.default`.

## Manifests

Always set resource requests/limits, liveness + readiness probes, and a non-root securityContext:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: myapp }
spec:
  replicas: 3
  selector: { matchLabels: { app: myapp } }
  template:
    metadata: { labels: { app: myapp } }
    spec:
      securityContext: { runAsNonRoot: true, runAsUser: 1000 }
      containers:
        - name: app
          image: registry.example.com/myapp:1.2.3   # pinned, never latest
          ports: [{ containerPort: 8080 }]
          resources:
            requests: { cpu: 100m, memory: 128Mi }
            limits:   { cpu: 500m, memory: 256Mi }
          readinessProbe: { httpGet: { path: /healthz, port: 8080 }, initialDelaySeconds: 5 }
          livenessProbe:  { httpGet: { path: /healthz, port: 8080 }, periodSeconds: 10 }
```

## Helm

Package manager for K8s — templated manifests with values overlays.

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami && helm repo update
helm install myrelease bitnami/postgresql -n data --create-namespace \
  -f values.prod.yaml
helm template myrelease ./chart -f values.yaml    # render locally, no cluster
helm upgrade --install myrelease ./chart -f values.yaml --atomic --wait
helm diff upgrade myrelease ./chart               # (helm-diff plugin) preview
helm rollback myrelease 1
helm uninstall myrelease -n data
```

`--atomic` rolls back automatically on a failed upgrade; `--install` makes upgrade idempotent. Keep environment differences in `values.<env>.yaml`, secrets out of values (use sealed-secrets / external-secrets).

## Security (RBAC, secrets, network)

- **RBAC least-privilege:** scope `Role`/`RoleBinding` to a namespace; reserve `ClusterRole` for genuinely cluster-wide needs. Bind ServiceAccounts, not users, for workloads.
- **Secrets** are base64, not encrypted at rest by default — enable etcd encryption, or use external-secrets/sealed-secrets/a cloud secret manager. Never commit raw `Secret` manifests.
- **NetworkPolicies** default-deny then allow explicitly; `securityContext` with `runAsNonRoot`, `readOnlyRootFilesystem`, dropped capabilities.
- Scan images before deploy; use Pod Security Admission (`restricted`) to enforce baseline.
