# Web Testing Reference

Use this reference for test strategy, Vitest, Testing Library, Playwright, accessibility testing, visual regression, performance checks, cross-browser validation, load testing, and release readiness.

## Strategy

Pick the smallest test that proves the behavior:

- **Unit:** pure functions, formatters, reducers, validation helpers, permission checks.
- **Component/integration:** user-visible component behavior, form flows, table controls, router state, mocked network.
- **E2E:** critical paths across routing, real browser behavior, auth, server integration, file upload, payments, or permissions.
- **Contract/API:** frontend/backend schema and endpoint assumptions.
- **Visual:** layout and appearance where regressions are costly.
- **Accessibility:** automated scan plus manual keyboard checks.
- **Performance:** Core Web Vitals, bundle, render cost, API latency.

Do not pyramid-dogmatize. Modern SPAs usually need a trophy shape: strong integration/component tests, a few unit tests, and focused E2E on critical flows.

## Testing Library

Testing Library's principle is to test in ways that resemble user interaction.

Prefer:

- `getByRole` with accessible name.
- `userEvent` over low-level event firing.
- Assertions on visible output and ARIA state.
- Tests that survive refactors.

Avoid:

- Querying private class names or implementation details.
- Asserting internal component state.
- Snapshotting large DOM trees.
- Mocking every child until the test no longer resembles the app.

Source: https://testing-library.com/docs/

## Vitest

Use Vitest for fast unit and component tests in Vite/React projects:

```bash
npx vitest run
npx vitest --ui
npx vitest run --coverage
```

Checklist:

- Put shared setup in `setupTests.ts`.
- Use fake timers only when needed and restore them.
- Mock network at the boundary (`msw`, fetch mock, or app service seams).
- Keep tests deterministic; no real time, random IDs, or shared mutable fixtures without reset.
- Cover loading, success, empty, error, and permission branches.

## Playwright

Use Playwright for browser truth:

```bash
npx playwright test
npx playwright test --ui
npx playwright test --debug
npx playwright show-report
```

Rules:

- Use role/text/test-id locators, not brittle CSS paths.
- Prefer web-first assertions (`toBeVisible`, `toHaveURL`) over sleeps.
- Store auth state only when it does not hide the flow under test.
- Isolate data per test or reset fixtures.
- Record traces on retry in CI.
- Test responsive behavior with named projects for desktop/mobile.

## Accessibility Testing

Playwright can catch issues such as low contrast, unlabeled controls, and duplicate IDs when paired with an accessibility scanner. It is not a substitute for manual checks.

Minimum:

- Automated scan for changed pages.
- Keyboard-only path through primary flow.
- Visible focus and focus not obscured by sticky UI.
- Screen-reader-oriented check of names, labels, headings, landmarks, and live regions.
- Reduced motion path.
- Color-not-only check.

Source: https://playwright.dev/docs/accessibility-testing

## Visual Regression

Use visual tests when layout/appearance is a contract:

```ts
import { test, expect } from '@playwright/test'

test('dashboard layout', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveScreenshot()
})
```

Rules:

- Stabilize data, time, animations, fonts, and network.
- Mask dynamic areas.
- Capture desktop and mobile if responsive layout matters.
- Keep baselines reviewed and intentional.
- Do not use broad full-page screenshots for volatile apps unless the team accepts the maintenance cost.

Source: https://playwright.dev/docs/test-snapshots

## Performance And Core Web Vitals

Core Web Vitals stable metrics are:

- **LCP:** loading performance.
- **CLS:** visual stability.
- **INP:** interaction responsiveness.

Measure at the 75th percentile across mobile and desktop when real-user data exists.

Practical checks:

- Hero/LCP image optimized, sized, and prioritized.
- Images/videos have dimensions or `aspect-ratio`.
- Fonts use `font-display` and do not create major layout shift.
- Heavy components are route-split or lazy-loaded.
- Long tasks are reduced; expensive filtering/sorting is debounced, memoized, moved server-side, or virtualized.
- Third-party scripts are deferred, async, or removed.

Source: https://web.dev/articles/vitals

## Cross-Browser And Responsive

At minimum for meaningful UI changes:

- Chromium desktop.
- Mobile viewport emulation.
- Safari/WebKit when CSS, media, touch, or forms are risky.
- Firefox when layout, focus, or browser APIs are risky.

Check:

- No horizontal scroll.
- Focus and hover/active/disabled states.
- Sticky elements and safe areas.
- Dialogs, popovers, menus, and scroll locking.
- File inputs, date/time inputs, and mobile keyboards.

## CI

Recommended order:

```yaml
- run: npm run typecheck
- run: npm run lint
- run: npm run test
- run: npx playwright test
```

Use sharding only when suites are slow enough to justify CI complexity. Keep E2E artifacts: traces, videos on failure, screenshots, and HTML reports.

## Flakiness

Common causes:

- Fixed sleeps instead of readiness assertions.
- Shared test data.
- Animation or time-dependent UI.
- Race between navigation and network.
- Hidden retries in app or test runner.
- Third-party network calls.

Fix by waiting for user-visible readiness, isolating fixtures, controlling time, mocking external services, and using traces to prove the real wait condition.

## Release Checklist

Before shipping a web UI:

- Typecheck/lint/tests pass.
- Primary path works in a browser.
- Error, empty, loading, and permission states checked.
- Keyboard path checked.
- Responsive widths checked.
- No console errors.
- No obvious Core Web Vitals regression.
- Visual snapshots updated intentionally if used.
