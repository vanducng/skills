# Red-Team Personas

`--red-team` runs the threat pass from distinct attacker viewpoints - each persona is blind to what the others surface, so they catch different classes. Iterative, bounded.

## Personas

| Persona | Goal | Asks |
|---|---|---|
| **External attacker** | Break in unauthenticated | Which endpoints/inputs are reachable without auth? Injection, SSRF, auth bypass, enumeration. |
| **Authenticated user / tenant** | Escalate or cross boundaries | IDOR, missing object-level authz, role confusion, cross-tenant reads, mass-assignment. |
| **Supply chain** | Compromise via dependencies/build | Vulnerable/unpinned deps, insecure deserialization, unverified CI artifacts, postinstall scripts. |
| **Insider** | Abuse legitimate access | Over-broad permissions, secrets in logs/repo, missing audit, exfiltration paths. |
| **Infrastructure** | Exploit config/runtime | Permissive CORS, debug endpoints, default creds, exposed metadata, misconfigured storage. |

## Iterative discovery loop (bounded)

```
seen = {}; dry = 0; round = 0
while dry < 2 and round < Iterations:     # Iterations default 5
    round += 1
    persona = personas[(round-1) % len(personas)]
    found = scan_as(persona)              # STRIDE×OWASP pass through this lens
    new   = [f for f in found if key(f) not in seen]   # key = category + file:line + gist
    if not new: dry += 1; continue
    dry = 0; seen |= {key(f) for f in new}
    log(f"round {round} [{persona}]: +{len(new)} (total {len(seen)})")
```

- Rotate personas across rounds; once all have run at least once, revisit the persona that surfaced the most.
- **Termination is always bounded:** stop on 2 consecutive zero-new rounds (converged) or at `Iterations` (log truncation).
- Dedupe so the same finding under two personas counts once; note multi-persona findings (reachable from several angles) as higher confidence.

## Safety

All findings go through the credential-masking rules (SKILL.md → Scope & posture). PoCs are templates, never live exploits. Defensive intent only.
