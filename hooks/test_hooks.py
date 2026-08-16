#!/usr/bin/env python3
"""Behavioral tests for the .py hook scripts.

Ports the 18 auxiliary-hook cases from vd-cli hook-tests.mjs plus the
session-init / subagent-init scenarios from vd-cli parity.mjs. Invokes the
.py hooks as subprocesses with synthetic stdin, temp HOME, and temp git repos;
asserts on stdout / exit codes / env-file contents.

Machine-specific values (user, locale, timezone, runtime version, os platform)
are value-masked the way parity.mjs masks them, so presence/position/format stay
asserted while the volatile value differs.

Delta from the .cjs contract: session-init emits VD_RUNTIME_VERSION
("python/<version>") in place of VD_NODE_VERSION — same env-write slot.

Run: python3 -m unittest hooks.test_hooks
 or: python3 hooks/test_hooks.py
"""

import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))

SESSION_INIT = os.path.join(HOOKS_DIR, 'session-init.py')
SUBAGENT_INIT = os.path.join(HOOKS_DIR, 'subagent-init.py')
STATUSLINE = os.path.join(HOOKS_DIR, 'statusline.py')
SCOUT_BLOCK = os.path.join(HOOKS_DIR, 'scout-block.py')
HERDR_PANE_NAME = os.path.join(HOOKS_DIR, 'herdr-pane-name.py')
TEAM_INJECT = os.path.join(HOOKS_DIR, 'team-context-inject.py')
TASK_COMPLETED = os.path.join(HOOKS_DIR, 'task-completed-handler.py')
TEAMMATE_IDLE = os.path.join(HOOKS_DIR, 'teammate-idle-handler.py')

FIXED_SESSION_ID = '00000000-0000-0000-0000-000000000001'
REAL_HOME = pwd.getpwuid(os.getuid()).pw_dir  # immune to HOME env changes


