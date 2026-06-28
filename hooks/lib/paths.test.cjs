'use strict';
// Run: node --test hooks/lib/paths.test.cjs
const { test } = require('node:test');
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const paths = require('./paths.cjs');

function realpath(p) {
  try { return fs.realpathSync(p); } catch { return path.resolve(p); }
}
function git(cwd, ...args) {
  execFileSync('git', args, { cwd, stdio: 'ignore' });
}

// Stray-ancestor guard: a coincidental repo rooted at $HOME must not hijack a
// nested project's umbrella. The project (a child dir below $HOME, with no git of
// its own) must anchor .workbench to itself, not to $HOME.
test('umbrella does not hijack to an ancestor repo rooted at $HOME', () => {
  const fakeHome = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-home-'));
  try {
    git(fakeHome, 'init', '-b', 'main');
    git(fakeHome, 'config', 'user.email', 't@t.t');
    git(fakeHome, 'config', 'user.name', 't');
    git(fakeHome, 'commit', '--allow-empty', '-m', 'stray home repo');
    fs.writeFileSync(path.join(fakeHome, '.vd.json'), JSON.stringify({ paths: { umbrella: '.bad' } }));

    const project = path.join(fakeHome, 'git', 'personal', 'proj');
    fs.mkdirSync(project, { recursive: true });

    // os.homedir() reads HOME/USERPROFILE; use a child so this process is untouched.
    const script =
      "const p=require(process.env.PCJS);const c=require(process.env.CCJS);" +
      "process.stdout.write(JSON.stringify({root:p.resolveUmbrellaRoot({paths:{umbrella:'.workbench'}},process.env.BASE),allowed:p.resolveUmbrellaRoot({paths:{umbrella:'.workbench',allowHomeRoot:true}},process.env.BASE),main:c.getMainWorktreeConfig(process.env.BASE)}));";
    const out = JSON.parse(execFileSync(process.execPath, ['-e', script], {
      env: {
        ...process.env,
        PCJS: require.resolve('./paths.cjs'),
        CCJS: require.resolve('./config.cjs'),
        BASE: project,
        HOME: fakeHome,
        USERPROFILE: fakeHome
      },
      encoding: 'utf8',
    }).trim());

    assert.notStrictEqual(realpath(out.root), realpath(path.join(fakeHome, '.workbench')),
      'umbrella must NOT anchor to $HOME');
    assert.strictEqual(realpath(out.root), realpath(path.join(project, '.workbench')),
      'umbrella must anchor to the project dir');
    assert.strictEqual(out.main, null, 'main worktree config must ignore a stray $HOME repo');
    assert.strictEqual(realpath(path.dirname(out.allowed)), realpath(fakeHome),
      'allowHomeRoot keeps the home repo anchor');
  } finally {
    fs.rmSync(fakeHome, { recursive: true, force: true });
  }
});

// Regression: a normal repo (git root != $HOME) is unaffected by the guard.
test('normal repo anchors umbrella to its own git root', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-repo-'));
  try {
    git(repo, 'init', '-b', 'main');
    const got = paths.resolveUmbrellaRoot({ paths: { umbrella: '.workbench' }, _gitRoot: repo }, repo);
    // Compare via the existing parent dir (git realpaths /var → /private/var; the
    // not-yet-created .workbench leaf can't be symlink-normalized directly).
    assert.strictEqual(path.basename(got), '.workbench');
    assert.strictEqual(realpath(path.dirname(got)), realpath(repo));
  } finally {
    fs.rmSync(repo, { recursive: true, force: true });
  }
});

