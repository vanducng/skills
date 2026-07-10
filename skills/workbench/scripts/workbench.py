#!/usr/bin/env python3
"""workbench - lifecycle CLI for the feature-first .workbench umbrella.

Reuses the control-plane libs (repo hooks/lib, else ~/.claude or ~/.codex) so the
id it creates is exactly the id the hooks resolve. Owns the WRITE path
(create/archive/gc); hooks own the read-path resolution.
"""

import errno
import json
import os
import re
import shutil
import sys
import time

_SCRIPT = os.path.realpath(__file__)
_CANDIDATES = [
    os.path.normpath(os.path.join(_SCRIPT, '..', '..', '..', '..', 'hooks', 'lib')),
    os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'lib'),
    os.path.join(os.path.expanduser('~'), '.codex', 'hooks', 'lib'),
]
_LIB = next((d for d in _CANDIDATES if os.path.isdir(d)), None)
if not _LIB:
    sys.stderr.write('workbench: control-plane libs not found (looked in %s). Run `vd install hooks` first.\n'
                     % ', '.join(_CANDIDATES))
    sys.exit(2)
sys.path.insert(0, _LIB)
import vd_config  # noqa: E402
import vd_paths as P  # noqa: E402
import vd_state as state  # noqa: E402

TYPES = ['plans', 'reports', 'visuals', 'journals', 'state']
BOOLEAN_FLAGS = {'from-scratch', 'json', 'force'}


def out(msg):
    print(msg, flush=True)


def err(msg):
    print(msg, file=sys.stderr, flush=True)


def parse_args(argv):
    pos, flags = [], {}
    i, n = 0, len(argv)
    while i < n:
        a = argv[i]
        if a.startswith('--'):
            k = a[2:]
            if k not in BOOLEAN_FLAGS and i + 1 < n and not argv[i + 1].startswith('--'):
                i += 1
                flags[k] = argv[i]
            else:
                flags[k] = True
        else:
            pos.append(a)
        i += 1
    return {'pos': pos, 'flags': flags}


def ctx():
    cfg = vd_config.load_config()
    cwd = os.getcwd()
    umbrella = P.resolve_umbrella_root(cfg, cwd)
    if not umbrella:
        err('workbench: no .workbench umbrella for this repo. Set `paths.umbrella` in <git-root>/.vd.json.')
        sys.exit(2)
    return {
        'cfg': cfg, 'cwd': cwd, 'umbrella': umbrella,
        'featuresDir': os.path.join(umbrella, 'features'),
        'archiveDir': os.path.join(umbrella, '_archive'),
        'globalDir': os.path.join(umbrella, '_global'),
        'unsortedDir': os.path.join(umbrella, '_unsorted'),
    }


