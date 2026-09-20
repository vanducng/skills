---
name: security
description: "Threat-modeled security audit using STRIDE + OWASP (incl. OWASP LLM Top-10), Cloudflare-style evidence bar (confirmed / needs_validation / rejected), optional red-team discovery, adversarial verify, and an autoresearch-style fix loop. Use for defensive security review, vulnerability discovery, threat modeling, prompt-injection / LLM / MCP security, multi-tenant isolation, and authorized remediation. Triggers: 'security audit', 'STRIDE', 'OWASP', 'find vulnerabilities', 'threat model', 'red-team this', 'is this secure', 'prompt injection', 'LLM security', 'pen-test the code'."
license: MIT
argument-hint: "<scope glob or 'full'> [--fix] [--red-team] [--verify] [--iterations N]"
metadata:
  author: vanducng
  attribution: "Threat-model + fix-loop pattern from autoresearch by Udit Goenka (MIT); evidence bar + attack-class companions distilled from Cloudflare security-audit-skill (MIT)"
  version: "0.2.0"
---

# security

> STRIDE + OWASP from multiple attacker perspectives → evidence-gated findings, optionally auto-fixed.

## Scope & posture

**Defensive / authorized use only.** Run against code you own or are authorized to audit. This skill performs review and authorized remediation; it does **not** produce weaponized exploits, mass-targeting tooling, or detection-evasion for malicious use.

**Credential masking is mandatory** - even when the secret *is* the finding. Mask per the table in `vd:optimize-loop`'s SKILL.md (API keys → `<REDACTED_TOKEN>`, connection strings → `…:<REDACTED_PASSWORD>@…`, env values → reference the name). No report or PoC may contain a live secret or a copy-paste-ready exploit with real credentials - write PoCs as templates the user fills in.

Do not probe deployed / shared / production endpoints. Prefer source review and local dummy fixtures. If a decisive fact lives only in deployment config you cannot see, use `needs_validation` - do not guess.

## What this is - and isn't

This is an LLM-driven threat-modeled review + bounded fix loop - **not** a replacement for a SAST scanner, dependency CVE database, or pentest engagement. Use it to reason about *this codebase's* threat surface and remediate findings; pair with real scanners for breadth.

For Cloudflare's full six-phase multi-agent harness (coverage ledger, schema validators, independent record verification at fleet scale), install their skill separately: `npx skills add https://github.com/cloudflare/security-audit-skill --skill security-audit`. This skill keeps the daily-driver path and our `--fix` loop.

## Evidence bar (required)

A candidate is a security finding only when you can name:

1. **Lower-trust principal** (who starts)
2. **Accepted input / action** they control
3. **Intended control** that should stop them
4. **Crossed boundary** in source
5. **Affected principal or resource** and a **concrete result**

| Verdict | Meaning | Severity? |
|---|---|---|
| `confirmed` | Source trace + bounded evidence establish the boundary failure and result | Yes |
| `needs_validation` | Source-grounded hypothesis blocked by an exact missing fact (deploy/provider/runtime); state the blocker and a safe owner check | No |
| `rejected` | Disproved during review/verify; keep briefly so you do not re-report | No |
| hardening note | Defense-in-depth gap while Layer A already blocks the attack | No (not a finding) |

**Anti-patterns:** checklist deviations as vulns; defense-in-depth advice with no reachable boundary failure; guessing proxy/WAF/IdP behavior absent from source; treating intended same-principal self-impact as cross-boundary; assigning severity to `needs_validation`.

## Modes

| Mode | Behaviour |
|---|---|
| _(default / guidance)_ | Security questions and focused reviews: use relevant references only; do not invent a full report unless asked. |
| _(full audit)_ | Explicit audit / pen-test / "full review" / requested report: run the workflow below and write the report. |
| `--red-team` | Iterative persona-driven discovery - see [`references/red-team-personas.md`](references/red-team-personas.md). |
| `--verify` | After hunting, adversarially try to refute every High+ candidate before it stays `confirmed`. |
| `--fix` | Remediate `confirmed` findings using the autoresearch loop (below). |

If the request could be guidance or full audit, ask one focused question before writing report files.

## Workflow

1. **Scope** - resolve `<scope>` glob (or `full` = whole repo). List surfaces / trust boundaries in play.
2. **Threat pass** - walk STRIDE × OWASP per [`references/stride-owasp.md`](references/stride-owasp.md). Layer attack classes from [`references/attack-classes.md`](references/attack-classes.md). If multi-tenant / export / backup / delete / restore are in scope, also [`references/data-isolation.md`](references/data-isolation.md). If the scope calls an LLM, agent, MCP, or builds prompts from untrusted data, also [`references/llm-owasp.md`](references/llm-owasp.md).
3. **Categorize** - each item: verdict, title, STRIDE, OWASP (or LLM) ref, location (`file:line`), masked PoC / source trace, remediation. Severity only on `confirmed`.
4. **`--red-team`** (optional) - personas iteratively; dedupe; stop on dry rounds or `--iterations` (default 5).
5. **`--verify`** (optional) - for each High+ `confirmed` candidate, a fresh pass tries to refute it from source (and local fixtures if available). Promote to `needs_validation` or `rejected` when the claim fails; never keep severity on a shaky claim.
6. **`--fix`** (optional) - see Fix loop. Only remediates `confirmed`.
7. **Report** - write to the injected `Reports:` path. Filename: `security-{date}-{slug}.md`.
   Final handoff must include an openable report location, such as
   `[security-report.md](/absolute/path/to/security-report.md)` or
   `file:///absolute/path/to/security-report.md`, not just the basename.

## Fix loop (`--fix`)

Reuses the `vd:optimize-loop` discipline (see [`../optimize-loop/references/loop-protocol.md`](../optimize-loop/references/loop-protocol.md)) - do not duplicate it:

- **One finding per iteration.** Atomic change. Prefer the smallest source fix at the last trusted decision point.
- **Commit before verify** (`loop(iter-N): fix <finding-id>`).
- **Verify** = the specific finding no longer reproduces (its detection check now passes).
- **Guard** = the project's test suite (do not regress behavior). Guard files are read-only.
- **Keep** if verify passes and guard holds; else `git revert` and try a different remediation (max 2 reworks), then defer the finding to the report.

## Output shape

```markdown
### [confirmed · Critical] SQL injection in users query - STRIDE: Tampering · OWASP: A05
- Location: src/db/users.ts:42
- Boundary: unauth caller → string-concat query → other users' rows
- PoC (masked): GET /users?id=1';DROP… (param reaches concatenated query)
- Remediation: parameterized query / prepared statement.
- Fix status: applied (loop iter-3) | deferred | n/a

### [needs_validation] Cross-tenant cache key - missing CDN ACL fact
- Blocker: whether edge cache key includes tenant (not in repo)
- Owner check: inspect cache key policy / purge behavior in <env>
```

End with: `Verdicts: confirmed C/H/M/L · needs_validation N · rejected R · hardening H · personas: P · verifies: V · fixes: K`.

## Limitations (honest)

- Reasoning-based - can miss what a dedicated SAST/CVE scanner catches; pair with those for breadth.
- `--red-team`, `--verify`, and `--fix` are bounded by `--iterations`; log when a cap truncates work.
- Cannot assess runtime/infra config it can't see (secrets managers, WAF rules, network policy) - use `needs_validation`.
- Confirming via executing target code needs an OS-enforced sandbox (no external net, allowlisted env, resource limits). Without it, keep the lead at `needs_validation` instead of claiming local exploit confirmation.
