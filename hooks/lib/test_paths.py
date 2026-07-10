#!/usr/bin/env python3
"""1:1 Python port of paths.test.cjs, targeting vd_paths.py + vd_config.py.

Run: python3 -m unittest discover -s hooks/lib
 or: python3 hooks/lib/test_paths.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

LIB_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, LIB_DIR)

import vd_paths as paths  # noqa: E402
import vd_config as config  # noqa: E402


def realpath(p):
    try:
        return os.path.realpath(p)
    except Exception:
        return os.path.abspath(p)


def git(cwd, *args):
    subprocess.run(['git'] + list(args), cwd=cwd,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def mkdtemp(prefix):
    return tempfile.mkdtemp(prefix=prefix)


def run_child(script, extra_env):
    env = dict(os.environ)
    env['PYLIB'] = LIB_DIR
    env.update(extra_env)
    r = subprocess.run([sys.executable, '-c', script], env=env,
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError('child failed: %s\n%s' % (r.stdout, r.stderr))
    return json.loads(r.stdout.strip())


class PathsTest(unittest.TestCase):
    def _cleanup(self, path):
        self.addCleanup(shutil.rmtree, path, ignore_errors=True)

    # Stray-ancestor guard: a coincidental repo rooted at $HOME must not hijack a
    # nested project's umbrella. The project (a child dir below $HOME, with no git of
    # its own) must anchor .workbench to itself, not to $HOME.
    def test_umbrella_does_not_hijack_ancestor_repo_rooted_at_home(self):
        fake_home = mkdtemp('vd-home-')
        self._cleanup(fake_home)
        git(fake_home, 'init', '-b', 'main')
        git(fake_home, 'config', 'user.email', 't@t.t')
        git(fake_home, 'config', 'user.name', 't')
        git(fake_home, 'commit', '--allow-empty', '-m', 'stray home repo')
        with open(os.path.join(fake_home, '.vd.json'), 'w') as f:
            f.write(json.dumps({'paths': {'umbrella': '.bad'}}))

        project = os.path.join(fake_home, 'git', 'personal', 'proj')
        os.makedirs(project, exist_ok=True)

        # os.path.expanduser reads HOME; use a child so this process is untouched.
        script = (
            "import os, sys, json\n"
            "sys.path.insert(0, os.environ['PYLIB'])\n"
            "import vd_paths as p, vd_config as c\n"
            "b = os.environ['BASE']\n"
            "print(json.dumps({\n"
            "  'root': p.resolve_umbrella_root({'paths': {'umbrella': '.workbench'}}, b),\n"
            "  'allowed': p.resolve_umbrella_root({'paths': {'umbrella': '.workbench', 'allowHomeRoot': True}}, b),\n"
            "  'main': c.get_main_worktree_config(b),\n"
            "}))\n"
        )
        out = run_child(script, {'HOME': fake_home, 'USERPROFILE': fake_home, 'BASE': project})

        self.assertNotEqual(realpath(out['root']), realpath(os.path.join(fake_home, '.workbench')),
                            'umbrella must NOT anchor to $HOME')
        self.assertEqual(realpath(out['root']), realpath(os.path.join(project, '.workbench')),
                         'umbrella must anchor to the project dir')
        self.assertIsNone(out['main'], 'main worktree config must ignore a stray $HOME repo')
        self.assertEqual(realpath(os.path.dirname(out['allowed'])), realpath(fake_home),
                         'allowHomeRoot keeps the home repo anchor')

    # Regression: a normal repo (git root != $HOME) is unaffected by the guard.
    def test_normal_repo_anchors_umbrella_to_its_own_git_root(self):
        repo = mkdtemp('vd-repo-')
        self._cleanup(repo)
        git(repo, 'init', '-b', 'main')
        got = paths.resolve_umbrella_root({'paths': {'umbrella': '.workbench'}, '_gitRoot': repo}, repo)
        self.assertEqual(os.path.basename(got), '.workbench')
        self.assertEqual(realpath(os.path.dirname(got)), realpath(repo))

    # Regression: a brand-new project not yet git-init'd must still anchor at the
    # working dir — returning <cwd>/.workbench — instead of scattering to legacy plans/.
    def test_no_git_root_anchors_umbrella_to_working_dir(self):
        d = mkdtemp('vd-nogit-')
        self._cleanup(d)
        got = paths.resolve_umbrella_root({'paths': {'umbrella': '.workbench'}}, d)
        self.assertTrue(got, 'umbrella must not be None without a git root')
        self.assertEqual(os.path.basename(got), '.workbench')
        self.assertEqual(realpath(os.path.dirname(got)), realpath(d))
        # Opt-out preserved: umbrella unset still returns None (legacy).
        self.assertIsNone(paths.resolve_umbrella_root({'paths': {'umbrella': None}}, d))

    def test_feature_first_getters_use_session_feature_state_when_provided(self):
        repo = mkdtemp('vd-feature-')
        self._cleanup(repo)
        git(repo, 'init', '-b', 'main')
        cfg = {
            '_gitRoot': repo,
            'plan': {'reportsDir': 'reports'},
            'paths': {'umbrella': '.workbench', 'layout': 'feature-first', 'plans': 'plans'},
        }
        read_state = lambda sid=None: {'featureId': 'demo-feature'}  # noqa: E731
        feature_root = os.path.join(realpath(repo), '.workbench', 'features', 'demo-feature')

        self.assertEqual(paths.get_plans_path(repo, cfg, 's1', read_state),
                         os.path.join(feature_root, 'plans'))
        self.assertEqual(
            paths.get_reports_path(None, None, cfg['plan'], cfg['paths'], repo, cfg, 's1', read_state),
            os.path.join(feature_root, 'reports'))
        self.assertEqual(
            paths.get_reports_path(os.path.join(repo, 'plans', 'active'), 'session',
                                   cfg['plan'], cfg['paths'], repo, cfg, 's1', read_state),
            os.path.join(repo, 'plans', 'active', 'reports'))
        prev = os.getcwd()
        try:
            os.chdir(repo)
            self.assertEqual(
                paths.get_reports_path(None, None, cfg['plan'], cfg['paths'], None, cfg, 's1', read_state),
                os.path.join(feature_root, 'reports').replace('\\', '/') + '/')
        finally:
            os.chdir(prev)

    def test_readonly_feature_first_plan_lookup_does_not_create_metadata(self):
        repo = mkdtemp('vd-readonly-feature-')
        self._cleanup(repo)
        git(repo, 'init', '-b', 'main')
        git(repo, 'checkout', '-b', 'feat/demo-work')
        cfg = {
            '_gitRoot': repo,
            'plan': {
                'reportsDir': 'reports',
                'resolution': {
                    'order': ['branch'],
                    'branchPattern': '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)',
                },
            },
            'paths': {'umbrella': '.workbench', 'layout': 'feature-first', 'plans': 'plans'},
        }

        plans_dir = paths.get_plans_path(repo, cfg, 's1', lambda sid=None: None)
        self.assertTrue(plans_dir.endswith(os.path.join('.workbench', 'features', 'demo-work', 'plans')))
        self.assertFalse(os.path.exists(
            os.path.join(repo, '.workbench', 'features', 'demo-work', 'feature.json')))

        paths.get_plans_path(repo, cfg, 's2', lambda sid=None: None, {'readOnly': False})
        self.assertTrue(os.path.exists(
            os.path.join(repo, '.workbench', 'features', 'demo-work', 'feature.json')))

    def test_is_global_scratch_path_detects_only_global_scratch_subtree(self):
        repo = mkdtemp('vd-scratch-path-')
        self._cleanup(repo)
        git(repo, 'init', '-b', 'main')
        cfg = {'_gitRoot': repo, 'paths': {'umbrella': '.workbench', 'layout': 'feature-first'}}
        global_root = paths.get_global_path(repo, cfg)
        self.assertTrue(
            paths.is_global_scratch_path(os.path.join(global_root, 'scratch', 'reports'), repo, cfg))
        feature_path = os.path.join(os.path.dirname(global_root), 'features', 'some-feature', 'reports')
        self.assertFalse(paths.is_global_scratch_path(feature_path, repo, cfg))

    def test_compute_feature_id_strips_multi_segment_ticket_prefixes(self):
        self.assertEqual(
            paths.compute_feature_id('PROJ-SUB-123', 'proj-sub-123-manual-upload'),
            'proj-sub-123-manual-upload')
        self.assertEqual(
            paths.compute_feature_id('ELT-3316', '3316-manual-upload'),
            'elt-3316-manual-upload')

    def test_branch_plan_resolution_scans_session_feature_plans_dir(self):
        repo = mkdtemp('vd-branch-plan-')
        self._cleanup(repo)
        git(repo, 'init', '-b', 'main')
        git(repo, 'checkout', '-b', 'feat/demo-work')
        cfg = {
            '_gitRoot': repo,
            'plan': {
                'reportsDir': 'reports',
                'resolution': {
                    'order': ['branch'],
                    'branchPattern': '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)',
                },
            },
            'paths': {'umbrella': '.workbench', 'layout': 'feature-first', 'plans': 'plans'},
        }
        feature_root = os.path.join(realpath(repo), '.workbench', 'features', 'demo-feature')
        plan_dir = os.path.join(feature_root, 'plans', '260620-1200-demo-work')
        os.makedirs(plan_dir, exist_ok=True)

        resolved = paths.resolve_plan_path('s1', cfg, lambda sid=None: {'featureId': 'demo-feature'}, repo)
        self.assertEqual(resolved, {'path': plan_dir, 'resolvedBy': 'branch'})

    def test_linked_worktree_overlays_main_worktree_umbrella_layout(self):
        fake_home = mkdtemp('vd-home-')
        repo = mkdtemp('vd-main-')
        linked = os.path.join(tempfile.gettempdir(), 'vd-linked-%s-%s' % (os.getpid(), int(os.times()[4] * 1000)))
        self._cleanup(fake_home)
        self._cleanup(repo)
        self.addCleanup(shutil.rmtree, linked, ignore_errors=True)
        self.addCleanup(lambda: subprocess.run(['git', 'worktree', 'remove', '--force', linked],
                        cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        git(repo, 'init', '-b', 'main')
        git(repo, 'config', 'user.email', 't@t.t')
        git(repo, 'config', 'user.name', 't')
        git(repo, 'commit', '--allow-empty', '-m', 'init')
        git(repo, 'worktree', 'add', '-b', 'linked', linked)

        with open(os.path.join(repo, '.vd.json'), 'w') as f:
            f.write(json.dumps({
                'paths': {'umbrella': '.main-workbench', 'layout': 'feature-first', 'allowHomeRoot': True},
                'plan': {'ticketPrefixes': ['MAIN'],
                         'resolution': {'order': ['branch'], 'branchPattern': 'main/(.+)'}},
            }))
        with open(os.path.join(linked, '.vd.json'), 'w') as f:
            f.write(json.dumps({
                'paths': {'umbrella': '.linked-workbench', 'layout': 'type-first', 'allowHomeRoot': False},
                'plan': {'ticketPrefixes': ['LINKED'],
                         'resolution': {'order': ['session'], 'branchPattern': 'linked/(.+)'}},
            }))

        script = (
            "import os, sys, json\n"
            "sys.path.insert(0, os.environ['PYLIB'])\n"
            "import vd_config as c\n"
            "os.chdir(os.environ['BASE'])\n"
            "cfg = c.load_config()\n"
            "print(json.dumps({'paths': cfg['paths'], 'plan': cfg['plan']}))\n"
        )
        got = run_child(script, {'HOME': fake_home, 'USERPROFILE': fake_home, 'BASE': linked})

        self.assertEqual(got['paths']['umbrella'], '.main-workbench')
        self.assertEqual(got['paths']['layout'], 'feature-first')
        self.assertEqual(got['paths']['allowHomeRoot'], True)
        self.assertEqual(got['plan']['ticketPrefixes'], ['MAIN'])
        self.assertEqual(got['plan']['resolution']['order'], ['branch'])
        self.assertEqual(got['plan']['resolution']['branchPattern'], 'main/(.+)')

    def test_absolute_config_and_state_values_cannot_escape_anchor(self):
        # Node path.join concatenates absolute later segments; os.path.join resets.
        self.assertEqual(paths.node_join('/repo/.wb/features', '/outside'),
                         '/repo/.wb/features/outside')
        cfg = {'paths': {'plans': '/etc', 'docs': '/etc'}}
        self.assertEqual(paths.get_plans_path('/repo', cfg), '/repo/etc')
        self.assertEqual(paths.get_docs_path('/repo', cfg), '/repo/etc')
        ff_cfg = {'paths': {'umbrella': '.wb', 'layout': 'feature-first'},
                  '_gitRoot': '/repo'}
        root = paths.resolve_feature_root(
            ff_cfg, '/repo', 'sid', lambda sid: {'featureId': '/outside'}, {'readOnly': True})
        self.assertEqual(root, '/repo/.wb/features/outside')

    def test_regexes_are_ascii_like_js(self):
        self.assertEqual(paths.clean_slug('café-fix'), 'caf-fix')
        self.assertIsNone(paths.extract_issue_from_branch('gh٠١'))
        self.assertEqual(paths.extract_ticket_from_branch('feat/ELT-123-x', ['ELT']), 'ELT-123')


if __name__ == '__main__':
    unittest.main()
