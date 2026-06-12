#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

// Reads the project's .e2e/config.json (vd:web-e2e contract) so the scaffold
// inherits baseUrl/TLS posture instead of inventing its own.
function readE2eConfig(dir) {
  try {
    return JSON.parse(fs.readFileSync(path.join(dir, '.e2e', 'config.json'), 'utf8'));
  } catch {
    return null;
  }
}

function buildConfig(e2e) {
  const baseUrl = (e2e && e2e.baseUrl) || 'http://localhost:3000';
  const ignoreHttps = Boolean(e2e && e2e.insecureTLS);
  return `import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || '${baseUrl}',
    // Identity comes from the persistent profile: export once with
    // browser-profile/scripts/profile-export.sh <profile> .e2e/storageState.json
    storageState: process.env.E2E_STORAGE_STATE || '.e2e/storageState.json',${ignoreHttps ? "\n    ignoreHTTPSErrors: true," : ''}
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // Add firefox/webkit/mobile projects when cross-browser coverage earns its runtime.
  ],
  // App lifecycle is owned outside Playwright (Herd / docker compose / e2e status --wait).
});
`;
}

const EXAMPLE_TEST = `import { test, expect } from '@playwright/test';

test.describe('smoke (replays the logged-in profile identity)', () => {
  test('authenticated shell renders, not the login page', async ({ page }) => {
    await page.goto('/');
    await expect(page).not.toHaveURL(/login/);
  });
});
`;

const LOGGED_OUT_TEST = `import { test, expect } from '@playwright/test';

// For flows that must see the login page, opt out of the shared identity.
test.use({ storageState: { cookies: [], origins: [] } });

test('anonymous visit redirects to login', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/login/);
});
`;

const GITIGNORE_LINES = ['.e2e/storageState.json', 'playwright/.auth/', 'test-results/', 'playwright-report/'];

function scaffold(targetDir, log = console.log) {
  const e2e = readE2eConfig(targetDir);
  const files = {
    'playwright.config.ts': buildConfig(e2e),
    'tests/e2e/smoke.spec.ts': EXAMPLE_TEST,
    'tests/e2e/logged-out.spec.ts': LOGGED_OUT_TEST,
  };
  const created = [];
  for (const [rel, content] of Object.entries(files)) {
    const full = path.join(targetDir, rel);
    if (fs.existsSync(full)) {
      log(`skip (exists): ${rel}`);
      continue;
    }
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, content);
    created.push(rel);
    log(`created: ${rel}`);
  }

  const giPath = path.join(targetDir, '.gitignore');
  const gi = fs.existsSync(giPath) ? fs.readFileSync(giPath, 'utf8') : '';
  const missing = GITIGNORE_LINES.filter((l) => !gi.split('\n').includes(l));
  if (missing.length) {
    fs.writeFileSync(giPath, `${gi.replace(/\n*$/, '\n')}${missing.join('\n')}\n`);
    log(`gitignore: added ${missing.join(', ')}`);
  }

  log('\nnext:');
  log('  npm i -D @playwright/test && npx playwright install chromium');
  log('  "$HOME/.claude/skills/browser-profile/scripts/profile-export.sh" <profile> .e2e/storageState.json');
  log('  npx playwright test');
  return { created, usedE2eConfig: Boolean(e2e) };
}

module.exports = { readE2eConfig, buildConfig, scaffold, GITIGNORE_LINES };

if (require.main === module) {
  const args = process.argv.slice(2);
  const dirIdx = args.indexOf('--dir');
  scaffold(dirIdx !== -1 ? path.resolve(args[dirIdx + 1]) : process.cwd());
}