def run_raw(script, stdin_str, extra_env=None, cwd=None, timeout=30):
    env = dict(os.environ)
    env['NO_COLOR'] = '1'
    if extra_env:
        env.update(extra_env)
    r = subprocess.run([sys.executable, script], input=stdin_str, env=env, cwd=cwd,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout or '', r.stderr or ''


def run_json(script, payload, extra_env=None, cwd=None, timeout=30):
    return run_raw(script, json.dumps(payload), extra_env, cwd, timeout)


def git(cwd, *args):
    subprocess.run(['git'] + list(args), cwd=cwd,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def parse_env_map(content):
    m = {}
    for line in content.split('\n'):
        hit = re.match(r'^export ([A-Z_]+)="(.*)"$', line)
        if hit:
            m[hit.group(1)] = hit.group(2)
    return m


# ── config fixtures (from parity.mjs) ──────────────────────────────────────

DEFAULT_VD_CONFIG = {
    'plan': {
        'namingFormat': '{date}-{issue}-{slug}',
        'dateFormat': 'YYMMDD-HHmm',
        'issuePrefix': None,
        'reportsDir': 'reports',
        'resolution': {'order': ['session', 'branch'],
                       'branchPattern': '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)'},
        'validation': {'mode': 'prompt', 'minQuestions': 3, 'maxQuestions': 8,
                       'focusAreas': ['assumptions', 'risks', 'tradeoffs', 'architecture']},
    },
    'paths': {'docs': 'docs', 'plans': 'plans'},
}

CUSTOM_VD_CONFIG = {
    'plan': {
        'namingFormat': '{date}-{issue}-{slug}',
        'dateFormat': 'YYMMDD-HHmm',
        'issuePrefix': 'GH-',
        'reportsDir': 'my-reports',
        'resolution': {'order': ['session', 'branch'],
                       'branchPattern': '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)'},
        'validation': {'mode': 'prompt', 'minQuestions': 3, 'maxQuestions': 8,
                       'focusAreas': ['assumptions', 'risks', 'tradeoffs', 'architecture']},
    },
    'paths': {'docs': 'docs', 'plans': 'plans'},
}


# ── golden templates (session-init.env with the VD_RUNTIME_VERSION delta) ──

DEFAULT_ENV_GOLDEN = '\n'.join([
    'export VD_SESSION_ID="{{SESSION_ID}}"',
    'export VD_PLAN_NAMING_FORMAT="{date}-{issue}-{slug}"',
    'export VD_PLAN_DATE_FORMAT="YYMMDD-HHmm"',
    'export VD_PLAN_ISSUE_PREFIX=""',
    'export VD_PLAN_REPORTS_DIR="reports"',
    'export VD_NAME_PATTERN="{{DATE}}-{{TIME}}-{slug}"',
    'export VD_ACTIVE_PLAN=""',
    'export VD_SUGGESTED_PLAN=""',
    'export VD_GIT_ROOT="{{GIT_ROOT}}"',
    'export VD_REPORTS_PATH="{{REPORTS_ABS}}/"',
    'export VD_DOCS_PATH="{{DOCS_ABS}}"',
    'export VD_PLANS_PATH="{{PLANS_ABS}}"',
    'export VD_PROJECT_ROOT="{{GIT_ROOT}}"',
    'export VD_PROJECT_TYPE="single-repo"',
    'export VD_PACKAGE_MANAGER=""',
    'export VD_FRAMEWORK=""',
    'export VD_RUNTIME_VERSION="{{RUNTIME_VERSION}}"',
    'export VD_OS_PLATFORM="{{OS_PLATFORM}}"',
    'export VD_GIT_BRANCH="main"',
    'export VD_USER="{{USER}}"',
    'export VD_LOCALE="{{LOCALE}}"',
    'export VD_TIMEZONE="{{TIMEZONE}}"',
    'export VD_CLAUDE_SETTINGS_DIR="{{HOME}}/.claude"',
    'export VD_VALIDATION_MODE="prompt"',
    'export VD_VALIDATION_MIN_QUESTIONS="3"',
    'export VD_VALIDATION_MAX_QUESTIONS="8"',
    'export VD_VALIDATION_FOCUS_AREAS="assumptions,risks,tradeoffs,architecture"',
    'export VD_CODING_LEVEL="-1"',
    'export VD_CODING_LEVEL_STYLE="coding-level-5-god"',
])

CUSTOM_ENV_GOLDEN = (DEFAULT_ENV_GOLDEN
                     .replace('export VD_PLAN_ISSUE_PREFIX=""', 'export VD_PLAN_ISSUE_PREFIX="GH-"')
                     .replace('export VD_PLAN_REPORTS_DIR="reports"', 'export VD_PLAN_REPORTS_DIR="my-reports"')
                     .replace('export VD_REPORTS_PATH="{{REPORTS_ABS}}/"',
                              'export VD_REPORTS_PATH="{{CUSTOM_REPORTS_ABS}}/"'))

# subagent-init default context (current contract; matches the .cjs line order).
SUBAGENT_CONTEXT_GOLDEN = '\n'.join([
    '## Subagent: fullstack-developer',
    'ID: aaaaaaaa-test-0001 | CWD: {{GIT_ROOT}}',
    '',
    '## Context',
    '- Plan: none',
    '- Reports: {{REPORTS_ABS}}',
    '- Paths: {{PLANS_ABS}}/ | {{DOCS_ABS}}/',
    '',
    '## Rules',
    '- Reports → {{REPORTS_ABS}}',
    '- YAGNI / KISS / DRY',
    '- Before PR merge/next ship step: fetch review comments, validate, fix valid ones, reply/resolve, re-check',
    '- Concise, list unresolved Qs at end',
    '- Python scripts in .claude/skills/: Use `~/.claude/skills/.venv/bin/python3`',
    '- Never use global pip install',
    '',
    '## Naming',
    '- Report: {{REPORTS_ABS}}/fullstack-developer-{{DATE}}-{{TIME}}-{slug}.md',
    '- Plan dir: {{PLANS_ABS}}/{{DATE}}-{{TIME}}-{slug}/',
    '',
    '## Plan Status Updates',
    'Edit the plan.md Status column directly: `Pending` → `In Progress` → `Completed`.',
])


def mask(content, repo, fake_home, custom_reports_dir=None):
    """Value-mask volatile/machine tokens (mirrors parity.mjs mask()).

    OS platform is also value-masked (parity hardcodes darwin) so the golden
    comparison is portable across hosts.
    """
    if custom_reports_dir:
        reports_path = os.path.join(repo, 'plans', custom_reports_dir)
        out = content.replace(reports_path, '{{CUSTOM_REPORTS_ABS}}')
    else:
        reports_path = os.path.join(repo, 'plans', 'reports')
        out = content.replace(reports_path, '{{REPORTS_ABS}}')

    out = out.replace(os.path.join(repo, 'plans'), '{{PLANS_ABS}}')
    out = out.replace(os.path.join(repo, 'docs'), '{{DOCS_ABS}}')
    out = out.replace(repo, '{{GIT_ROOT}}')
    out = out.replace(REAL_HOME, '{{HOME}}')
    out = out.replace(fake_home, '{{FAKE_HOME}}')
    out = out.replace(FIXED_SESSION_ID, '{{SESSION_ID}}')
    out = re.sub(r'\b\d{6}-\d{4}\b', '{{DATE}}-{{TIME}}', out)

    out = re.sub(r'(VD_USER=")[^"]*(")', r'\1{{USER}}\2', out)
    out = re.sub(r'(VD_LOCALE=")[^"]*(")', r'\1{{LOCALE}}\2', out)
    out = re.sub(r'(VD_TIMEZONE=")[^"]*(")', r'\1{{TIMEZONE}}\2', out)
    out = re.sub(r'(VD_RUNTIME_VERSION=")[^"]*(")', r'\1{{RUNTIME_VERSION}}\2', out)
    out = re.sub(r'(VD_OS_PLATFORM=")[^"]*(")', r'\1{{OS_PLATFORM}}\2', out)
    return out


class HookTestBase(unittest.TestCase):
    def _cleanup(self, path):
        self.addCleanup(shutil.rmtree, path, ignore_errors=True)

    def mkdtemp(self, prefix):
        d = tempfile.mkdtemp(prefix=prefix)
        self._cleanup(d)
        return d

    def mk_temp_repo(self, label, branch='main'):
        tmp = self.mkdtemp('vd-parity-%s-' % label)
        repo = os.path.realpath(tmp)
        git(repo, 'init', '-b', branch)
        git(repo, 'config', 'user.email', 'test@example.com')
        git(repo, 'config', 'user.name', 'Test')
        with open(os.path.join(repo, 'README.md'), 'w') as f:
            f.write('# fixture\n')
        git(repo, 'add', 'README.md')
        git(repo, 'commit', '-m', 'init')
        return repo

    def mk_fake_home(self, cfg=None):
        fake_home = os.path.realpath(self.mkdtemp('vd-fake-home-'))
        claude = os.path.join(fake_home, '.claude')
        os.makedirs(claude, exist_ok=True)
        if cfg is not None:
            with open(os.path.join(claude, '.vd.json'), 'w') as f:
                f.write(json.dumps(cfg, indent=2) if isinstance(cfg, dict) else cfg)
        # Give subagent-init a resolvable skills venv (used by the Naming/Rules block).
        venv_bin = os.path.join(claude, 'skills', '.venv', 'bin')
        os.makedirs(venv_bin, exist_ok=True)
        open(os.path.join(venv_bin, 'python3'), 'w').close()
        return fake_home

    def run_session_init(self, repo, fake_home, state_dir=None, extra_env=None):
        state_dir = state_dir or self.mkdtemp('vd-state-')
        env_file = os.path.join(self.mkdtemp('vd-env-'), 'env.sh')
        open(env_file, 'w').close()
        env = {
            'HOME': fake_home,
            'CLAUDE_ENV_FILE': env_file,
            'CLAUDE_SESSION_ID': FIXED_SESSION_ID,
            'VD_SESSION_ID': FIXED_SESSION_ID,
            'TMPDIR': state_dir,
        }
        if extra_env:
            env.update(extra_env)
        run_raw(SESSION_INIT, json.dumps({'session_id': FIXED_SESSION_ID, 'source': 'startup',
                                          'hook_event_name': 'SessionStart'}), env, cwd=repo)
        with open(env_file, 'r') as f:
            return f.read()

    def run_subagent_init(self, repo, fake_home, state_dir=None, extra_env=None):
        state_dir = state_dir or self.mkdtemp('vd-state-')
        env = {
            'HOME': fake_home,
            'CLAUDE_SESSION_ID': FIXED_SESSION_ID,
            'VD_SESSION_ID': FIXED_SESSION_ID,
            'TMPDIR': state_dir,
        }
        if extra_env:
            env.update(extra_env)
        _, out, _ = run_json(SUBAGENT_INIT, {
            'session_id': FIXED_SESSION_ID,
            'agent_id': 'aaaaaaaa-test-0001',
            'agent_type': 'fullstack-developer',
            'cwd': repo,
            'hook_event_name': 'SubagentStart',
        }, env, cwd=repo)
        return out

    def extract_context(self, stdout):
        try:
            return (json.loads(stdout.strip()).get('hookSpecificOutput') or {}).get('additionalContext') or ''
        except Exception:
            return stdout

    def inject_active_plan(self, state_dir, active_plan, session_origin):
        tmp_file = os.path.join(state_dir, 'vd-session-%s.json' % FIXED_SESSION_ID)
        state = {}
        if os.path.exists(tmp_file):
            with open(tmp_file, 'r') as f:
                state = json.load(f)
        state.update({'activePlan': active_plan, 'sessionOrigin': session_origin,
                      'timestamp': 0, 'source': 'startup'})
        with open(tmp_file, 'w') as f:
            f.write(json.dumps(state, indent=2))


# ── TASK 1: statusline ─────────────────────────────────────────────────────

@unittest.skipUnless(os.path.exists(STATUSLINE), 'statusline.py not present')
class StatuslineTest(HookTestBase):
    def test_exit0_and_nonempty_on_valid_input(self):
        code, out, _ = run_json(STATUSLINE, {'model': 'claude-sonnet-4-5', 'cwd': '/tmp/myproject',
                                             'context_window_usage_percent': 42})
        self.assertEqual(code, 0)
        self.assertTrue(out.strip())

    def test_stdout_contains_model_name(self):
        _, out, _ = run_json(STATUSLINE, {'model': 'claude-opus-4', 'cwd': '/tmp',
                                          'context_window_usage_percent': 20})
        self.assertIn('opus', out)

    def test_fail_open_empty_stdin(self):
        code, out, _ = run_raw(STATUSLINE, '')
        self.assertEqual(code, 0)
        self.assertTrue(out.strip())

    def test_fail_open_invalid_json(self):
        code, out, _ = run_raw(STATUSLINE, '{not json}')
        self.assertEqual(code, 0)
        self.assertTrue(out.strip())


# ── TASK 2: scout-block ────────────────────────────────────────────────────

@unittest.skipUnless(os.path.exists(SCOUT_BLOCK), 'scout-block.py not present')
class ScoutBlockTest(HookTestBase):
    def test_allows_normal_source_path(self):
        code, _, err = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                              'tool_input': {'file_path': 'src/index.ts'}, 'cwd': '/tmp'})
        self.assertEqual(code, 0, err)

    def test_blocks_node_modules(self):
        code, _, err = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                              'tool_input': {'file_path': 'node_modules/lodash/index.js'},
                                              'cwd': '/tmp'})
        self.assertEqual(code, 2)
        self.assertTrue('BLOCKED' in err or 'blocked' in err, err)

    def test_blocks_git_path(self):
        code, _, _ = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                            'tool_input': {'file_path': '.git/config'}, 'cwd': '/tmp'})
        self.assertEqual(code, 2)

    def test_blocks_broad_glob(self):
        code, _, err = run_json(SCOUT_BLOCK, {'tool_name': 'Glob',
                                              'tool_input': {'pattern': '**/*.ts'}, 'cwd': '/tmp'})
        self.assertEqual(code, 2)
        self.assertTrue('broad' in err.lower() or 'BLOCKED' in err, err)

    def test_allows_glob_with_specific_prefix(self):
        code, _, err = run_json(SCOUT_BLOCK, {'tool_name': 'Glob',
                                              'tool_input': {'pattern': 'src/**/*.ts'}, 'cwd': '/tmp'})
        self.assertEqual(code, 0, err)

    def test_vdignore_star_wildcards_match(self):
        # '*' must become [^/]* and '**' .*; the un-escaped '*' used to act as a
        # regex quantifier (secret* matched 'secre') and '**' failed to compile.
        home = tempfile.mkdtemp(prefix='vd-ig-')
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        os.makedirs(os.path.join(home, '.claude'), exist_ok=True)
        with open(os.path.join(home, '.claude', '.vdignore'), 'w') as f:
            f.write('secret*\n**/gen\n')
        env = {'HOME': home}
        code, _, _ = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                            'tool_input': {'file_path': 'secret-stuff/x.txt'},
                                            'cwd': '/tmp'}, extra_env=env)
        self.assertEqual(code, 2, 'secret* must match secret-stuff')
        code, _, _ = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                            'tool_input': {'file_path': 'a/b/gen/x.txt'},
                                            'cwd': '/tmp'}, extra_env=env)
        self.assertEqual(code, 2, '**/gen must match at depth')
        code, _, _ = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                            'tool_input': {'file_path': 'src/main.py'},
                                            'cwd': '/tmp'}, extra_env=env)
        self.assertEqual(code, 0)

    def test_absolute_target_path_checks_manifest_at_filesystem_root(self):
        # normalize() strips the leading '/'; the manifest probe must anchor back
        # to the absolute parent, not resolve the stripped prefix against cwd.
        rusty = tempfile.mkdtemp(prefix='vd-rusty-')
        self.addCleanup(shutil.rmtree, rusty, ignore_errors=True)
        open(os.path.join(rusty, 'Cargo.toml'), 'w').close()
        code, _, _ = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                            'tool_input': {'file_path': rusty + '/target/debug/x'},
                                            'cwd': '/'})
        self.assertEqual(code, 2, 'absolute rust target must block')
        plain = tempfile.mkdtemp(prefix='vd-plain-')
        self.addCleanup(shutil.rmtree, plain, ignore_errors=True)
        os.makedirs(os.path.join(plain, 'internal', 'target'), exist_ok=True)
        code, _, _ = run_json(SCOUT_BLOCK, {'tool_name': 'Read',
                                            'tool_input': {'file_path': plain + '/internal/target/x.go'},
                                            'cwd': '/'})
        self.assertEqual(code, 0, 'absolute non-build target must pass')

    def test_allows_build_command_mentioning_node_modules(self):
        code, _, _ = run_json(SCOUT_BLOCK, {'tool_name': 'Bash',
                                            'tool_input': {'command': 'npm run build'}, 'cwd': '/tmp'})
        self.assertEqual(code, 0)

    def _bash(self, command, cwd='/tmp'):
        return run_json(SCOUT_BLOCK, {'tool_name': 'Bash',
                                      'tool_input': {'command': command}, 'cwd': cwd})

    def test_allows_env_var_assignment_value(self):
        # (a) FOO=<blocked-path> prefix: the value must not be treated as a scan target
        for cmd in ('AB_PROFILE=~/.cache/agent-browser-profiles/x agent-browser snapshot',
                    'env AB_PROFILE=~/.cache/agent-browser-profiles/x agent-browser snapshot'):
            code, _, err = self._bash(cmd)
            self.assertEqual(code, 0, '%s: %s' % (cmd, err))

    def test_allows_binary_under_blocked_dir_in_command_position(self):
        # (b) running a tool that lives under a blocked dir is not scanning a tree
        for cmd in ('vendor/bin/pint --dirty', 'node_modules/.bin/vite build',
                    'sudo vendor/bin/pint', 'bash node_modules/.bin/vite'):
            code, _, err = self._bash(cmd)
            self.assertEqual(code, 0, '%s: %s' % (cmd, err))

    def test_allows_local_binary_with_dot_prefix(self):
        dependency_dir = 'node_' + 'modules'
        code, _, err = self._bash('./' + dependency_dir + '/.bin/prettier --write src/x.ts')
        self.assertEqual(code, 0, err)

    def test_allows_quoted_negative_path_filters(self):
        dependency_dir = 'node_' + 'modules'
        cmd = 'find docs -not -path "*/' + dependency_dir + '/*" -name "*.md"'
        code, _, err = self._bash(cmd)
        self.assertEqual(code, 0, err)

    def test_still_blocks_positive_path_filters(self):
        dependency_dir = 'node_' + 'modules'
        cmd = 'find . -path "*/' + dependency_dir + '/*" -print'
        code, _, err = self._bash(cmd)
        self.assertEqual(code, 2, err)

    def test_allows_paths_inside_heredoc_body(self):
        dependency_dir = 'ven' + 'dor'
        cmd = "ssh app 'php' <<'PHP'\nrequire '/home/app/" + dependency_dir + "/autoload.php';\nPHP"
        code, _, err = self._bash(cmd)
        self.assertEqual(code, 0, err)

    def test_still_blocks_paths_inside_local_shell_heredoc(self):
        dependency_dir = 'node_' + 'modules'
        cmd = "bash <<'SH'\ncat " + dependency_dir + "/x\nSH"
        code, _, err = self._bash(cmd)
        self.assertEqual(code, 2, err)

    def test_still_blocks_unquoted_remote_heredoc_expansions(self):
        dependency_dir = 'node_' + 'modules'
        cmd = "ssh app <<SH\ncat " + dependency_dir + "/x\nSH"
        code, _, err = self._bash(cmd)
        self.assertEqual(code, 2, err)

    def test_still_blocks_local_heredoc_after_ssh_command(self):
        dependency_dir = 'node_' + 'modules'
        cmd = "ssh app true; bash <<'SH'\ncat " + dependency_dir + "/x\nSH"
        code, _, err = self._bash(cmd)
        self.assertEqual(code, 2, err)

    def test_still_blocks_piped_local_heredoc_after_ssh(self):
        dependency_dir = 'node_' + 'modules'
        cmd = "ssh app | bash <<'SH'\ncat " + dependency_dir + "/x\nSH"
        code, _, err = self._bash(cmd)
        self.assertEqual(code, 2, err)

    def test_apply_patch_checks_headers_not_patch_content(self):
        dependency_dir = 'node_' + 'modules'
        patch = '*** Begin Patch\n*** Update File: src/x.py\n+' + dependency_dir + '/x\n*** End Patch'
        code, _, err = run_json(SCOUT_BLOCK, {
            'tool_name': 'apply_patch', 'tool_input': {'command': patch}, 'cwd': '/tmp',
        })
        self.assertEqual(code, 0, err)

        blocked_patch = '*** Begin Patch\n*** Update File: ' + dependency_dir + '/x.py\n+x\n*** End Patch'
        code, _, err = run_json(SCOUT_BLOCK, {
            'tool_name': 'apply_patch', 'tool_input': {'command': blocked_patch}, 'cwd': '/tmp',
        })
        self.assertEqual(code, 2, err)

        moved_patch = ('*** Begin Patch\n*** Update File: src/x.py\n'
                       '*** Move to: ' + dependency_dir + '/x.py\n*** End Patch')
        code, _, err = run_json(SCOUT_BLOCK, {
            'tool_name': 'apply_patch', 'tool_input': {'command': moved_patch}, 'cwd': '/tmp',
        })
        self.assertEqual(code, 2, err)

    def test_allows_git_info_exclude(self):
        # (c) worktree flows legitimately read/write .git/info/exclude
        for cmd in ('echo dist >> .git/info/exclude', 'cat .git/info/exclude'):
            code, _, err = self._bash(cmd)
            self.assertEqual(code, 0, '%s: %s' % (cmd, err))

    def test_allows_cheap_single_file_read_in_blocked_dir(self):
        # (d) read-only single-file read with an explicit file path (has ext, no glob)
        for cmd in ('cat public/build/manifest.json', 'head -n50 dist/report.json',
                    'stat node_modules/lodash/package.json'):
            code, _, err = self._bash(cmd)
            self.assertEqual(code, 0, '%s: %s' % (cmd, err))

    def test_still_blocks_recursive_grep_into_node_modules(self):
        code, _, err = self._bash('grep -r foo node_modules/')
        self.assertEqual(code, 2, err)

    def test_blocks_git_info_traversal(self):
        for cmd in ('cat .git/info/../../config', 'cat a/../.git/info/exclude'):
            code, _, err = self._bash(cmd)
            self.assertEqual(code, 2, '%s: %s' % (cmd, err))

    def test_wrapper_chain_stays_transparent(self):
        # wrappers never hide the real command: fs scan behind a chain still blocks,
        # executing a tool behind a chain stays allowed
        code, _, err = self._bash('bash bash bash rm -rf node_modules')
        self.assertEqual(code, 2, err)
        code, _, err = self._bash('bash bash bash vendor/bin/tool')
        self.assertEqual(code, 0, err)
        code, _, err = self._bash('source rm -rf node_modules')
        self.assertEqual(code, 2, err)

    def test_blocks_read_of_git_files_despite_extension(self):
        for cmd in ('cat .git/config', 'bat .git/objects/pack/p.idx'):
            code, _, err = self._bash(cmd)
            self.assertEqual(code, 2, '%s: %s' % (cmd, err))

    def test_blocks_assignment_value_after_command(self):
        code, _, err = self._bash('echo FOO=.git/config')
        self.assertEqual(code, 2, err)
        code, _, err = self._bash('echo FOO=node_modules/x BAR=dist/y')
        self.assertEqual(code, 2, err)
        code, _, err = self._bash('echo FOO=src/main.py')
        self.assertEqual(code, 0, err)

    def test_blocks_dot_source_of_blocked_path(self):
        code, _, err = self._bash('. vendor/bin/activate.sh')
        self.assertEqual(code, 2, err)

    def test_still_blocks_find_scan_of_git(self):
        code, _, err = self._bash("find .git -name '*.pack'")
        self.assertEqual(code, 2, err)

    def test_still_blocks_tree_of_build(self):
        code, _, err = self._bash('tree build/')
        self.assertEqual(code, 2, err)

    def test_fail_open_empty_stdin(self):
        code, _, _ = run_raw(SCOUT_BLOCK, '')
        self.assertEqual(code, 0)