// Regression: a brand-new project not yet `git init`'d (no git root anywhere) must
// still anchor the umbrella at the working dir — returning <cwd>/.workbench — instead
// of returning null and silently scattering artifacts to the legacy plans/ layout.
test('no git root anchors umbrella to the working dir', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-nogit-'));
  try {
    const got = paths.resolveUmbrellaRoot({ paths: { umbrella: '.workbench' } }, dir);
    assert.ok(got, 'umbrella must not be null without a git root');
    assert.strictEqual(path.basename(got), '.workbench');
    assert.strictEqual(realpath(path.dirname(got)), realpath(dir));
    // Opt-out is preserved: umbrella unset still returns null (legacy).
    assert.strictEqual(paths.resolveUmbrellaRoot({ paths: { umbrella: null } }, dir), null);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('feature-first getters use session feature state when provided', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-feature-'));
  try {
    git(repo, 'init', '-b', 'main');
    const cfg = {
      _gitRoot: repo,
      plan: { reportsDir: 'reports' },
      paths: { umbrella: '.workbench', layout: 'feature-first', plans: 'plans' }
    };
    const readState = () => ({ featureId: 'demo-feature' });
    const featureRoot = path.join(realpath(repo), '.workbench', 'features', 'demo-feature');

    assert.strictEqual(paths.getPlansPath(repo, cfg, 's1', readState), path.join(featureRoot, 'plans'));
    assert.strictEqual(
      paths.getReportsPath(null, null, cfg.plan, cfg.paths, repo, cfg, 's1', readState),
      path.join(featureRoot, 'reports')
    );
    assert.strictEqual(
      paths.getReportsPath(path.join(repo, 'plans', 'active'), 'session', cfg.plan, cfg.paths, repo, cfg, 's1', readState),
      path.join(repo, 'plans', 'active', 'reports')
    );
    const prevCwd = process.cwd();
    try {
      process.chdir(repo);
      assert.strictEqual(
        paths.getReportsPath(null, null, cfg.plan, cfg.paths, null, cfg, 's1', readState),
        `${path.join(featureRoot, 'reports').replace(/\\/g, '/')}/`
      );
    } finally {
      process.chdir(prevCwd);
    }
  } finally {
    fs.rmSync(repo, { recursive: true, force: true });
  }
});

test('read-only feature-first plan lookup does not create feature metadata', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-readonly-feature-'));
  try {
    git(repo, 'init', '-b', 'main');
    git(repo, 'checkout', '-b', 'feat/demo-work');
    const cfg = {
      _gitRoot: repo,
      plan: {
        reportsDir: 'reports',
        resolution: {
          order: ['branch'],
          branchPattern: '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)'
        }
      },
      paths: { umbrella: '.workbench', layout: 'feature-first', plans: 'plans' }
    };

    const plansDir = paths.getPlansPath(repo, cfg, 's1', () => null);

    assert.strictEqual(plansDir.endsWith(path.join('.workbench', 'features', 'demo-work', 'plans')), true);
    assert.strictEqual(
      fs.existsSync(path.join(repo, '.workbench', 'features', 'demo-work', 'feature.json')),
      false
    );

    paths.getPlansPath(repo, cfg, 's2', () => null, { readOnly: false });
    assert.strictEqual(
      fs.existsSync(path.join(repo, '.workbench', 'features', 'demo-work', 'feature.json')),
      true
    );
  } finally {
    fs.rmSync(repo, { recursive: true, force: true });
  }
});

test('isGlobalScratchPath detects only the global scratch subtree', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-scratch-path-'));
  try {
    git(repo, 'init', '-b', 'main');
    const cfg = {
      _gitRoot: repo,
      paths: { umbrella: '.workbench', layout: 'feature-first' }
    };
    const globalRoot = paths.getGlobalPath(repo, cfg);
    assert.strictEqual(
      paths.isGlobalScratchPath(path.join(globalRoot, 'scratch', 'reports'), repo, cfg),
      true
    );
    const featurePath = path.join(path.dirname(globalRoot), 'features', 'some-feature', 'reports');
    assert.strictEqual(
      paths.isGlobalScratchPath(featurePath, repo, cfg),
      false
    );
  } finally {
    fs.rmSync(repo, { recursive: true, force: true });
  }
});

