# STRIDE × OWASP

Walk each STRIDE category; for each, inspect the listed sinks and map findings to the OWASP Top-10 reference.

## STRIDE categories

| STRIDE | Threat | Inspect for |
|---|---|---|
| **S**poofing | Identity forgery | Weak/absent auth, missing token verification, predictable session IDs, trusting client-supplied identity. |
| **T**ampering | Unauthorized modification | Missing input validation, mutable shared state, unsigned data, mass-assignment, path traversal. |
| **R**epudiation | Deniable actions | Missing/weak audit logs, log injection, no integrity on audit trail. |
| **I**nfo disclosure | Data leakage | Verbose errors/stack traces, secrets in logs/responses, directory listing, IDOR, over-broad serialization. |
| **D**enial of service | Availability | Unbounded loops/allocations, no rate limit, ReDoS, zip bombs, N+1, missing timeouts. |
| **E**levation of privilege | Gaining rights | Missing authz checks, role confusion, insecure deserialization, SSRF→metadata, command/SQL injection. |

## OWASP Top-10 (2021) quick map

| Ref | Category | Common sinks to grep |
|---|---|---|
| A01 | Broken access control | route handlers without authz middleware; object access by user-supplied id (IDOR); `../` path use. |
| A02 | Cryptographic failures | MD5/SHA1 for passwords, hardcoded keys, `http://`, missing TLS, weak random (`Math.random` for tokens). |
| A03 | Injection | string-concatenated SQL, `exec`/`eval`/`child_process` with user input, unescaped template/HTML. |
| A04 | Insecure design | missing rate limits, no lockout, trust boundaries crossed without checks. |
| A05 | Security misconfiguration | debug=true in prod, default creds, permissive CORS (`*` + credentials), open S3/bucket. |
| A06 | Vulnerable components | pinned-old deps, known-CVE versions (cross-check `npm/pip audit`). |
| A07 | Auth failures | weak password policy, no MFA path, session fixation, JWT `alg:none`, missing expiry. |
| A08 | Integrity failures | insecure deserialization, unsigned updates, CI/CD pulling unverified artifacts. |
| A09 | Logging/monitoring failures | no audit on auth events, secrets in logs, no alerting hook. |
| A10 | SSRF | server-side fetch of user-supplied URL without allow-list; cloud metadata reachable. |

### SSRF — beyond a naïve host check

A string allow-list on the URL is not enough. Verify the fetcher: resolves **all** DNS answers and rejects any non-unicast address (loopback, link-local `169.254.0.0/16` incl. cloud metadata `169.254.169.254`, RFC-1918, `::1`, `fc00::/7`); **forbids redirects** (or re-validates each hop — a 302 to the metadata IP defeats a one-time check); and is not vulnerable to **DNS rebinding** (re-resolve at connect time, or pin the validated IP for the actual socket). Flag any user-controlled URL passed to `fetch`/`requests`/`http.get`/`curl`/webhook senders without all four.

### Secrets — remediation order

A committed secret is **compromised the instant it reaches a remote** (push, PR, CI log, mirror), even if later force-pushed away — assume it's harvested. Remediation order is **revoke & reissue first**, then purge history (`git filter-repo`/BFG), then add a pre-commit/gitleaks gate. "Rotate later" is wrong; the credential is live in someone's scraper now.

## Severity rubric

| Severity | Bar |
|---|---|
| Critical | Remote unauth code exec / data breach / privilege escalation, trivially reachable. |
| High | Exploitable with auth or some friction; significant data/integrity impact. |
| Medium | Requires unlikely preconditions, or limited impact. |
| Low | Defense-in-depth / hardening; no direct exploit path. |

Findings reachable by combining two categories (e.g. IDOR + missing rate limit) escalate one level — note the chain.