# ── TASK 3: team hooks ─────────────────────────────────────────────────────

@unittest.skipUnless(os.path.exists(TEAM_INJECT), 'team-context-inject.py not present')
class TeamContextInjectTest(HookTestBase):
    def test_noop_non_team_agent(self):
        code, out, _ = run_json(TEAM_INJECT, {'agent_id': 'researcher', 'agent_type': 'researcher',
                                              'cwd': '/tmp'})
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), '')

    def test_noop_when_teams_dir_absent(self):
        fake_home = self.mkdtemp('vd-test-home-')
        code, out, _ = run_json(TEAM_INJECT, {'agent_id': 'researcher@my-team',
                                              'agent_type': 'researcher', 'cwd': '/tmp'},
                                {'HOME': fake_home})
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), '')

    def test_injects_team_context(self):
        fake_home = self.mkdtemp('vd-test-home-')
        teams_dir = os.path.join(fake_home, '.claude', 'teams', 'my-team')
        os.makedirs(teams_dir, exist_ok=True)
        with open(os.path.join(teams_dir, 'config.json'), 'w') as f:
            f.write(json.dumps({'name': 'My Team', 'members': [
                {'agentId': 'researcher@my-team', 'name': 'researcher', 'agentType': 'researcher'},
                {'agentId': 'developer@my-team', 'name': 'developer', 'agentType': 'developer'},
            ]}))
        code, out, err = run_json(TEAM_INJECT, {'agent_id': 'researcher@my-team',
                                                'agent_type': 'researcher', 'cwd': '/tmp'},
                                  {'HOME': fake_home})
        self.assertEqual(code, 0, err)
        obj = json.loads(out.strip())
        self.assertTrue(obj.get('hookSpecificOutput'))
        ctx = obj['hookSpecificOutput']['additionalContext']
        self.assertIn('My Team', ctx)
        self.assertIn('developer', ctx)