test('computeFeatureId strips multi-segment ticket prefixes from slug', () => {
  assert.strictEqual(
    paths.computeFeatureId('PROJ-SUB-123', 'proj-sub-123-manual-upload'),
    'proj-sub-123-manual-upload'
  );
  assert.strictEqual(
    paths.computeFeatureId('ELT-3316', '3316-manual-upload'),
    'elt-3316-manual-upload'
  );
});

test('branch plan resolution scans the session feature plans dir', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-branch-plan-'));
  try {
    git(repo, 'init', '-b', 'main');
    git(repo, 'checkout', '-b', 'feat/demo-work');
    const cfg = {
      _gitRoot: repo,
      plan: {
        reportsDir: 'reports',
        resolution: {
          order: ['branch'],
          branchPattern: '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)'
        }
      },
      paths: { umbrella: '.workbench', layout: 'feature-first', plans: 'plans' }
    };
    const featureRoot = path.join(realpath(repo), '.workbench', 'features', 'demo-feature');
    const planDir = path.join(featureRoot, 'plans', '260620-1200-demo-work');
    fs.mkdirSync(planDir, { recursive: true });

    const resolved = paths.resolvePlanPath('s1', cfg, () => ({ featureId: 'demo-feature' }), repo);
    assert.deepStrictEqual(resolved, { path: planDir, resolvedBy: 'branch' });
  } finally {
    fs.rmSync(repo, { recursive: true, force: true });
  }
});

test('linked worktree overlays main worktree umbrella layout', () => {
  const fakeHome = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-home-'));
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-main-'));
  const linked = path.join(os.tmpdir(), `vd-linked-${process.pid}-${Date.now()}`);
  try {
    git(repo, 'init', '-b', 'main');
    git(repo, 'config', 'user.email', 't@t.t');
    git(repo, 'config', 'user.name', 't');
    git(repo, 'commit', '--allow-empty', '-m', 'init');
    git(repo, 'worktree', 'add', '-b', 'linked', linked);

    fs.writeFileSync(path.join(repo, '.vd.json'), JSON.stringify({
      paths: { umbrella: '.main-workbench', layout: 'feature-first', allowHomeRoot: true },
      plan: {
        ticketPrefixes: ['MAIN'],
        resolution: { order: ['branch'], branchPattern: 'main/(.+)' }
      }
    }));
    fs.writeFileSync(path.join(linked, '.vd.json'), JSON.stringify({
      paths: { umbrella: '.linked-workbench', layout: 'type-first', allowHomeRoot: false },
      plan: {
        ticketPrefixes: ['LINKED'],
        resolution: { order: ['session'], branchPattern: 'linked/(.+)' }
      }
    }));

    const script =
      "const c=require(process.env.CCJS);" +
      "process.chdir(process.env.BASE);" +
      "const cfg=c.loadConfig();" +
      "process.stdout.write(JSON.stringify({paths:cfg.paths,plan:cfg.plan}));";
    const got = JSON.parse(execFileSync(process.execPath, ['-e', script], {
      env: {
        ...process.env,
        CCJS: require.resolve('./config.cjs'),
        BASE: linked,
        HOME: fakeHome,
        USERPROFILE: fakeHome
      },
      encoding: 'utf8'
    }));

    assert.strictEqual(got.paths.umbrella, '.main-workbench');
    assert.strictEqual(got.paths.layout, 'feature-first');
    assert.strictEqual(got.paths.allowHomeRoot, true);
    assert.deepStrictEqual(got.plan.ticketPrefixes, ['MAIN']);
    assert.deepStrictEqual(got.plan.resolution.order, ['branch']);
    assert.strictEqual(got.plan.resolution.branchPattern, 'main/(.+)');
  } finally {
    try { git(repo, 'worktree', 'remove', '--force', linked); } catch { /* ignore */ }
    fs.rmSync(linked, { recursive: true, force: true });
    fs.rmSync(repo, { recursive: true, force: true });
    fs.rmSync(fakeHome, { recursive: true, force: true });
  }
});
