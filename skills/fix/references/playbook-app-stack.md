# Playbook — App stack (backend + frontend)

Load this when the failure is in a backend service, API, deploy, DB migration, or frontend UI/build/runtime.

## First-look checklist

- **Where does the error originate?** Read the stack trace from bottom (root frame) up, not top. The top frame is usually generic framework code.
- **Reproducible locally?** If not, what's different between local and the failing env (env vars, DB version, feature flags, traffic shape)?
- **Recent changes?** `git log --since='3 days ago' -- <touched path>`; check related deploy events and migration history.
- **Env parity?** Compare env vars / secrets / config between working and failing envs. Mismatched config is the #1 cause of "works locally, fails in prod".

## Backend — fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| 5xx on a specific endpoint | Unhandled error path / null deref / failed dep call | Add typed error at the boundary; return correct status; cover with a test that hits the bad path. |
| 5xx everywhere after deploy | Bad config / missing migration / version mismatch | Roll back first if traffic is impacted, then fix forward. Never debug in prod while users are erroring. |
| Migration fails to apply | Forward migration assumes a state that doesn't exist in env | Write a **new** corrective migration; never edit an applied migration. |
| Connection pool exhausted | Slow query / leaked connection / N+1 | Find the offending query (APM / `pg_stat_activity`); fix at source. Raising the pool size masks the leak. |
| Auth failures | Clock skew / wrong key / rotated secret | Verify key rotation completed across all replicas before declaring fixed. |
| Intermittent 502 from load balancer | Pod crashing under load / readiness probe wrong | Check `kubectl get events`, `--previous` logs. See infra playbook. |
| Slow endpoint regression | New N+1 / missing index / chatty downstream | Profile; fix at source (eager-load / batch / cache key). Don't paper over with timeout bump. |

**Backend verification:**
```
<run failing test>          # unit/integration, exact -k filter from Step 2
curl -i ...                 # reproduce the failing request, capture before/after
<rerun migration in lower env>
```

## Frontend — fix patterns

| Symptom | Likely cause | Fix shape |
|---|---|---|
| Hydration mismatch | Server and client render different DOM | Find the divergent data source (Date.now, random, locale, window). Make server and client agree, or move to client-only render. |
| White screen / chunk load error | Stale CDN / missing dependency / SSR error | Check browser console + network tab. For SSR errors, check server logs. |
| Build fails | Type error / missing peer dep / config change | Run `tsc --noEmit` / `vue-tsc` / framework's typecheck. Fix at the type, not via `any`/`@ts-ignore`. |
| UI looks wrong only in one browser | CSS feature support / layout engine | Verify in DevTools target browser; pick a portable CSS path, don't ship vendor hacks. |
| State doesn't update | Stale closure / wrong dep array / store not subscribed | Trace the data flow; fix the dep array or store subscription. Don't `forceUpdate`. |
| Form submit double-fires | Missing disabled state / no debounce | Disable on submit + server-side idempotency key. Both. |
| 404 on a route after deploy | Stale router config / missing static asset / build output mismatch | Reproduce after hard refresh + cleared cache. Confirm the asset exists in the deployed bundle. |

**Frontend verification:**
- Hard reload from a clean state (incognito or cleared cache).
- Reproduce the original failing flow end-to-end.
- Screenshot before/after if visual.
- For UI fixes, use Chrome MCP / `vd:web-e2e` to verify in a real browser, not just unit tests.
- Run the e2e suite if one exists for the affected flow.

## Cross-cutting

- **Logging & tracing:** confirm the fix surfaces in logs/traces correctly (success path emits expected event). A silent fix is hard to monitor.
- **Feature flags:** if the fix is gated, verify behavior with the flag both off and on, not just one side.
- **Rollback path:** state the rollback in the commit if the fix is risky (revert SHA, migration down step if reversible, flag flip).

## Done criteria (app-stack-specific)

- [ ] Failing request/test reran; before/after captured.
- [ ] Stack trace pointer at root frame, not symptom.
- [ ] Test added that covers the broken path (unit + integration if user-reachable).
- [ ] Migration: new forward migration, not edited history.
- [ ] Env parity confirmed (vars/secrets in target env).
- [ ] Frontend: visually verified in a real browser, not only unit tests.
- [ ] Rollback path documented if risky.
