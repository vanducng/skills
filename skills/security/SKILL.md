---
name: security
description: "Threat-modeled security audit using STRIDE + OWASP, scanning code from multiple attacker perspectives, with optional red-team discovery loop and an autoresearch-style fix loop. Use for defensive security review, vulnerability discovery, threat modeling, and authorized remediation. Triggers: 'security audit', 'STRIDE', 'OWASP', 'find vulnerabilities', 'threat model', 'red-team this', 'is this secure'."
license: MIT
argument-hint: "<scope glob or 'full'> [--fix] [--red-team] [--iterations N]"
metadata:
  author: vanducng
  attribution: "Threat-model + fix-loop pattern from autoresearch by Udit Goenka (MIT)"
  version: "0.1.0"
---

# security

> STRIDE + OWASP, from multiple attacker perspectives → severity-ranked findings, optionally auto-fixed.

## Scope & posture

**Defensive / authorized use only.** Run against code you own or are authorized to audit. This skill performs review and authorized remediation; it does **not** produce weaponized exploits, mass-targeting tooling, or detection-evasion for malicious use.

**Credential masking is mandatory** — even when the secret *is* the finding. Mask per the table in `vd:optimize-loop`'s SKILL.md (API keys → `<REDACTED_TOKEN>`, connection strings → `…:<REDACTED_PASSWORD>@…`, env values → reference the name). No report or PoC may contain a live secret or a copy-paste-ready exploit with real credentials — write PoCs as templates the user fills in.

## What this is — and isn't

This is an LLM-driven threat-modeled review + bounded fix loop — **not** a replacement for a SAST scanner, dependency CVE database, or pentest engagement. Use it to reason about *this codebase's* threat surface and remediate findings; pair with real scanners for breadth.

## Modes

| Mode | Behaviour |
|---|---|
| _(default)_ | One-shot scan: STRIDE + OWASP pass over `<scope>` → severity-ranked findings report. |
| `--red-team` | Iterative persona-driven discovery loop — see [`references/red-team-personas.md`](references/red-team-personas.md). |
| `--fix` | Remediate findings using the autoresearch loop (below). |

## Workflow

1. **Scope** — resolve `<scope>` glob (or `full` = whole repo). List the files/surfaces in play.
2. **Threat pass** — walk STRIDE × OWASP per [`references/stride-owasp.md`](references/stride-owasp.md): for each category, grep/inspect the relevant sinks.
3. **Categorize** — each finding: title, STRIDE category, OWASP ref, **severity** (Critical/High/Med/Low), location (`file:line`), masked PoC, remediation.
4. **`--red-team`** (optional) — run attacker personas iteratively; dedupe vs seen; stop on a dry round or `--iterations` cap (default 5). Bounded.
5. **`--fix`** (optional) — see Fix loop.
6. **Report** → `plans/reports/security-{date}-{slug}.md`.
   Final handoff must include an openable report location, such as
   `[security-report.md](/absolute/path/to/security-report.md)` or
   `file:///absolute/path/to/security-report.md`, not just the basename.

## Fix loop (`--fix`)

Reuses the `vd:optimize-loop` discipline (see [`../optimize-loop/references/loop-protocol.md`](../optimize-loop/references/loop-protocol.md)) — do not duplicate it:

- **One finding per iteration.** Atomic change.
- **Commit before verify** (`loop(iter-N): fix <finding-id>`).
- **Verify** = the specific finding no longer reproduces (its detection check now passes).
- **Guard** = the project's test suite (do not regress behavior). Guard files are read-only.
- **Keep** if verify passes and guard holds; else `git revert` and try a different remediation (max 2 reworks), then defer the finding to the report.

## Output shape

```markdown
### [Critical] SQL injection in users query — STRIDE: Tampering · OWASP: A03 Injection
- Location: src/db/users.ts:42
- PoC (masked): GET /users?id=1';DROP… (param reaches string-concatenated query)
- Remediation: use parameterized query / prepared statement.
- Fix status: applied (loop iter-3) | deferred
```

End with: `Findings: C/H/M/L counts · personas run: N · fixes applied: K`.

## Limitations (honest)

- Reasoning-based — can miss what a dedicated SAST/CVE scanner catches; pair with those for breadth.
- `--red-team` and `--fix` are bounded by `--iterations`; logs when a cap truncates discovery.
- Cannot assess runtime/infra config it can't see (secrets managers, WAF rules, network policy).