def read_meta(dir_path):
    try:
        with open(os.path.join(dir_path, 'feature.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def write_meta(dir_path, meta):
    os.makedirs(dir_path, exist_ok=True)
    tmp = os.path.join(dir_path, '.feature.%s.tmp' % os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(json.dumps(meta, indent=2))
    os.rename(tmp, os.path.join(dir_path, 'feature.json'))


def now_iso():
    now = time.gmtime()
    return '%04d-%02d-%02dT%02d:%02d:%02d.%03dZ' % (
        now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec,
        int(time.time() * 1000) % 1000)


def git_branch(cwd):
    try:
        return P.get_git_branch(cwd)
    except Exception:
        return None


def list_dirs(d):
    try:
        return [e.name for e in os.scandir(d) if e.is_dir(follow_symlinks=False)]
    except Exception:
        return []


def count_files(dir_path):
    total = [0]

    def walk(p):
        try:
            ents = list(os.scandir(p))
        except Exception:
            return
        for e in ents:
            fp = os.path.join(p, e.name)
            if e.is_dir(follow_symlinks=False):
                walk(fp)
            elif e.name != 'feature.json':
                total[0] += 1
    walk(dir_path)
    return total[0]


def set_session(feature_id):
    sid = os.environ.get('VD_SESSION_ID')
    if not sid:
        return False
    return state.update_session_state(sid, {'featureId': feature_id})


def warn_if_no_session(ok):
    if not ok:
        err('  (VD_SESSION_ID unset — feature not set as the session default)')


def cmd_new(args):
    pos, flags = args['pos'], args['flags']
    c = ctx()
    br = git_branch(c['cwd'])
    ticket = flags.get('ticket') or None
    # Normalize a user slug through the same cleaner the resolver uses, so a later
    # branch resolution matches feature.json.slug. A branch-derived slug already matches.
    slug = P.clean_slug(str(pos[0]).lower()) if (pos and pos[0]) else None
    if not slug and not ticket:
        ticket = P.extract_ticket_from_branch(br, c['cfg']['plan'].get('ticketPrefixes'))
        slug = P.slug_from_branch(br, (c['cfg']['plan'].get('resolution') or {}).get('branchPattern'))
    feature_id = P.compute_feature_id(ticket or None, slug or None)
    if not feature_id:
        err('workbench new: need a slug or --ticket (or run on a feat/* branch).')
        sys.exit(1)
    dir_path = os.path.join(c['featuresDir'], feature_id)
    if os.path.exists(os.path.join(dir_path, 'feature.json')):
        out('exists: features/%s — switching to it' % feature_id)
        warn_if_no_session(set_session(feature_id))
        return
    for t in TYPES:
        os.makedirs(os.path.join(dir_path, t), exist_ok=True)
    write_meta(dir_path, {
        'id': feature_id, 'ticket': ticket or None, 'slug': slug or None,
        'label': slug or feature_id, 'status': 'active', 'created': now_iso(),
        'parentId': flags.get('parent') or None, 'supersededBy': None,
        'relatedDocs': [], 'branches': [br] if br else [],
    })
    if flags.get('from-scratch'):
        scratch = os.path.join(c['globalDir'], 'scratch')
        try:
            entries = os.listdir(scratch)
        except Exception:
            entries = []
        for name in entries:
            try:
                os.rename(os.path.join(scratch, name), os.path.join(dir_path, 'state', name))
            except Exception as e:
                code = errno.errorcode.get(getattr(e, 'errno', None)) or str(e)
                err('  ! skipped scratch/%s: %s' % (name, code))
    out('created: features/%s/{%s}' % (feature_id, ','.join(TYPES)))
    warn_if_no_session(set_session(feature_id))


def cmd_resolve(args):
    flags = args['flags']
    c = ctx()
    ff = (c['cfg']['paths'].get('layout')) == 'feature-first'
    # resolve is a query/display command; keep feature resolution read-only.
    opts = {'readOnly': True}
    sid = os.environ.get('VD_SESSION_ID') or None
    state_cache = {}
    if sid:
        def read_state(session_id):
            key = session_id or ''
            if key not in state_cache:
                state_cache[key] = state.read_session_state(session_id)
            return state_cache[key]
    else:
        read_state = None
    root = P.resolve_feature_root(c['cfg'], c['cwd'], sid, read_state, opts) if ff else c['umbrella']
    rel_feature = os.path.relpath(root, c['featuresDir']) if (ff and root) else ''
    feature_id = None
    if rel_feature and rel_feature != '.' and not rel_feature.startswith('..') and not os.path.isabs(rel_feature):
        feature_id = rel_feature.split(os.sep)[0]
    result = {
        'layout': c['cfg']['paths'].get('layout') or 'type-first',
        'feature': feature_id, 'featureRoot': root if ff else None,
        'reports': os.path.join(root, 'reports'), 'plans': os.path.join(root, 'plans'),
        'visuals': os.path.join(root, 'visuals'), 'journals': os.path.join(root, 'journals'),
        'state': os.path.join(root, 'state'),
        'global': P.get_global_path(c['cwd'], c['cfg']), 'archive': P.get_archive_path(c['cwd'], c['cfg']),
    }
    if flags.get('json'):
        out(json.dumps(result, indent=2))
        return
    out('layout:  %s' % result['layout'])
    out('feature: %s' % (feature_id or '(none — no signal; artifacts → _global/scratch)'))
    for t in TYPES:
        out('  %-9s %s' % (t, result[t]))
    if not ff:
        out('note: repo is type-first — hooks use the flat layout; the above shows the would-be feature paths.')


def cmd_switch(args):
    pos = args['pos']
    c = ctx()
    key = pos[0] if pos else None
    if not key:
        err('workbench switch <id|ticket|slug>')
        sys.exit(1)
    match = None
    for d in list_dirs(c['featuresDir']):
        if d == key:
            match = d
            break
        m = read_meta(os.path.join(c['featuresDir'], d))
        if m and (m.get('ticket') == key or m.get('slug') == key
                  or (m.get('ticket') or '').lower() == key.lower()):
            match = d
            break
    if not match:
        err('workbench switch: no feature matching "%s". Try `workbench list`.' % key)
        sys.exit(1)
    if not set_session(match):
        err('workbench switch: VD_SESSION_ID not set; cannot set per-session feature.')
        sys.exit(1)
    out('switched session → features/%s' % match)


def cmd_list(args):
    flags = args['flags']
    c = ctx()
    want = flags.get('status') or 'active'
    rows = []
    for scope, d in [('active', c['featuresDir']), ('archived', c['archiveDir'])]:
        for feature_id in list_dirs(d):
            m = read_meta(os.path.join(d, feature_id)) or {}
            st = 'archived' if scope == 'archived' else (m.get('status') or 'active')
            if want != 'all' and want != st:
                continue
            rows.append({'id': feature_id, 'ticket': m.get('ticket') or '-', 'status': st,
                         'artifacts': count_files(os.path.join(d, feature_id)), 'label': m.get('label') or ''})
    if not rows:
        out('(no %s features)' % want)
        return
    out('FEATURE%sTICKET      STATUS    FILES' % (' ' * 34))
    for r in sorted(rows, key=lambda x: x['id']):
        out('%s %s %s %s' % (r['id'][:40].ljust(40), str(r['ticket']).ljust(11), r['status'].ljust(9), r['artifacts']))


def cmd_status(args):
    pos = args['pos']
    c = ctx()
    feature_id = (pos[0] if pos else None) or P.resolve_feature_id(c['cfg'], c['cwd'])
    if not feature_id:
        err('workbench status <id> (or run on a feature branch)')
        sys.exit(1)
    base = os.path.join(c['featuresDir'], feature_id)
    if not os.path.exists(base):
        base = os.path.join(c['archiveDir'], feature_id)
    if not os.path.exists(base):
        err('workbench status: no feature "%s"' % feature_id)
        sys.exit(1)
    m = read_meta(base) or {}
    out('feature: %s' % feature_id)
    out('ticket:  %s   status: %s   created: %s'
        % (m.get('ticket') or '-', m.get('status') or '?', m.get('created') or '?'))
    if m.get('supersededBy'):
        out('superseded-by: %s' % m['supersededBy'])
    if m.get('parentId'):
        out('parent: %s' % m['parentId'])
    for t in TYPES:
        n = count_files(os.path.join(base, t))
        if n:
            out('  %-9s %s file(s)' % (t, n))
    if isinstance(m.get('relatedDocs'), list) and m['relatedDocs']:
        out('relatedDocs: %s' % ', '.join(m['relatedDocs']))


def cmd_archive(args):
    pos, flags = args['pos'], args['flags']
    c = ctx()
    feature_id = pos[0] if pos else None
    if not feature_id:
        err('workbench archive <id> [--reason r] [--superseded-by id]')
        sys.exit(1)
    src = os.path.join(c['featuresDir'], feature_id)
    if not os.path.exists(src):
        err('workbench archive: no active feature "%s"' % feature_id)
        sys.exit(1)
    dst = os.path.join(c['archiveDir'], feature_id)
    if os.path.exists(dst):
        err('workbench archive: _archive/%s already exists' % feature_id)
        sys.exit(1)
    os.makedirs(c['archiveDir'], exist_ok=True)
    os.rename(src, dst)
    m = read_meta(dst) or {'id': feature_id}
    m['status'] = 'done'
    m['archivedAt'] = now_iso()
    if flags.get('reason'):
        m['reason'] = flags['reason']
    if flags.get('superseded-by'):
        m['supersededBy'] = flags['superseded-by']
    write_meta(dst, m)
    out('archived: features/%s → _archive/%s' % (feature_id, feature_id))


def cmd_restore(args):
    pos = args['pos']
    c = ctx()
    feature_id = pos[0] if pos else None
    src = os.path.join(c['archiveDir'], feature_id or '')
    if not feature_id or not os.path.exists(src):
        err('workbench restore <id>: no _archive/%s' % (feature_id if feature_id else 'undefined'))
        sys.exit(1)
    dst = os.path.join(c['featuresDir'], feature_id)
    if os.path.exists(dst):
        err('workbench restore: features/%s already exists' % feature_id)
        sys.exit(1)
    os.rename(src, dst)
    m = read_meta(dst) or {'id': feature_id}
    m['status'] = 'active'
    m.pop('archivedAt', None)
    write_meta(dst, m)
    out('restored: _archive/%s → features/%s' % (feature_id, feature_id))


def cmd_reindex(args):
    c = ctx()
    lines = ['# .workbench index', '', '_Regenerated by `workbench reindex`._', '']
    for title, d in [('## Active', c['featuresDir']), ('## Archived', c['archiveDir'])]:
        lines.append(title)
        lines.append('')
        ids = sorted(list_dirs(d))
        if not ids:
            lines.append('_(none)_')
            lines.append('')
        for feature_id in ids:
            m = read_meta(os.path.join(d, feature_id)) or {}
            lines.append('- **%s** — %s · %s · %s files'
                         % (feature_id, m.get('ticket') or 'no-ticket', m.get('status') or '?',
                            count_files(os.path.join(d, feature_id))))
        lines.append('')
    index_path = os.path.join(c['umbrella'], 'INDEX.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    out('wrote %s' % index_path)


def cmd_gc(args):
    flags = args['flags']
    c = ctx()
    force = bool(flags.get('force'))
    targets = []
    tmp = os.path.join(c['umbrella'], 'tmp')
    if os.path.exists(tmp):
        targets.append(tmp)

    # Scope *.pid/*.log sweep to ephemeral zones only — never features/ (a feature may keep a real .log).
    def find_junk(p):
        try:
            ents = list(os.scandir(p))
        except Exception:
            return
        for e in ents:
            fp = os.path.join(p, e.name)
            if e.is_dir(follow_symlinks=False):
                find_junk(fp)
            elif re.search(r'\.(pid|log)$', e.name):
                targets.append(fp)
    find_junk(c['globalDir'])
    if not targets:
        out('gc: nothing to sweep (no tmp/, *.pid, *.log).')
        return
    out('gc: %s:' % ('removing' if force else 'would remove (use --force)'))
    for t in targets:
        out('  %s' % os.path.relpath(t, c['umbrella']))
        if force:
            try:
                if os.path.isdir(t) and not os.path.islink(t):
                    shutil.rmtree(t)
                else:
                    os.remove(t)
            except Exception as e:
                err('  ! %s' % str(e))


def cmd_migrate(args):
    out('workbench migrate: delegates to the native migrator (Phase 4).')
    out('  vd migrate --dry-run   # classify + report')
    out('  vd migrate --apply     # snapshot, move, manifest (ask-first on real data)')
    out('  vd migrate --revert    # replay manifest in reverse')


def cmd_triage(args):
    c = ctx()
    ids = list_dirs(c['unsortedDir'])
    try:
        files = [n for n in os.listdir(c['unsortedDir']) if n not in ids]
    except Exception:
        files = []
    if not ids and not files:
        out('triage: _unsorted/ is empty.')
        return
    out('triage: items needing a home (assign with `workbench new` then move, or wait for `vd migrate`):')
    for n in sorted(ids + files):
        out('  _unsorted/%s' % n)


USAGE = """workbench <command>
  new [slug] [--ticket T] [--parent id] [--from-scratch]   create/switch a feature folder
  resolve [--json]                                         show the resolved feature + type paths
  switch <id|ticket|slug>                                  set this session's active feature
  list [--status active|done|archived|all]                list features (derived from feature.json)
  status [id]                                              detail for one feature
  archive <id> [--reason r] [--superseded-by id]          move feature → _archive
  restore <id>                                             move _archive → features
  reindex                                                  rebuild INDEX.md
  gc [--force]                                             sweep tmp/, *.pid, *.log (dry-run unless --force)
  triage                                                   list _unsorted/ items
  migrate [...]                                            pointer to `vd migrate` (Phase 4)"""

CMDS = {
    'new': cmd_new, 'resolve': cmd_resolve, 'switch': cmd_switch, 'list': cmd_list,
    'status': cmd_status, 'archive': cmd_archive, 'restore': cmd_restore,
    'reindex': cmd_reindex, 'gc': cmd_gc, 'migrate': cmd_migrate, 'triage': cmd_triage,
}


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else None
    if not cmd or cmd in ('-h', '--help') or cmd not in CMDS:
        print(USAGE)
        sys.exit(1 if (cmd and cmd not in CMDS) else 0)
    CMDS[cmd](parse_args(argv[1:]))


if __name__ == '__main__':
    main()
