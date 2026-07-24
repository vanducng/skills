#!/usr/bin/env python3
"""Integration test for the workbench lifecycle CLI.

Requires the control-plane libs (repo hooks/lib, else ~/.claude/.codex). The
plain `wb` helper scrubs VD_SESSION_ID so branch resolution stays deterministic
regardless of the ambient session; `wb_env` sets it explicitly when needed.
Run: python3 skills/workbench/scripts/test_workbench.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time

_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
WB = os.path.join(_SCRIPT_DIR, 'workbench.py')
_CANDIDATES = [
    os.path.normpath(os.path.join(_SCRIPT_DIR, '..', '..', '..', 'hooks', 'lib')),
    os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'lib'),
    os.path.join(os.path.expanduser('~'), '.codex', 'hooks', 'lib'),
]
_LIB = next((d for d in _CANDIDATES if os.path.isdir(d)), _CANDIDATES[1])
sys.path.insert(0, _LIB)
import vd_paths as P  # noqa: E402
import vd_state as S  # noqa: E402

_pass = 0
_fail = 0


def ok(name, cond):
    global _pass, _fail
    if cond:
        _pass += 1
        print('  ✓', name)
    else:
        _fail += 1
        print('  ✗', name)


def _clean_env(extra=None):
    e = dict(os.environ)
    e.pop('VD_SESSION_ID', None)
    if extra:
        e.update(extra)
    return e


def git(cwd, *a):
    subprocess.run(['git', *a], cwd=cwd, stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def _run(cwd, env, a):
    r = subprocess.run([sys.executable, WB, *a], cwd=cwd, env=env,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    text = (r.stdout or b'').decode('utf-8', 'replace')
    if r.returncode == 0:
        return text
    return text + (r.stderr or b'').decode('utf-8', 'replace')


def wb(cwd, *a):
    return _run(cwd, _clean_env(), a)


def wb_env(cwd, env, *a):
    return _run(cwd, _clean_env(env), a)


def cleanup_session(sid):
    session_path = S.get_session_temp_path(sid)
    for p in (session_path, session_path + '.lock'):
        try:
            os.unlink(p)
        except Exception:
            pass
    try:
        d = os.path.dirname(session_path)
        base = os.path.basename(session_path)
        for name in os.listdir(d):
            if name.startswith(base + '.') and name.endswith('.json'):
                try:
                    os.unlink(os.path.join(d, name))
                except Exception:
                    pass
    except Exception:
        pass


def repo(branch):
    d = tempfile.mkdtemp(prefix='wbt-')
    git(d, 'init', '-q')
    git(d, 'checkout', '-q', '-b', branch)
    with open(os.path.join(d, '.vd.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps({'paths': {'umbrella': '.workbench', 'layout': 'feature-first'}}))
    return d


def meta(d, feature_id):
    try:
        with open(os.path.join(d, '.workbench', 'features', feature_id, 'feature.json'),
                  'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


print('new - branch-derived:')
d = repo('feat/ELT-3316-manual-upload')
wb(d, 'new')
m = meta(d, 'elt-3316-manual-upload')
ok('creates feature from branch', bool(m))
ok('feature.json ticket = ELT-3316', bool(m) and m.get('ticket') == 'ELT-3316')
ok('stored slug matches hooks slugFromBranch (parity)',
   bool(m) and m.get('slug') == P.slug_from_branch('feat/ELT-3316-manual-upload'))
ok('5 type subdirs created',
   all(os.path.exists(os.path.join(d, '.workbench', 'features', 'elt-3316-manual-upload', t))
       for t in ['plans', 'reports', 'visuals', 'journals', 'state']))

print('new - user slug (H2: cleaned/lowercased + parity):')
d = repo('trunk')
wb(d, 'new', 'My Cool Feature')
m = meta(d, 'my-cool-feature')
ok('user slug → lowercased cleaned id', bool(m))
ok('stored slug == branch-resolved slug for feat/my-cool-feature',
   bool(m) and m.get('slug') == P.slug_from_branch('feat/my-cool-feature'))

print('new - idempotent:')
out2 = wb(d, 'new', 'My Cool Feature')
ok('second new says exists (no dup)', bool(re.search(r'exists: features/my-cool-feature', out2)))
ok('exactly one dir', len(os.listdir(os.path.join(d, '.workbench', 'features'))) == 1)

print('parseArgs (H1: positional after boolean flag):')
d = repo('trunk')
wb(d, 'new', '--from-scratch', 'other-feature')
ok('slug not swallowed by --from-scratch',
   os.path.exists(os.path.join(d, '.workbench', 'features', 'other-feature')))

print('list / archive / restore:')
d = repo('feat/ELT-1-alpha')
wb(d, 'new')
wb(d, 'new', 'beta')
ok('list --status all shows both',
   (lambda o: bool(re.search(r'elt-1-alpha', o)) and bool(re.search(r'beta', o)))(wb(d, 'list', '--status', 'all')))
wb(d, 'archive', 'beta')
ok('archived appears under archived', bool(re.search(r'beta', wb(d, 'list', '--status', 'archived'))))
ok('beta moved to _archive', os.path.exists(os.path.join(d, '.workbench', '_archive', 'beta')))
ok('active list excludes archived', not re.search(r'beta', wb(d, 'list')))
wb(d, 'restore', 'beta')
ok('restored back to features', os.path.exists(os.path.join(d, '.workbench', 'features', 'beta')))

print('resolve / reindex / gc:')
d = repo('feat/ELT-9-gamma')
wb(d, 'new')
r = json.loads(wb(d, 'resolve', '--json'))
ok('resolve --json feature', r['feature'] == 'elt-9-gamma')
ok('resolve reports path', r['reports'].endswith(os.path.join('features', 'elt-9-gamma', 'reports')))
wb(d, 'new', 'session-feature')
sid = 'wbt-%s-%s' % (os.getpid(), int(time.time() * 1000))
ok('session state write succeeds', bool(S.update_session_state(sid, {'featureId': 'session-feature'})))
sr = {}
raw_resolve = ''
try:
    raw_resolve = wb_env(d, {'VD_SESSION_ID': sid}, 'resolve', '--json')
    sr = json.loads(raw_resolve)
except Exception:
    sys.stderr.write(raw_resolve)
    cleanup_session(sid)
    raise
finally:
    cleanup_session(sid)
ok('resolve honors session feature', sr.get('feature') == 'session-feature')
wb(d, 'reindex')
ok('reindex writes INDEX.md', os.path.exists(os.path.join(d, '.workbench', 'INDEX.md')))
os.makedirs(os.path.join(d, '.workbench', 'tmp'), exist_ok=True)
ok('gc dry-run lists tmp, does not delete',
   (lambda o: bool(re.search(r'would remove', o)) and os.path.exists(os.path.join(d, '.workbench', 'tmp')))(wb(d, 'gc')))
wb(d, 'gc', '--force')
ok('gc --force deletes tmp', not os.path.exists(os.path.join(d, '.workbench', 'tmp')))

print('absolute feature ids stay under the umbrella:')
ok('status /tmp errors instead of reading /tmp', 'no feature' in wb(d, 'status', '/tmp'))
ok('archive /tmp errors', 'no active feature' in wb(d, 'archive', '/tmp'))

print('\n%s tests: %s passed, %s failed' % (_pass + _fail, _pass, _fail))
sys.exit(1 if _fail else 0)