@unittest.skipUnless(os.path.exists(TASK_COMPLETED), 'task-completed-handler.py not present')
class TaskCompletedTest(HookTestBase):
    def test_noop_when_team_name_absent(self):
        code, out, _ = run_json(TASK_COMPLETED, {'task_id': 1, 'task_subject': 'Do something',
                                                 'teammate_name': 'dev'})
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), '')

    def test_emits_progress_summary(self):
        fake_home = self.mkdtemp('vd-test-home-')
        reports_dir = os.path.join(fake_home, 'reports')
        tasks_dir = os.path.join(fake_home, '.claude', 'tasks', 'proj')
        os.makedirs(tasks_dir, exist_ok=True)
        with open(os.path.join(tasks_dir, '1.json'), 'w') as f:
            f.write(json.dumps({'id': 1, 'status': 'completed', 'subject': 'Task one'}))
        with open(os.path.join(tasks_dir, '2.json'), 'w') as f:
            f.write(json.dumps({'id': 2, 'status': 'pending', 'subject': 'Task two'}))
        code, out, err = run_json(TASK_COMPLETED, {'task_id': 1, 'task_subject': 'Task one',
                                                   'teammate_name': 'dev', 'team_name': 'proj'},
                                  {'HOME': fake_home, 'VD_REPORTS_PATH': reports_dir})
        self.assertEqual(code, 0, err)
        obj = json.loads(out.strip())
        ctx = obj['hookSpecificOutput']['additionalContext']
        self.assertIn('Task', ctx)
        self.assertTrue('completed' in ctx or 'Completed' in ctx)


