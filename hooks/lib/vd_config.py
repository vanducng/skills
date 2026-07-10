"""vd_config - Three-layer config loader: defaults ← global ← project-local.

Local config resolves via git-root (not a literal unexpanded HOME string).
paths.umbrella (default null) opts a repo into the .workbench/ layout.
Config file: .vd.json only. A lingering legacy .ck.json raises a migration
error (run the cktovd skill) — vd no longer reads .ck.json.
"""

import copy
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vd_paths import get_main_worktree_root, is_home_dir  # noqa: E402

DEFAULT_CONFIG = {
    'plan': {
        'namingFormat': '{date}-{issue}-{slug}',
        'dateFormat': 'YYMMDD-HHmm',
        'issuePrefix': None,
        'ticketPrefixes': ['ELT', 'GH', 'PROJ'],
        'reportsDir': 'reports',
        'resolution': {
            'order': ['session', 'branch'],
            'branchPattern': '(?:feat|fix|chore|refactor|docs)/(?:[^/]+/)?(.+)',
        },
        'validation': {
            'mode': 'prompt',
            'minQuestions': 3,
            'maxQuestions': 8,
            'focusAreas': ['assumptions', 'risks', 'tradeoffs', 'architecture'],
        },
    },
    'paths': {
        'docs': 'docs',
        'plans': 'plans',
        # Umbrella: null = legacy CWD-anchored layout.
        # Set to a relative name (e.g. ".workbench") in <git-root>/.vd.json to opt in.
        'umbrella': None,
        # Layout: 'type-first' (flat type siblings) | 'feature-first' (per-feature folders).
        'layout': 'type-first',
        'allowHomeRoot': False,
        'visuals': 'visuals',
        'journals': 'journals',
        'state': 'state',
    },
    'locale': {'thinkingLanguage': None, 'responseLanguage': None},
    'trust': {'passphrase': None, 'enabled': False},
    'project': {'type': 'auto', 'packageManager': 'auto', 'framework': 'auto'},
    'codingLevel': -1,
    'assertions': [],
    'hooks': {
        'session-init': True,
        'subagent-init': True,
        'dev-rules-reminder': True,
        'session-state': True,
    },
}


def layer_configs(base, override):
    """Layer two config dicts, override wins. Arrays replace; empty dict inherits; scalars override."""
    if not isinstance(override, dict):
        return base
    if not isinstance(base, dict):
        return override

    out = dict(base)
    for k, ov in override.items():
        if isinstance(ov, list):
            out[k] = list(ov)  # replace, never merge
        elif isinstance(ov, dict):
            # Empty object means "inherit from base" — skip
            if not ov:
                continue
            out[k] = layer_configs(base.get(k) or {}, ov)
        else:
            out[k] = ov  # scalar: override wins
    return out


def read_json(file_path):
    try:
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def get_git_root(cwd=None):
    try:
        r = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip()
    except Exception:
        return None


def sanitize_umbrella(raw, git_root):
    """Must be a relative, traversal-free name that stays inside the repo; else None (disabled)."""
    if not raw or not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    if os.path.isabs(trimmed):
        return None
    parts = re.split(r'[/\\]', trimmed)
    if any(p == '..' or p == '' for p in parts):
        return None
    if git_root:
        resolved = os.path.abspath(os.path.join(git_root, trimmed))
        if not resolved.startswith(git_root + os.sep) and resolved != git_root:
            return None
    return trimmed


def assert_migrated(vd_path, ck_path):
    """Raise if a legacy .ck.json lingers without its .vd.json."""
    if not ck_path:
        return
    if not os.path.exists(vd_path) and os.path.exists(ck_path):
        raise RuntimeError(
            'Legacy %s found at %s but no %s. '
            'vd no longer reads .ck.json — run the cktovd skill, or rename it to %s.'
            % (os.path.basename(ck_path), ck_path, os.path.basename(vd_path), os.path.basename(vd_path))
        )


def get_main_worktree_config_details(cwd=None):
    """Read the MAIN worktree's .vd.json (or None). Layout-determining keys come from here
    so linked worktrees can't disagree about artifact resolution."""
    main_root = get_main_worktree_root(cwd)
    if not main_root:
        return None
    config = read_json(os.path.join(main_root, '.vd.json'))
    allow_home = (isinstance(config, dict) and isinstance(config.get('paths'), dict)
                  and config['paths'].get('allowHomeRoot') is True)
    if is_home_dir(main_root) and not allow_home:
        return None
    return {'root': main_root, 'config': config}


def get_main_worktree_config(cwd=None):
    """Public compatibility helper: returns only the main worktree .vd.json payload."""
    details = get_main_worktree_config_details(cwd)
    return details['config'] if details else None


