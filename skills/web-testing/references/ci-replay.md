# CI replay — running the suite unattended

## Identity in CI

`storageState.json` contains live session cookies. Treat it like a password:

- Store base64 of a freshly exported state as a CI secret (`E2E_STORAGE_STATE_B64`), decode in the job, point `E2E_STORAGE_STATE` at the file. Rotate when the underlying session rotates.
- Apps with short-lived JWTs (hours) can't use a static secret — log in via API in the job instead and write the state programmatically:

```ts
// global-setup.ts: API login → storageState, no UI needed
const ctx = await request.newContext({ baseURL });
await ctx.post('/api/v1/auth/login', { data: { email, password } });   // seeded CI user
await ctx.storageState({ path: '.e2e/storageState.json' });
```

## GitHub Actions shape

```yaml
e2e:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: 22 }
    - run: docker compose up -d --build          # or the app's boot command
    - run: npm ci && npx playwright install --with-deps chromium
    - run: until curl -fsS http://localhost:8000/api/v1/readyz; do sleep 2; done
      timeout-minutes: 3
    - run: echo "$E2E_STORAGE_STATE_B64" | base64 -d > .e2e/storageState.json
      env: { E2E_STORAGE_STATE_B64: ${{ secrets.E2E_STORAGE_STATE_B64 }} }
    - run: npx playwright test
    - run: node analyze-test-results.cjs --playwright test-results/results.json --output markdown >> "$GITHUB_STEP_SUMMARY"
      if: always()
    - uses: actions/upload-artifact@v4
      if: failure()
      with: { name: playwright-report, path: playwright-report/ }
```

## Sharding

Past ~5 minutes of wall-clock, shard: `npx playwright test --shard=${{ matrix.shard }}/4` with a 4-way matrix, then merge reports with `npx playwright merge-reports`. Don't shard before it hurts — matrix startup costs real minutes too.

## Rules of thumb

- Gate on the app's readiness endpoint, never `sleep`.
- `retries: 2` in CI only — local retries hide flakiness instead of fixing it (see test-flakiness-mitigation.md).
- Upload the HTML report only on failure; green-run artifacts are noise.