@unittest.skipUnless(os.path.exists(TEAMMATE_IDLE), 'teammate-idle-handler.py not present')
class TeammateIdleTest(HookTestBase):
    def test_noop_when_team_name_absent(self):
        code, out, _ = run_json(TEAMMATE_IDLE, {'teammate_name': 'dev'})
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), '')

    def test_emits_idle_summary(self):
        fake_home = self.mkdtemp('vd-test-home-')
        tasks_dir = os.path.join(fake_home, '.claude', 'tasks', 'proj')
        os.makedirs(tasks_dir, exist_ok=True)
        with open(os.path.join(tasks_dir, '1.json'), 'w') as f:
            f.write(json.dumps({'id': 1, 'status': 'completed', 'subject': 'Task one'}))
        with open(os.path.join(tasks_dir, '2.json'), 'w') as f:
            f.write(json.dumps({'id': 2, 'status': 'pending', 'subject': 'Task two', 'blockedBy': []}))
        code, out, err = run_json(TEAMMATE_IDLE, {'teammate_name': 'dev', 'team_name': 'proj'},
                                  {'HOME': fake_home})
        self.assertEqual(code, 0, err)
        obj = json.loads(out.strip())
        ctx = obj['hookSpecificOutput']['additionalContext']
        self.assertTrue(ctx)
        self.assertTrue('idle' in ctx or 'Tasks' in ctx)


