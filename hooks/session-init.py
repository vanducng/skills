#!/usr/bin/env python3
"""session-init.py - VD-CLI clean-room SessionStart hook.

Emits all VD_* env vars to CLAUDE_ENV_FILE, writes per-session temp state,
and prints a context summary. Never throws (fail-open).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))

try:
    import json
    import platform
    import time

    import vd_config
    import vd_paths
    import vd_state

    def escape_shell(v):
        s = str(v)
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('$', '\\$')
        s = s.replace('`', '\\`')
        return s

    def write_env(env_file, key, value):
        if not env_file or value is None:
            return
        with open(env_file, 'a', encoding='utf-8') as f:
            f.write('export %s="%s"\n' % (key, escape_shell(value)))

    def detect_project_type(override):
        if override and override != 'auto':
            return override
        if os.path.exists('pnpm-workspace.yaml') or os.path.exists('lerna.json'):
            return 'monorepo'
        if os.path.exists('package.json'):
            try:
                with open('package.json', 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                # JS truthiness: [] and {} count as present (only null/''/0/false don't)
                def _js_truthy(v):
                    return not (v is None or v is False or v == '' or v == 0)
                if _js_truthy(pkg.get('workspaces')):
                    return 'monorepo'
                if _js_truthy(pkg.get('main')) or _js_truthy(pkg.get('exports')):
                    return 'library'
            except Exception:
                pass
        return 'single-repo'

    def detect_package_manager(override):
        if override and override != 'auto':
            return override
        if os.path.exists('bun.lockb'):
            return 'bun'
        if os.path.exists('pnpm-lock.yaml'):
            return 'pnpm'
        if os.path.exists('yarn.lock'):
            return 'yarn'
        if os.path.exists('package-lock.json'):
            return 'npm'
        return ''

    def detect_framework(override):
        if override and override != 'auto':
            return override
        if not os.path.exists('package.json'):
            return ''
        try:
            with open('package.json', 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            deps = {}
            deps.update(pkg.get('dependencies') or {})
            deps.update(pkg.get('devDependencies') or {})
            if deps.get('next'):
                return 'next'
            if deps.get('nuxt'):
                return 'nuxt'
            if deps.get('astro'):
                return 'astro'
            if deps.get('@remix-run/node') or deps.get('@remix-run/react'):
                return 'remix'
            if deps.get('svelte') or deps.get('@sveltejs/kit'):
                return 'svelte'
            if deps.get('vue'):
                return 'vue'
            if deps.get('react'):
                return 'react'
            if deps.get('express'):
                return 'express'
            if deps.get('fastify'):
                return 'fastify'
        except Exception:
            pass
        return ''

    _CODING_LEVEL_STYLES = {
        0: 'coding-level-0-eli5', 1: 'coding-level-1-junior',
        2: 'coding-level-2-mid', 3: 'coding-level-3-senior',
        4: 'coding-level-4-lead', 5: 'coding-level-5-god',
    }

    def get_coding_level_style_name(level):
        return _CODING_LEVEL_STYLES.get(level) or 'coding-level-5-god'

    def detect_agent_team():
        try:
            teams_dir = os.path.join(os.path.expanduser('~'), '.claude', 'teams')
            if not os.path.exists(teams_dir):
                return None
            # libuv's scandir sorts entries with strcmp; mirror bytewise order.
            for entry in sorted(os.scandir(teams_dir), key=lambda e: e.name.encode('utf-8')):
                if not entry.is_dir():
                    continue
                try:
                    with open(os.path.join(teams_dir, entry.name, 'config.json'), 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    members = cfg.get('members') if isinstance(cfg, dict) else None
                    if isinstance(members, list) and len(members) > 0:
                        return {'teamName': entry.name, 'memberCount': len(members)}
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def resolve_timezone():
        tz = os.environ.get('TZ')
        if tz:
            return tz
        try:
            link = os.readlink('/etc/localtime')
            marker = 'zoneinfo/'
            idx = link.find(marker)
            if idx != -1:
                return link[idx + len(marker):]
        except Exception:
            pass
        try:
            return time.tzname[0]
        except Exception:
            return ''

    def real_homedir():
        try:
            import pwd
            return pwd.getpwuid(os.getuid()).pw_dir
        except Exception:
            return os.path.expanduser('~')

    def real_username():
        try:
            import pwd
            return pwd.getpwuid(os.getuid()).pw_name
        except Exception:
            return ''

    def main():
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
        env_file = os.environ.get('CLAUDE_ENV_FILE') or None
        session_id = data.get('session_id') or None
        source = data.get('source') or 'unknown'
        base_dir = os.getcwd()

        config = vd_config.load_config()

        # Resolve plan (session lookup needs the state reader injected)
        state_cache = {}

        def read_session_state_once(sid):
            key = sid or ''
            if key not in state_cache:
                state_cache[key] = vd_state.read_session_state(sid)
            return state_cache[key]

        resolved = vd_paths.resolve_plan_path(session_id, config, read_session_state_once, base_dir)

        # Persist session state
        if session_id:
            def _updater(prev):
                nxt = dict(prev)
                nxt['sessionOrigin'] = base_dir
                nxt['activePlan'] = resolved['path'] if resolved['resolvedBy'] == 'session' else None
                nxt['suggestedPlan'] = None  # session-init always writes null here per contract
                nxt['timestamp'] = int(time.time() * 1000)
                nxt['source'] = source
                return nxt
            vd_state.update_session_state(session_id, _updater)

        git_branch = vd_paths.get_git_branch()
        git_root = vd_paths.get_git_root()
        name_pattern = vd_paths.resolve_naming_pattern(config['plan'], git_branch)

        # Pass base_dir so get_reports_path's isabs guard handles absolute
        # active_plan paths correctly (avoids double-anchoring). Append trailing
        # '/' explicitly to match golden. Pass full config plus session state so
        # umbrella and feature-first layouts resolve through the same path logic.
        path_resolve_opts = {'readOnly': True}
        reports_path_abs = vd_paths.get_reports_path(
            resolved['path'], resolved['resolvedBy'], config['plan'], config['paths'],
            base_dir, config, session_id, read_session_state_once, path_resolve_opts) + '/'
        plans_path_abs = vd_paths.get_plans_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts)
        docs_path_abs = vd_paths.get_docs_path(base_dir, config)
        umbrella_val = (config.get('paths') or {}).get('umbrella') or None
        visuals_path_abs = vd_paths.get_visuals_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts) if umbrella_val else None
        journals_path_abs = vd_paths.get_journals_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts) if umbrella_val else None
        state_path_abs = vd_paths.get_state_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts) if umbrella_val else None
        umbrella_root = vd_paths.resolve_umbrella_root(config, base_dir) if umbrella_val else None
        feature_first = bool(umbrella_val and umbrella_root and (config.get('paths') or {}).get('layout') == 'feature-first')
        scratch_feature = feature_first and vd_paths.is_global_scratch_path(reports_path_abs, base_dir, config)

        task_list_id = vd_paths.extract_task_list_id(resolved)

        project_type = detect_project_type(vd_paths._get(config, 'project', 'type'))
        package_manager = detect_package_manager(vd_paths._get(config, 'project', 'packageManager'))
        framework = detect_framework(vd_paths._get(config, 'project', 'framework'))
        cl = config.get('codingLevel')
        coding_level = -1 if cl is None else cl

        real_home = real_homedir()
        user = os.environ.get('USERNAME') or os.environ.get('USER') or os.environ.get('LOGNAME') or real_username()
        locale = os.environ.get('LANG') or ''
        timezone = resolve_timezone()
        # VD_CLAUDE_SETTINGS_DIR must point to the real ~/.claude, not a test-injected fake HOME.
        claude_settings_dir = os.path.join(real_home, '.claude')

        if env_file:
            plan_cfg = config['plan']
            write_env(env_file, 'VD_SESSION_ID', session_id or '')
            write_env(env_file, 'VD_PLAN_NAMING_FORMAT', plan_cfg.get('namingFormat'))
            write_env(env_file, 'VD_PLAN_DATE_FORMAT', plan_cfg.get('dateFormat'))
            write_env(env_file, 'VD_PLAN_ISSUE_PREFIX', plan_cfg.get('issuePrefix') or '')
            write_env(env_file, 'VD_PLAN_REPORTS_DIR', plan_cfg.get('reportsDir'))
            write_env(env_file, 'VD_NAME_PATTERN', name_pattern)
            write_env(env_file, 'VD_ACTIVE_PLAN', resolved['path'] if resolved['resolvedBy'] == 'session' else '')
            write_env(env_file, 'VD_SUGGESTED_PLAN', resolved['path'] if resolved['resolvedBy'] == 'branch' else '')

            if task_list_id:
                write_env(env_file, 'CLAUDE_CODE_TASK_LIST_ID', task_list_id)

            write_env(env_file, 'VD_GIT_ROOT', git_root or '')
            write_env(env_file, 'VD_REPORTS_PATH', reports_path_abs)
            write_env(env_file, 'VD_DOCS_PATH', docs_path_abs)
            write_env(env_file, 'VD_PLANS_PATH', plans_path_abs)
            write_env(env_file, 'VD_PROJECT_ROOT', base_dir)
            # Umbrella vars — emitted only when opt-in is active (purely additive)
            if umbrella_val:
                write_env(env_file, 'VD_UMBRELLA', umbrella_val)
                write_env(env_file, 'VD_VISUALS_PATH', visuals_path_abs)
                write_env(env_file, 'VD_JOURNALS_PATH', journals_path_abs)
                write_env(env_file, 'VD_STATE_PATH', state_path_abs)
            write_env(env_file, 'VD_PROJECT_TYPE', project_type)
            write_env(env_file, 'VD_PACKAGE_MANAGER', package_manager)
            write_env(env_file, 'VD_FRAMEWORK', framework)
            write_env(env_file, 'VD_RUNTIME_VERSION', 'python/' + platform.python_version())
            write_env(env_file, 'VD_OS_PLATFORM', sys.platform)
            write_env(env_file, 'VD_GIT_BRANCH', git_branch or '')
            write_env(env_file, 'VD_USER', user)
            write_env(env_file, 'VD_LOCALE', locale)
            write_env(env_file, 'VD_TIMEZONE', timezone)
            write_env(env_file, 'VD_CLAUDE_SETTINGS_DIR', claude_settings_dir)

            locale_cfg = config.get('locale') or {}
            if locale_cfg.get('thinkingLanguage'):
                write_env(env_file, 'VD_THINKING_LANGUAGE', locale_cfg['thinkingLanguage'])
            if locale_cfg.get('responseLanguage'):
                write_env(env_file, 'VD_RESPONSE_LANGUAGE', locale_cfg['responseLanguage'])

            val = (config.get('plan') or {}).get('validation') or {}
            mn = val.get('minQuestions')
            mn = 3 if mn is None else mn
            mx = val.get('maxQuestions')
            mx = 8 if mx is None else mx
            write_env(env_file, 'VD_VALIDATION_MODE', val.get('mode') or 'prompt')
            write_env(env_file, 'VD_VALIDATION_MIN_QUESTIONS', mn)
            write_env(env_file, 'VD_VALIDATION_MAX_QUESTIONS', mx)
            write_env(env_file, 'VD_VALIDATION_FOCUS_AREAS',
                      ','.join(val.get('focusAreas') or ['assumptions', 'risks', 'tradeoffs', 'architecture']))
            write_env(env_file, 'VD_CODING_LEVEL', coding_level)
            write_env(env_file, 'VD_CODING_LEVEL_STYLE', get_coding_level_style_name(coding_level))

            team_info = detect_agent_team()
            if team_info:
                write_env(env_file, 'VD_AGENT_TEAM', team_info['teamName'])
                write_env(env_file, 'VD_AGENT_TEAM_MEMBERS', team_info['memberCount'])

        plan_part = ''
        if resolved['path']:
            plan_part = ('Plan: %s' % resolved['path']) if resolved['resolvedBy'] == 'session' else ('Suggested: %s' % resolved['path'])
        parts = ['Session %s. Project: %s' % (source, project_type)]
        if package_manager:
            parts.append('PM: %s' % package_manager)
        parts.append('Plan naming: %s' % config['plan'].get('namingFormat'))
        if plan_part:
            parts.append(plan_part)
        if scratch_feature:
            parts.append('Feature: _global/scratch')
        sys.stdout.write(' | '.join(parts) + '\n')

        sys.exit(0)

    try:
        main()
    except Exception as err:
        sys.stderr.write('[session-init] error: %s\n' % err)
        sys.exit(0)

except Exception as e:
    sys.stderr.write('[session-init] fatal: %s\n' % e)
    sys.exit(0)