def apply_main_worktree_layout(merged, main_cfg):
    """Overlay repo-wide layout/resolution keys from the main worktree config."""
    if not main_cfg:
        return merged
    out = dict(merged)
    paths_cfg = main_cfg.get('paths') if isinstance(main_cfg, dict) else None
    if paths_cfg:
        out['paths'] = dict(merged.get('paths') or {})
        if isinstance(paths_cfg, dict):
            if isinstance(paths_cfg.get('umbrella'), str):
                out['paths']['umbrella'] = paths_cfg['umbrella']
            if isinstance(paths_cfg.get('layout'), str):
                out['paths']['layout'] = paths_cfg['layout']
            if isinstance(paths_cfg.get('allowHomeRoot'), bool):
                out['paths']['allowHomeRoot'] = paths_cfg['allowHomeRoot']
    plan_cfg = main_cfg.get('plan') if isinstance(main_cfg, dict) else None
    if plan_cfg:
        out['plan'] = dict(merged.get('plan') or {})
        if isinstance(plan_cfg, dict):
            if isinstance(plan_cfg.get('ticketPrefixes'), list):
                out['plan']['ticketPrefixes'] = list(plan_cfg['ticketPrefixes'])
            if isinstance(plan_cfg.get('resolution'), dict):
                out['plan']['resolution'] = layer_configs(
                    (merged.get('plan') or {}).get('resolution') or {}, plan_cfg['resolution'])
    return out


def load_config():
    """DEFAULT ← global (~/.claude/.vd.json) ← project (<git-root>/.vd.json), then overlay
    repo-wide layout/resolution keys from the MAIN worktree. Falls back to defaults on any error."""
    global_path = os.path.join(os.path.expanduser('~'), '.claude', '.vd.json')
    git_root = get_git_root(os.getcwd())
    local_path = os.path.join(git_root, '.vd.json') if git_root else None

    # No silent .ck.json fallback — raise a migration error if a legacy file lingers.
    assert_migrated(global_path, os.path.join(os.path.expanduser('~'), '.claude', '.ck.json'))
    if git_root:
        assert_migrated(local_path, os.path.join(git_root, '.ck.json'))

    global_cfg = read_json(global_path)
    local_cfg = read_json(local_path) if local_path else None
    git_metadata = os.path.join(git_root, '.git') if git_root else None
    git_dir_is_file = False
    try:
        git_dir_is_file = bool(git_metadata and os.path.exists(git_metadata)
                               and not os.path.isdir(git_metadata))
    except Exception:
        pass

    try:
        merged = layer_configs({}, copy.deepcopy(DEFAULT_CONFIG))
        umbrella_git_root = git_root
        if global_cfg:
            merged = layer_configs(merged, global_cfg)
        if local_cfg:
            merged = layer_configs(merged, local_cfg)
        # Keep this merge path even when global/local configs are absent: linked
        # worktrees still need the main checkout's layout overlay.
        if git_dir_is_file:
            main_worktree = get_main_worktree_config_details(os.getcwd())
            merged = apply_main_worktree_layout(merged, main_worktree['config'] if main_worktree else None)
            if main_worktree:
                umbrella_git_root = main_worktree['root']
            # If main_worktree is None, no safe main root exists (e.g. a stray HOME repo);
            # keep the local root so sanitize_umbrella preserves the same guard. That
            # fallback makes artifacts worktree-local instead of shared.
        return build_result(merged, git_root, umbrella_git_root)
    except Exception:
        # DEFAULT_CONFIG has umbrella None, so umbrella_git_root is irrelevant here.
        return build_result(layer_configs({}, copy.deepcopy(DEFAULT_CONFIG)), git_root, git_root)


def build_result(merged, git_root, umbrella_git_root):
    defaults = copy.deepcopy(DEFAULT_CONFIG)
    raw_paths = merged.get('paths') or defaults['paths']
    if not isinstance(raw_paths, dict):
        raw_paths = {}
    umbrella = sanitize_umbrella(raw_paths.get('umbrella'), umbrella_git_root or git_root or None)
    coding_level = merged.get('codingLevel')

    return {
        'plan': merged.get('plan') or defaults['plan'],
        'paths': {
            'docs': raw_paths.get('docs') or defaults['paths']['docs'],
            'plans': raw_paths.get('plans') or defaults['paths']['plans'],
            'umbrella': umbrella,
            'layout': 'feature-first' if raw_paths.get('layout') == 'feature-first' else 'type-first',
            'allowHomeRoot': raw_paths.get('allowHomeRoot') is True,
            'visuals': raw_paths.get('visuals') or defaults['paths']['visuals'],
            'journals': raw_paths.get('journals') or defaults['paths']['journals'],
            'state': raw_paths.get('state') or defaults['paths']['state'],
        },
        'locale': merged.get('locale') or defaults['locale'],
        'trust': merged.get('trust') or defaults['trust'],
        'project': merged.get('project') or defaults['project'],
        'codingLevel': -1 if coding_level is None else coding_level,
        'assertions': merged.get('assertions') or [],
        'hooks': merged.get('hooks') or defaults['hooks'],
        'subagent': merged.get('subagent') or None,
        # Expose resolved gitRoot so hooks don't need to re-run git
        '_gitRoot': git_root or None,
    }