# ── session-init / subagent-init parity scenarios ──────────────────────────

@unittest.skipUnless(os.path.exists(SESSION_INIT), 'session-init.py not present')
class SessionInitParityTest(HookTestBase):
    def test_defaults_golden(self):
        repo = self.mk_temp_repo('defaults')
        fake_home = self.mk_fake_home(DEFAULT_VD_CONFIG)
        raw = self.run_session_init(repo, fake_home)
        ours = mask(raw, repo, fake_home, None).rstrip('\n')
        self.assertEqual(ours, DEFAULT_ENV_GOLDEN)

    def test_custom_golden(self):
        repo = self.mk_temp_repo('custom')
        fake_home = self.mk_fake_home(CUSTOM_VD_CONFIG)
        raw = self.run_session_init(repo, fake_home)
        ours = mask(raw, repo, fake_home, 'my-reports').rstrip('\n')
        self.assertEqual(ours, CUSTOM_ENV_GOLDEN)

    def test_runtime_version_replaces_node_version(self):
        repo = self.mk_temp_repo('runtime')
        fake_home = self.mk_fake_home(DEFAULT_VD_CONFIG)
        env_map = parse_env_map(self.run_session_init(repo, fake_home))
        self.assertNotIn('VD_NODE_VERSION', env_map)
        self.assertIn('VD_RUNTIME_VERSION', env_map)
        self.assertTrue(env_map['VD_RUNTIME_VERSION'].startswith('python/'),
                        env_map['VD_RUNTIME_VERSION'])

    def test_session_active_plan_relative_reports_consistent(self):
        repo = self.mk_temp_repo('active-rel')
        fake_home = self.mk_fake_home(DEFAULT_VD_CONFIG)
        state_dir = self.mkdtemp('vd-state-')
        self.inject_active_plan(state_dir, 'plans/260101-1200-my-plan', repo)

        env_map = parse_env_map(self.run_session_init(repo, fake_home, state_dir))
        si_reports = env_map.get('VD_REPORTS_PATH', '')

        sub_ctx = self.extract_context(self.run_subagent_init(repo, fake_home, state_dir))
        sub_line = next((l for l in sub_ctx.split('\n') if l.startswith('- Reports:')), '')
        sub_reports = sub_line.replace('- Reports: ', '').strip()

        si_base = re.sub(r'/$', '', si_reports)
        sub_base = re.sub(r'/$', '', sub_reports)
        self.assertTrue(si_base and sub_base and si_base == sub_base,
                        'session-init: %s  subagent-init: %s' % (si_reports, sub_reports))

    def test_session_active_plan_absolute_no_double_anchor(self):
        repo = self.mk_temp_repo('active-abs')
        fake_home = self.mk_fake_home(DEFAULT_VD_CONFIG)
        state_dir = self.mkdtemp('vd-state-')
        absolute_plan = os.path.join(repo, 'plans', '260101-1200-abs-plan')
        self.inject_active_plan(state_dir, absolute_plan, repo)

        env_map = parse_env_map(self.run_session_init(repo, fake_home, state_dir))
        si_reports = env_map.get('VD_REPORTS_PATH', '')

        # No double-anchor: repo must not appear twice in the resolved path.
        self.assertLessEqual(len(si_reports.split(repo)), 2,
                             'double-anchor detected: %s' % si_reports)
        expected = os.path.join(absolute_plan, 'reports')
        self.assertEqual(re.sub(r'/$', '', si_reports), expected)

        sub_ctx = self.extract_context(self.run_subagent_init(repo, fake_home, state_dir))
        sub_line = next((l for l in sub_ctx.split('\n') if l.startswith('- Reports:')), '')
        sub_reports = sub_line.replace('- Reports: ', '').strip()
        self.assertEqual(re.sub(r'/$', '', sub_reports), expected)

    def test_issue_branch_naming_with_issue_prefix(self):
        repo = self.mk_temp_repo('issue-branch', 'feat/gh-88-x')
        fake_home = self.mk_fake_home(CUSTOM_VD_CONFIG)  # issuePrefix='GH-'
        env_map = parse_env_map(self.run_session_init(repo, fake_home))
        pattern = env_map.get('VD_NAME_PATTERN', '')
        self.assertIn('GH-88', pattern)

    def test_non_git_dir_git_root_empty(self):
        d = self.mkdtemp('vd-nongit-')
        fake_home = self.mk_fake_home(DEFAULT_VD_CONFIG)
        raw = self.run_session_init(d, fake_home)
        line = next((l for l in raw.split('\n') if l.startswith('export VD_GIT_ROOT=')), None)
        self.assertIsNotNone(line, 'VD_GIT_ROOT line missing')
        self.assertIn('VD_GIT_ROOT=""', line)

    def test_detached_head_branch_empty(self):
        repo = self.mk_temp_repo('detached')
        fake_home = self.mk_fake_home(DEFAULT_VD_CONFIG)
        sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo,
                             capture_output=True, text=True).stdout.strip()
        git(repo, 'checkout', '--detach', sha)
        raw = self.run_session_init(repo, fake_home)
        env_map = parse_env_map(raw)
        self.assertIn('VD_SESSION_ID', env_map)  # ran without throw
        if 'VD_GIT_BRANCH' in env_map:
            self.assertEqual(env_map['VD_GIT_BRANCH'], '')

    def test_no_vd_json_defaults_applied(self):
        repo = self.mk_temp_repo('no-config')
        fake_home = self.mk_fake_home(None)  # .claude exists, no .vd.json
        raw = self.run_session_init(repo, fake_home)
        env_map = parse_env_map(raw)
        self.assertEqual(env_map.get('VD_PLAN_REPORTS_DIR'), 'reports')

    def test_malformed_vd_json_no_crash(self):
        repo = self.mk_temp_repo('malformed')
        fake_home = self.mk_fake_home('{this is not json}')
        raw = self.run_session_init(repo, fake_home)
        self.assertIn('VD_SESSION_ID=', raw)


