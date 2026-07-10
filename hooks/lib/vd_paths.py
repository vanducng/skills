"""vd_paths - CWD-anchored path resolution, naming pattern, and plan-resolution helpers.

P3: when config.paths.umbrella is set, paths.plans/reports/visuals/journals/state
anchor to GIT-ROOT/<umbrella>/. Docs always stays repo-root (CWD-anchored).
When umbrella is null the behavior is byte-identical to P2.
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid
from collections import OrderedDict

CACHE_MAX = 1024
_MISSING = object()


def _cache_get(cache, key):
    if key not in cache:
        return _MISSING
    cache.move_to_end(key)
    return cache[key]


def _cache_set(cache, key, value):
    if key not in cache and len(cache) >= CACHE_MAX:
        cache.popitem(last=False)
    cache[key] = value
    cache.move_to_end(key)
    return value


def _get(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


# Memoize git lookups per (cwd, process) — one subprocess call max per hook invocation.
_git_root_cache = OrderedDict()
_git_branch_cache = OrderedDict()


def run_git(args, cwd=None):
    try:
        r = subprocess.run(
            ['git'] + list(args),
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip() or None
    except Exception:
        return None


def get_git_branch(cwd=None):
    key = cwd or os.getcwd()
    cached = _cache_get(_git_branch_cache, key)
    if cached is not _MISSING:
        return cached
    result = run_git(['branch', '--show-current'], cwd)
    return _cache_set(_git_branch_cache, key, result)


def get_git_root(cwd=None):
    key = cwd or os.getcwd()
    cached = _cache_get(_git_root_cache, key)
    if cached is not _MISSING:
        return cached
    result = run_git(['rev-parse', '--show-toplevel'], cwd)
    return _cache_set(_git_root_cache, key, result)


# The MAIN worktree root — always the first entry of `git worktree list`.
# In a normal checkout this equals get_git_root (byte-identical behavior); inside
# a LINKED worktree it points back to the main checkout, so agent artifacts
# (the .workbench umbrella) survive `git worktree remove` instead of dying with the tree.
_main_root_cache = OrderedDict()


def get_main_worktree_root(cwd=None):
    key = cwd or os.getcwd()
    cached = _cache_get(_main_root_cache, key)
    if cached is not _MISSING:
        return cached
    result = None
    out = run_git(['worktree', 'list', '--porcelain'], cwd)
    if out:
        # Porcelain blocks are blank-line separated; pick the first NON-bare
        # "worktree <path>" entry — a bare repo's first block is its .git dir.
        for block in out.split('\n\n'):
            lines = block.split('\n')
            wl = next((l for l in lines if l.startswith('worktree ')), None)
            if not wl or any(l.strip() == 'bare' for l in lines):
                continue
            result = wl[len('worktree '):].strip() or None
            break
    return _cache_set(_main_root_cache, key, result)


def realpath_safe(p):
    try:
        return os.path.realpath(p)
    except Exception:
        return os.path.abspath(p)


_home_realpath = _MISSING


def is_home_dir(p):
    global _home_realpath
    home = os.path.expanduser('~')
    if not p or not home:
        return False
    if _home_realpath is _MISSING:
        _home_realpath = realpath_safe(home)
    return realpath_safe(p) == _home_realpath


def strip_trailing(p):
    if not p or not isinstance(p, str):
        return None
    s = re.sub(r'[/\\]+$', '', p.strip())
    return s or None


def with_trailing_slash(p):
    s = p.replace('\\', '/')
    return s if s.endswith('/') else s + '/'


def node_join(*parts):
    # Node path.join semantics: an absolute later segment concatenates instead of
    # resetting the result (os.path.join would discard everything before it).
    filtered = [p for p in parts if p]
    if not filtered:
        return '.'
    return os.path.normpath('/'.join(filtered))


normalize_path = strip_trailing


def same_or_child_path(child, parent):
    c = strip_trailing(child)
    p = strip_trailing(parent)
    if not c or not p:
        return False
    cn = c.replace('\\', '/')
    pn = p.replace('\\', '/')
    if sys.platform == 'win32':
        cn = cn.lower()
        pn = pn.lower()
    return cn == pn or cn.startswith(pn + '/')


def resolve_umbrella_root(config, base_dir=None):
    umbrella = _get(config, 'paths', 'umbrella')
    if not umbrella:
        return None
    # Main worktree == local git-root in a normal checkout, the main checkout inside
    # a linked worktree. config._gitRoot (LOCAL root, used for branch-local docs) is
    # only a last-resort fallback. With NO git root anywhere, anchor at the working
    # dir so artifacts still land in .workbench/ instead of scattering to legacy plans/.
    git_root = (get_main_worktree_root(base_dir)
                or (config.get('_gitRoot') if isinstance(config, dict) else None)
                or get_git_root(base_dir)
                or base_dir or os.getcwd())
    # Stray-ancestor guard: a coincidental repo rooted at $HOME must not swallow
    # every project below it; anchor to the working dir instead.
    if (base_dir and not _get(config, 'paths', 'allowHomeRoot')
            and is_home_dir(git_root)
            and not is_home_dir(base_dir)):
        git_root = base_dir
    return os.path.join(git_root, umbrella)


def get_plans_path(base_dir, config, session_id=None, read_state=None, opts=None):
    feature_root = resolve_feature_root(config, base_dir, session_id, read_state, opts)
    if feature_root:
        return node_join(feature_root, strip_trailing(_get(config, 'paths', 'plans')) or 'plans')
    # Legacy: second arg was pathsConfig in P2 — accept both shapes
    paths_config = config.get('paths') if (isinstance(config, dict) and config.get('paths')) else config
    return node_join(base_dir, strip_trailing(_get(paths_config, 'plans')) or 'plans')


def get_docs_path(base_dir, config):
    # Docs are ALWAYS repo-root (CWD) anchored — never under umbrella/feature folders.
    paths_config = config.get('paths') if (isinstance(config, dict) and config.get('paths')) else config
    return node_join(base_dir, strip_trailing(_get(paths_config, 'docs')) or 'docs')


def get_visuals_path(base_dir, config, session_id=None, read_state=None, opts=None):
    feature_root = resolve_feature_root(config, base_dir, session_id, read_state, opts)
    name = strip_trailing(_get(config, 'paths', 'visuals')) or 'visuals'
    if feature_root:
        return node_join(feature_root, name)
    return node_join(base_dir, 'plans', name)


def get_journals_path(base_dir, config, session_id=None, read_state=None, opts=None):
    feature_root = resolve_feature_root(config, base_dir, session_id, read_state, opts)
    name = strip_trailing(_get(config, 'paths', 'journals')) or 'journals'
    if feature_root:
        return node_join(feature_root, name)
    return node_join(base_dir, 'plans', name)


def get_state_path(base_dir, config, session_id=None, read_state=None, opts=None):
    feature_root = resolve_feature_root(config, base_dir, session_id, read_state, opts)
    name = strip_trailing(_get(config, 'paths', 'state')) or 'state'
    if feature_root:
        return node_join(feature_root, name)
    return os.path.join(base_dir, 'plans', 'goals')


def get_reports_path(plan_path, resolved_by, plan_config, paths_config, anchor=None,
                     config=None, session_id=None, read_state=None, opts=None):
    # Two modes: anchor None → relative string ending '/'; anchor set → absolute, no slash.
    subdir = strip_trailing(_get(plan_config, 'reportsDir')) or 'reports'
    active_plan = strip_trailing(plan_path) if (plan_path and resolved_by == 'session') else None

    # Feature-first: reports nest in the FEATURE dir, unless a session-active plan
    # explicitly pins reports to that plan.
    if not active_plan and config and _get(config, 'paths', 'layout') == 'feature-first':
        feature_root = resolve_feature_root(config, anchor or os.getcwd(), session_id, read_state, opts)
        if feature_root:
            if not anchor:
                return with_trailing_slash(node_join(feature_root, subdir))
            return node_join(feature_root, subdir)

    # Session-active plan overrides everything
    if active_plan:
        reports_base = active_plan
    elif config:
        umbrella_root = resolve_umbrella_root(config, anchor or os.getcwd())
        if umbrella_root:
            # Umbrella: reports is a direct sibling of plans under the umbrella root.
            reports_leaf = subdir
            if not anchor:
                return with_trailing_slash(node_join(umbrella_root, reports_leaf))
            return node_join(umbrella_root, reports_leaf)
        reports_base = strip_trailing(_get(paths_config, 'plans')) or 'plans'
    else:
        reports_base = strip_trailing(_get(paths_config, 'plans')) or 'plans'

    if not anchor:
        return with_trailing_slash(node_join(reports_base, subdir))

    # Absolute mode: isabs guard prevents double-anchoring
    if os.path.isabs(reports_base):
        return node_join(reports_base, subdir)
    return node_join(anchor, reports_base, subdir)


def format_date(fmt):
    now = time.localtime()
    substitutions = [
        # Longest tokens first so YYYY isn't partially consumed by YY
        ('YYYY', str(now.tm_year)),
        ('YY', str(now.tm_year)[-2:]),
        ('MM', '%02d' % now.tm_mon),
        ('DD', '%02d' % now.tm_mday),
        ('HH', '%02d' % now.tm_hour),
        ('mm', '%02d' % now.tm_min),
        ('ss', '%02d' % now.tm_sec),
    ]
    result = fmt
    for tok, val in substitutions:
        result = result.replace(tok, val)
    return result


def extract_issue_from_branch(branch):
    if not branch:
        return None
    attempts = [
        (r'(?:issue|gh|fix|feat|bug)[/-]?(\d+)', re.IGNORECASE | re.ASCII),
        (r'[/-](\d+)[/-]', re.ASCII),
        (r'#(\d+)', re.ASCII),
    ]
    for pattern, flags in attempts:
        hit = re.search(pattern, branch, flags)
        if hit:
            return hit.group(1)
    return None


def resolve_naming_pattern(plan_config, git_branch=None):
    formatted_date = format_date(plan_config['dateFormat'])
    issue_num = extract_issue_from_branch(git_branch)
    qualified_issue = ('%s%s' % (plan_config.get('issuePrefix'), issue_num)
                       if issue_num and plan_config.get('issuePrefix') else None)

    pat = plan_config['namingFormat'].replace('{date}', formatted_date)

    if qualified_issue:
        pat = pat.replace('{issue}', qualified_issue)
    else:
        pat = re.sub(r'-?\{issue\}-?', '-', pat, count=1)
        pat = re.sub(r'--+', '-', pat)

    pat = re.sub(r'^-+', '', pat)
    pat = re.sub(r'-+$', '', pat)
    pat = re.sub(r'-+(\{slug\})', r'-\1', pat)
    pat = re.sub(r'(\{slug\})-+', r'\1-', pat)
    pat = re.sub(r'--+', '-', pat)
    return pat


def clean_slug(raw):
    if not raw:
        return ''
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '', raw)
    s = re.sub(r'[^a-z0-9-]', '-', s, flags=re.IGNORECASE | re.ASCII)
    s = re.sub(r'-+', '-', s)
    s = re.sub(r'^-+|-+$', '', s)
    return s[:100]


def escape_re(s):
    return re.escape(str(s))


def slug_from_branch(branch, pattern=None):
    if not branch:
        return None
    src = pattern if pattern else r'(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)'
    m = re.search(src, branch, re.ASCII)
    return clean_slug(m.group(1)) if m else None


def plan_dir_slug(name):
    """Strip a leading `YYYYMMDD-HHMM-` or `YYMMDD-HHMM-` date prefix from a plan dir name."""
    return re.sub(r'^\d{6,8}-\d{4}-', '', name, count=1)


def resolve_plan_path(session_id, config, read_state, base_dir=None):
    base_dir = base_dir or os.getcwd()
    resolution = _get(config, 'plan', 'resolution') or {}
    order = resolution.get('order') or ['session', 'branch']
    state_box = {'loaded': False, 'value': None}

    def get_state():
        if not state_box['loaded']:
            state_box['value'] = read_state(session_id) if read_state else None
            state_box['loaded'] = True
        return state_box['value']

    read_state_once = (lambda _sid: get_state()) if read_state else None

    for step in order:
        if step == 'session':
            state = get_state()
            if _get(state, 'activePlan'):
                resolved = state['activePlan']
                if not os.path.isabs(resolved) and state.get('sessionOrigin'):
                    resolved = os.path.join(state['sessionOrigin'], resolved)
                return {'path': resolved, 'resolvedBy': 'session'}
        elif step == 'branch':
            try:
                branch = get_git_branch(base_dir)
                slug = slug_from_branch(branch, resolution.get('branchPattern'))
                if not slug:
                    continue
                # Anchor to the umbrella/main-worktree plans dir — cwd-relative silently
                # no-op'd inside linked worktrees. readOnly=True prevents ensureFeatureMeta
                # writes during plan resolution; read_state must stay a pure reader or
                # this chain could recurse.
                plans_dir = get_plans_path(base_dir, config, session_id, read_state_once, {'readOnly': True})
                if not os.path.exists(plans_dir):
                    continue
                dirs = [e for e in os.scandir(plans_dir) if e.is_dir()]
                # Prefer an EXACT slug match; fall back to substring only when unambiguous.
                # On >1 candidate, REFUSE — matches[last] silently mis-converged.
                exact = [e for e in dirs if plan_dir_slug(e.name) == slug]
                substr = [e for e in dirs if slug in e.name]
                ambiguous = len(exact) > 1 or (len(exact) == 0 and len(substr) > 1)
                if ambiguous:
                    sys.stderr.write('[paths] ambiguous branch plan resolution for slug "%s" in %s; skipping branch fallback\n' % (slug, plans_dir))
                    continue
                pick = exact[0] if len(exact) == 1 else (substr[0] if len(substr) == 1 else None)
                if pick:
                    return {'path': os.path.join(plans_dir, pick.name), 'resolvedBy': 'branch'}
            except Exception:
                pass
    return {'path': None, 'resolvedBy': None}


def extract_task_list_id(resolved):
    """Task list ID = plan dir basename, only for session-active plans."""
    if not resolved or resolved.get('resolvedBy') != 'session' or not resolved.get('path'):
        return None
    return os.path.basename(resolved['path'])


# ── feature-first resolution (gated on config.paths.layout == 'feature-first') ──

def extract_ticket_from_branch(branch, prefixes=None):
    """Prefix-preserving ticket extractor: `feat/ELT-3316-x` → `ELT-3316`; `gh3251` → `GH-3251`."""
    if not branch:
        return None
    lst = prefixes if (isinstance(prefixes, list) and prefixes) else ['ELT', 'GH', 'PROJ']
    pattern = r'\b(' + '|'.join(escape_re(p) for p in lst) + r')-?(\d+)\b'
    m = re.search(pattern, branch, re.IGNORECASE | re.ASCII)
    return '%s-%s' % (m.group(1).upper(), m.group(2)) if m else None


def compute_feature_id(ticket, slug):
    """Feature id from `{ticket}-{slug}` or `{slug}`; strips a leading duplicate ticket from slug."""
    if ticket:
        dash_idx = ticket.rfind('-')
        pre = ticket[:dash_idx] if dash_idx >= 0 else ticket
        num = ticket[dash_idx + 1:] if dash_idx >= 0 else ''
        if num:
            ticket_prefix = r'^(?:' + escape_re(pre) + r'-?)?' + escape_re(num) + r'-?'
        else:
            ticket_prefix = r'^' + escape_re(pre) + r'-?'
        desc = re.sub(ticket_prefix, '', slug, count=1, flags=re.IGNORECASE) if slug else ''
        return clean_slug(('%s-%s' % (ticket, desc) if desc else ticket).lower())
    if slug:
        return clean_slug(slug.lower())  # lowercase for parity with the ticket branch
    return None


_feature_find_cache = OrderedDict()


def find_feature(features_dir, ticket, slug):
    """Scan features/<id>/feature.json once; return a unique ticket match, then unique slug match."""
    try:
        st = os.stat(features_dir)
        dir_stamp = '%s:%s' % (st.st_mtime * 1000, st.st_size)
    except Exception:
        return None
    cache_key = '%s|%s|%s|%s' % (features_dir, dir_stamp, ticket or '', slug or '')
    cached = _cache_get(_feature_find_cache, cache_key)
    if cached is not _MISSING:
        return cached

    try:
        dirs = [e for e in os.scandir(features_dir) if e.is_dir()]
    except Exception:
        return None

    ticket_hits = []
    slug_hits = []
    for d in dirs:
        try:
            with open(os.path.join(features_dir, d.name, 'feature.json'), 'r', encoding='utf-8') as f:
                meta = json.load(f)
            if ticket and isinstance(meta, dict) and meta.get('ticket') == ticket:
                ticket_hits.append(d.name)
            if slug and isinstance(meta, dict) and meta.get('slug') == slug:
                slug_hits.append(d.name)
        except Exception:
            pass  # missing/invalid feature.json — skip
    found = (ticket_hits[0] if len(ticket_hits) == 1
             else slug_hits[0] if len(slug_hits) == 1
             else None)
    return _cache_set(_feature_find_cache, cache_key, found)


def cleanup_stale_feature_temps(dir_path, older_than_ms):
    """Remove orphaned feature.json temp files from interrupted metadata writes."""
    try:
        entries = list(os.scandir(dir_path))
    except Exception:
        return
    cutoff = time.time() * 1000 - older_than_ms
    for e in entries:
        if not e.is_file() or not e.name.startswith('feature.json.') or not e.name.endswith('.tmp'):
            continue
        p = os.path.join(dir_path, e.name)
        try:
            st = os.stat(p)
            if st.st_mtime * 1000 < cutoff:
                os.unlink(p)
        except Exception:
            pass


def ensure_feature_meta(features_dir, feature_id, meta):
    """Create features/<id>/feature.json if absent. Idempotent, atomic (rename), best-effort."""
    dir_path = os.path.join(features_dir, feature_id)
    meta_path = os.path.join(dir_path, 'feature.json')
    if os.path.exists(meta_path):
        return
    tmp = None
    try:
        os.makedirs(dir_path, exist_ok=True)
        cleanup_stale_feature_temps(dir_path, 60 * 60 * 1000)
        tmp = '%s.%s.%s.%s.tmp' % (meta_path, os.getpid(), int(time.time() * 1000), uuid.uuid4().hex)
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(json.dumps(meta, indent=2))
        # First committed writer wins; losers are ignored.
        os.rename(tmp, meta_path)
        tmp = None
    except Exception as e:
        # Never block resolution on a write failure.
        if os.environ.get('VD_DEBUG_PATHS'):
            sys.stderr.write('[paths] ensureFeatureMeta failed for %s: %s\n' % (feature_id, e))
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


# Per-process cache, keyed by session and branch, with a soft cap for long-lived hosts.
_feature_id_cache = OrderedDict()
# Keyed by the callable itself, not id(): a strong reference prevents the
# CPython id-reuse hazard where a new lambda at a dead lambda's address would
# hit its stale cached state (the .cjs WeakMap could only miss, never lie).
_feature_state_cache = OrderedDict()


def read_feature_state(read_state, session_id):
    if not read_state:
        return None
    try:
        by_session = _cache_get(_feature_state_cache, read_state)
    except TypeError:
        return read_state(session_id)
    if by_session is _MISSING:
        by_session = OrderedDict()
        _cache_set(_feature_state_cache, read_state, by_session)
    key = session_id or ''
    if key in by_session:
        return by_session[key]
    state = read_state(session_id)
    _cache_set(by_session, key, state)
    return state


def resolve_feature_id(config, base_dir=None, session_id=None, read_state=None, opts=None):
    """Resolve the feature id for the current context. Pure read except a one-time idempotent
    feature.json create on first strong-signal resolution (only with readOnly=False)."""
    base_dir = base_dir or os.getcwd()
    umbrella_root = resolve_umbrella_root(config, base_dir)
    if not umbrella_root:
        return None
    state = read_feature_state(read_state, session_id)
    read_only = not (isinstance(opts, dict) and opts.get('readOnly') is False)

    if state and isinstance(state.get('featureId'), str) and state.get('featureId'):
        state_key = '%s|%s|%s|state|%s|ro:%s' % (
            umbrella_root, session_id or '', state['featureId'],
            _get(state, 'activePlan') or '', '1' if read_only else '0')
        cached = _cache_get(_feature_id_cache, state_key)
        if cached is not _MISSING:
            return cached
        return _cache_set(_feature_id_cache, state_key, state['featureId'])

    branch = get_git_branch(base_dir)
    cache_key = '%s|%s|%s|%s|%s|ro:%s' % (
        umbrella_root, session_id or '', _get(state, 'featureId') or '',
        branch or '', _get(state, 'activePlan') or '', '1' if read_only else '0')
    cached = _cache_get(_feature_id_cache, cache_key)
    if cached is not _MISSING:
        return cached

    features_dir = os.path.join(umbrella_root, 'features')

    def remember(fid):
        return _cache_set(_feature_id_cache, cache_key, fid)

    # branch signals
    ticket = extract_ticket_from_branch(branch, _get(config, 'plan', 'ticketPrefixes'))
    slug = slug_from_branch(branch, _get(config, 'plan', 'resolution', 'branchPattern'))

    # 2-3. match an EXISTING feature (survives slug drift / relabel)
    existing = find_feature(features_dir, ticket, slug)
    if existing:
        return remember(existing)

    # 4. strong branch signal, no existing match → compute id + create the anchor (idempotent)
    computed = compute_feature_id(ticket, slug)
    if computed:
        if not read_only:
            now = time.gmtime()
            created = '%04d-%02d-%02dT%02d:%02d:%02d.%03dZ' % (
                now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec,
                int(time.time() * 1000) % 1000)
            ensure_feature_meta(features_dir, computed, {
                'id': computed, 'ticket': ticket or None, 'slug': slug or None,
                'label': slug or computed,
                'status': 'active', 'created': created, 'parentId': None,
                'supersededBy': None, 'relatedDocs': [], 'branches': [branch] if branch else [],
            })
        return remember(computed)

    # 5. session-active plan → its parent feature (plan path stored absolute in state)
    if state and state.get('activePlan'):
        p = state['activePlan']
        if not os.path.isabs(p) and state.get('sessionOrigin'):
            p = os.path.join(state['sessionOrigin'], p)
        seg = os.path.relpath(p, features_dir).split(os.sep)
        if seg and seg[0] and seg[0] != '.' and not seg[0].startswith('..'):
            return remember(seg[0])

    # 6. no signal
    return remember(None)


def resolve_feature_root(config, base_dir=None, session_id=None, read_state=None, opts=None):
    """Feature root: umbrella root verbatim when not feature-first; else features/<id> or _global/scratch."""
    base_dir = base_dir or os.getcwd()
    u = resolve_umbrella_root(config, base_dir)
    if not u or _get(config, 'paths', 'layout') != 'feature-first':
        return u
    fid = resolve_feature_id(config, base_dir, session_id, read_state, opts)
    return node_join(u, 'features', fid) if fid else os.path.join(u, '_global', 'scratch')


def get_global_path(base_dir, config):
    u = resolve_umbrella_root(config, base_dir)
    return os.path.join(u, '_global') if u else None


def get_archive_path(base_dir, config):
    u = resolve_umbrella_root(config, base_dir)
    return os.path.join(u, '_archive') if u else None


def is_global_scratch_path(candidate, base_dir, config):
    global_root = get_global_path(base_dir, config)
    return bool(global_root and same_or_child_path(candidate, os.path.join(global_root, 'scratch')))


def resolve_skills_venv(effective_cwd=None):
    """Check project-local then global ~/.claude for a skills venv python binary."""
    cfg_dir = '.claude'
    local_bin = os.path.join(effective_cwd or os.getcwd(), cfg_dir, 'skills', '.venv', 'bin', 'python3')
    global_bin = os.path.join(os.path.expanduser('~'), '.claude', 'skills', '.venv', 'bin', 'python3')
    if os.path.exists(local_bin):
        return '%s/skills/.venv/bin/python3' % cfg_dir
    if os.path.exists(global_bin):
        return '~/.claude/skills/.venv/bin/python3'
    return None
