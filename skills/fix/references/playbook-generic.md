# Playbook — Generic

Use this when the issue doesn't cleanly map to data-pipeline, app-stack, or infra. Examples: shell script, build tool, repo-level config, third-party SaaS integration, an outage that crosses surfaces.

## First-look checklist

- **Restate the failure** in one sentence using the actual error text, not your interpretation.
- **What's the smallest reproducer?** Strip everything until the minimal failing command remains. The reproducer is also your verification command for Step 5.
- **What changed?** `git log --since='1 week ago'`, recent deploys, recent config edits, recent dependency bumps, recent vendor changes (status page).
- **Is it environment-specific?** Try a different shell, account, region, OS, time zone, locale.

## Fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| Script "works on my machine" | Shell / locale / env-var / PATH difference | Make the script declare its assumptions: `set -euo pipefail`, explicit `PATH`, explicit interpreter shebang, locale `LC_ALL=C` where needed. |
| Tool ignores a flag silently | Flag in wrong position / tool version too old | Check `--help` output of the installed binary; pin version in CI. |
| External API call fails | Auth expired / rate limit / vendor outage | Check vendor status page BEFORE assuming code bug. Then auth, then code. |
| Build artifacts inconsistent across machines | Non-deterministic input (timestamp, hostname) | Make build reproducible: pin deps, freeze timestamps, sort deterministically. |
| Cron / scheduled job missed | Time zone / overlap / lock contention | Confirm scheduler's effective TZ; add a singleflight lock if overlap matters. |
| Repo-level lint/format/CI works locally, not in CI | Tool version mismatch | Pin the tool version in repo config; run via `mise` / `asdf` / similar. |

## When you can't categorize the failure

That's a signal the diagnosis isn't deep enough. Go back to Step 2 (`/vd:debug`) with sharper questions:
- What's the *exact* sequence of events leading to the failure?
- What's the *first* place the system's state diverges from expected?
- What's a smaller, faster reproducer?

Avoid spending more than a couple of attempts in "generic" — most real failures map to a surface once the diagnosis is sharp enough.

## Done criteria (generic)

- [ ] Minimal reproducer captured; it triggers the failure deterministically.
- [ ] Root cause stated in one sentence with evidence.
- [ ] Fix is the minimal change to address that cause.
- [ ] Reproducer reran post-fix; clean output captured.
- [ ] Regression guard: a check (test, lint rule, CI step, monitor) that would have caught this earlier.