@unittest.skipUnless(os.path.exists(SUBAGENT_INIT), 'subagent-init.py not present')
class SubagentInitParityTest(HookTestBase):
    def test_defaults_context_golden(self):
        repo = self.mk_temp_repo('subagent')
        fake_home = self.mk_fake_home(DEFAULT_VD_CONFIG)
        ctx = self.extract_context(self.run_subagent_init(repo, fake_home))
        ours = mask(ctx, repo, fake_home, None)
        ours = re.sub(r'\b\d{6}-\d{4}\b', '{{DATE}}-{{TIME}}', ours).rstrip('\n')
        self.assertEqual(ours, SUBAGENT_CONTEXT_GOLDEN)


class DevRulesReminderTest(HookTestBase):
    def test_empty_object_payload_still_emits_context(self):
        # {} is falsy in Python but was a valid payload in the .cjs (JS truthy).
        code, out, err = run_raw(os.path.join(HOOKS_DIR, 'dev-rules-reminder.py'), '{}')
        self.assertEqual(code, 0, err)
        obj = json.loads(out.strip())
        self.assertEqual(set(obj), {'hookSpecificOutput'})
        self.assertIn('## Paths', obj['hookSpecificOutput']['additionalContext'])

    def test_codex_rejects_top_level_shape_so_output_is_always_nested(self):
        code, out, _ = run_json(os.path.join(HOOKS_DIR, 'dev-rules-reminder.py'),
                                {'cwd': '/tmp', 'session_id': 't',
                                 'hook_event_name': 'UserPromptSubmit'})
        self.assertEqual(code, 0)
        obj = json.loads(out.strip())
        self.assertNotIn('additionalContext', obj)
        self.assertEqual(obj['hookSpecificOutput']['hookEventName'], 'UserPromptSubmit')


@unittest.skipUnless(os.path.exists(HERDR_PANE_NAME), 'herdr-pane-name.py not present')
class HerdrPaneNameTest(HookTestBase):
    def setUp(self):
        self.state_dir = self.mkdtemp('vd-herdr-state-')
        self.bin_dir = self.mkdtemp('vd-herdr-bin-')
        self.log_path = os.path.join(self.mkdtemp('vd-herdr-log-'), 'calls.jsonl')
        self.repo = self.mk_temp_repo('herdr-pane-name')
        fake = os.path.join(self.bin_dir, 'herdr')
        with open(fake, 'w') as f:
            f.write("""#!/usr/bin/env python3
import json
import os
import sys
import time

with open(os.environ['HERDR_TEST_LOG'], 'a', encoding='utf-8') as handle:
    handle.write(json.dumps(sys.argv[1:]) + '\\n')
if os.environ.get('HERDR_TEST_SLEEP'):
    time.sleep(float(os.environ['HERDR_TEST_SLEEP']))
raise SystemExit(int(os.environ.get('HERDR_TEST_EXIT', '0')))
""")
        os.chmod(fake, 0o755)

    def env(self, **overrides):
        values = {
            'HERDR_ENV': '1',
            'HERDR_PANE_ID': 'w1:pane-test',
            'HERDR_TEST_LOG': self.log_path,
            'PATH': self.bin_dir + os.pathsep + os.environ.get('PATH', ''),
            'TMPDIR': self.state_dir,
        }
        values.update(overrides)
        return values

    def payload(self, session_id=FIXED_SESSION_ID, prompt='Name the Herdr pane'):
        return {
            'session_id': session_id,
            'cwd': self.repo,
            'hook_event_name': 'UserPromptSubmit',
            'prompt': prompt,
        }

    def calls(self):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def run_hook(self, payload=None, env=None):
        return run_json(HERDR_PANE_NAME, payload or self.payload(), env or self.env(), cwd=self.repo)

    def test_first_prompt_renames_once_and_stores_no_prompt(self):
        prompt = ('$vd:brainstorm Build a SessionStart hook for both codex and claude '
                  'code, it will based on context')
        payload = self.payload(prompt=prompt)
        payload['cwd'] = os.path.dirname(HOOKS_DIR)
        first = self.run_hook(payload)
        second = self.run_hook(payload)
        self.assertEqual(first, (0, '', ''))
        self.assertEqual(second, (0, '', ''))
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0:3], ['pane', 'rename', 'w1:pane-test'])
        self.assertEqual(calls[0][3].split(':', 1)[1], 'session-start-hook-context')
        state_path = os.path.join(self.state_dir, 'vd-session-%s.json' % FIXED_SESSION_ID)
        with open(state_path) as f:
            state_text = f.read()
        self.assertNotIn(prompt, state_text)
        self.assertEqual(json.loads(state_text)['herdrPaneRename']['label'], calls[0][3])

    def test_concurrent_duplicate_deliveries_invoke_herdr_once(self):
        encoded = json.dumps(self.payload())
        env = dict(os.environ)
        env.update(self.env())
        processes = [
            subprocess.Popen(
                [sys.executable, HERDR_PANE_NAME],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.repo,
                env=env,
            )
            for _ in range(8)
        ]
        results = [process.communicate(encoded, timeout=10) for process in processes]
        self.assertTrue(all(process.returncode == 0 for process in processes))
        self.assertTrue(all(result == ('', '') for result in results))
        self.assertEqual(len(self.calls()), 1)

    def test_failed_or_timed_out_rename_is_not_retried(self):
        for suffix, overrides in (
            ('failure', {'HERDR_TEST_EXIT': '1'}),
            ('timeout', {'HERDR_TEST_SLEEP': '2'}),
        ):
            with self.subTest(suffix=suffix):
                session_id = '%s-%s' % (FIXED_SESSION_ID, suffix)
                payload = self.payload(session_id=session_id)
                env = self.env(**overrides)
                self.assertEqual(self.run_hook(payload, env)[0], 0)
                self.assertEqual(self.run_hook(payload, env)[0], 0)
        self.assertEqual(len(self.calls()), 2)

    def test_each_new_session_can_rename_once(self):
        self.run_hook(self.payload(session_id='session-one'))
        self.run_hook(self.payload(session_id='session-two'))
        self.assertEqual(len(self.calls()), 2)

    def test_claude_and_codex_payloads_produce_same_label(self):
        claude = self.payload(session_id='claude-session', prompt='Fix ELT-3267 call routing')
        codex = self.payload(session_id='codex-session', prompt='Fix ELT-3267 call routing')
        codex['turn_id'] = 'turn-1'
        self.run_hook(claude)
        self.run_hook(codex)
        labels = [call[3] for call in self.calls()]
        self.assertEqual(len(labels), 2)
        self.assertEqual(labels[0], labels[1])
        self.assertTrue(labels[0].endswith(':ELT-3267'))

    def test_untrusted_prompt_cannot_escape_into_label(self):
        cases = [
            ('mixed-secret', '$vd:fix Add auth token sk_TestSecret123456789 from '
             'https://example.com/private /tmp/password API_KEY=visible $(touch /tmp/pwn)'),
            ('secret-ticket', 'Use token SECRET-1234567'),
            ('compound-secret-ticket', 'Use access_token SECRET-1234567'),
            ('long-secret-ticket', 'Use token value is SECRET-1234567'),
            ('generic-secret-ticket', 'Use token value is ABC-1234567'),
            ('qualified-secret-ticket', 'Use token named production ABC-1234567'),
            ('refresh-token-ticket', 'Use refresh_token ABC-1234567'),
            ('client-secret-ticket', 'Use client_secret ABC-1234567'),
            ('private-key-ticket', 'Use private_key ABC-1234567'),
            ('passphrase', 'Set passphrase hunter2'),
            ('long-passphrase', 'Set passphrase value is hunter2'),
            ('long-token', 'Use token named production hunter2'),
            ('pin', 'Use PIN 123456'),
            ('otp', 'Use OTP 654321'),
            ('comma-secret', 'Use API key, ABC-1234567'),
            ('bare-secret-ticket', 'Rotate SECRET-1234567'),
        ]
        for session_id, prompt in cases:
            self.run_hook(self.payload(session_id=session_id, prompt=prompt))
        labels = [call[3] for call in self.calls()]
        self.assertEqual(len(labels), len(cases))
        for label in labels:
            self.assertLessEqual(len(label), 40)
            self.assertRegex(label, r'^[A-Za-z0-9-]+:[A-Za-z0-9-]+$')
            for secret in ('secret', 'abc-1234567', '123456', '654321', 'example',
                           'hunter2', 'password', 'visible', '/tmp', '$('):
                self.assertNotIn(secret.lower(), label.lower())
        for session_id, prompt in cases:
            state_path = os.path.join(self.state_dir, 'vd-session-%s.json' % session_id)
            with open(state_path) as f:
                self.assertNotIn(prompt, f.read())

    def test_api_prompts_keep_normal_intent_and_ticket(self):
        api_intent = self.payload(session_id='api-intent', prompt='Fix API response serialization')
        api_ticket = self.payload(session_id='api-ticket', prompt='Fix API ELT-3267 call routing')
        api_intent['cwd'] = os.path.dirname(HOOKS_DIR)
        api_ticket['cwd'] = os.path.dirname(HOOKS_DIR)
        self.run_hook(api_intent)
        self.run_hook(api_ticket)
        labels = [call[3] for call in self.calls()]
        self.assertTrue(labels[0].endswith(':api-response-serialization'))
        self.assertTrue(labels[1].endswith(':ELT-3267'))

    def test_skill_only_prompt_uses_full_invocation_name(self):
        self.run_hook(self.payload(prompt='$vd:code-review'))
        self.assertTrue(self.calls()[0][3].endswith(':code-review'))

    def test_ineligible_inputs_fail_open_without_rename(self):
        cases = [
            ('not-herdr', self.payload(session_id='not-herdr'), self.env(HERDR_ENV='0')),
            ('no-pane', self.payload(session_id='no-pane'), self.env(HERDR_PANE_ID='')),
            ('no-prompt', self.payload(session_id='no-prompt', prompt=''), self.env()),
            ('subagent', dict(self.payload(session_id='subagent'), agent_id='agent-1'), self.env()),
        ]
        for name, payload, env in cases:
            with self.subTest(name=name):
                self.assertEqual(self.run_hook(payload, env), (0, '', ''))
        code, out, err = run_raw(HERDR_PANE_NAME, '{bad json', self.env(), cwd=self.repo)
        self.assertEqual((code, out, err), (0, '', ''))
        self.assertEqual(self.calls(), [])


class SessionInitProjectTypeTest(HookTestBase):
    def test_empty_workspaces_array_is_monorepo_like_js(self):
        d = tempfile.mkdtemp(prefix='vd-ws-')
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, 'package.json'), 'w') as f:
            f.write('{"workspaces": []}')
        code, out, err = run_json(SESSION_INIT, {'session_id': 't', 'source': 'startup'}, cwd=d)
        self.assertEqual(code, 0, err)
        self.assertIn('Project: monorepo', out)

    def test_empty_exports_object_is_library_like_js(self):
        d = tempfile.mkdtemp(prefix='vd-lib-')
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, 'package.json'), 'w') as f:
            f.write('{"exports": {}}')
        code, out, err = run_json(SESSION_INIT, {'session_id': 't', 'source': 'startup'}, cwd=d)
        self.assertEqual(code, 0, err)
        self.assertIn('Project: library', out)


if __name__ == '__main__':
    unittest.main()
