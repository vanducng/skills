#!/usr/bin/env python3
"""dev-rules-reminder.py - VD-CLI clean-room UserPromptSubmit hook.

Emits hookSpecificOutput.additionalContext JSON to stdout with:
  ## Paths  - Reports/Plans/Docs/Visuals/Journals/State (umbrella-aware)
  ## Naming - Report + Plan-dir patterns
  ## Rules  - same core rules as subagent-init

Never throws (fail-open). Path-safe: no hardcoded home dirs.
"""

import json
import os
import sys

try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
    import vd_config
    import vd_paths
    import vd_state

    def read_payload():
        raw = ''
        if not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
        if not raw:
            raw = ''
            for arg in reversed(sys.argv[1:]):
                if arg.strip().startswith('{'):
                    raw = arg
                    break
        if not raw:
            return None
        return json.loads(raw)

    def main():
        payload = read_payload()
        if not payload:
            sys.exit(0)

        session_id = payload.get('session_id') or os.environ.get('VD_SESSION_ID') or None
        cwd_val = payload.get('cwd')
        base_dir = cwd_val.strip() if (isinstance(cwd_val, str) and cwd_val.strip()) else os.getcwd()

        config = vd_config.load_config()
        git_branch = vd_paths.get_git_branch(base_dir)
        name_pattern = vd_paths.resolve_naming_pattern(config['plan'], git_branch)

        path_resolve_opts = {'readOnly': True}
        state_cache = {}

        def read_session_state_once(sid):
            key = sid or ''
            if key not in state_cache:
                state_cache[key] = vd_state.read_session_state(sid)
            return state_cache[key]

        resolved = vd_paths.resolve_plan_path(session_id, config, read_session_state_once, base_dir)
        reports_path = vd_paths.get_reports_path(
            resolved['path'], resolved['resolvedBy'], config['plan'], config['paths'],
            base_dir, config, session_id, read_session_state_once, path_resolve_opts)
        plans_path = vd_paths.get_plans_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts)
        docs_path = vd_paths.get_docs_path(base_dir, config)

        umbrella_val = (config.get('paths') or {}).get('umbrella') or None
        visuals_path = vd_paths.get_visuals_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts) if umbrella_val else None
        journals_path = vd_paths.get_journals_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts) if umbrella_val else None
        state_path = vd_paths.get_state_path(base_dir, config, session_id, read_session_state_once, path_resolve_opts) if umbrella_val else None
        umbrella_root = vd_paths.resolve_umbrella_root(config, base_dir) if umbrella_val else None
        scratch_feature = bool(umbrella_val and umbrella_root
                               and (config.get('paths') or {}).get('layout') == 'feature-first'
                               and vd_paths.is_global_scratch_path(reports_path, base_dir, config))

        skills_venv = vd_paths.resolve_skills_venv(base_dir)

        lines = []

        lines.append('## Paths')
        if umbrella_val:
            lines.append('Reports: %s/ | Plans: %s/ | Docs: %s/ | Visuals: %s/ | Journals: %s/ | State: %s/'
                         % (reports_path, plans_path, docs_path, visuals_path, journals_path, state_path))
            if scratch_feature:
                lines.append('- Feature: none; artifacts use _global/scratch until `workbench new` or `workbench switch` selects a feature.')
        else:
            lines.append('Reports: %s/ | Plans: %s/ | Docs: %s/' % (reports_path, plans_path, docs_path))
        lines.append('')

        lines.append('## Naming')
        lines.append('- Report: %s' % os.path.join(reports_path, '{type}-%s.md' % name_pattern))
        lines.append('- Plan dir: %s/' % os.path.join(plans_path, name_pattern))
        lines.append('- Replace `{type}` with: agent name, report type, or context')
        lines.append('- Replace `{slug}` in pattern with: descriptive-kebab-slug')
        lines.append('')

        lines.append('## Rules')
        lines.append('- Reports → %s' % reports_path)
        lines.append('- YAGNI / KISS / DRY')
        lines.append('- Before PR merge/next ship step: fetch review comments, validate, fix valid ones, reply/resolve, re-check')
        lines.append('- Concise, list unresolved Qs at end')
        if skills_venv:
            lines.append('- Python scripts in .claude/skills/: Use `%s`' % skills_venv)
            lines.append('- Never use global pip install')

        # Codex >=0.144 parses the same nested shape as Claude (deny_unknown_fields;
        # top-level additionalContext now rejected) — one shape serves both runtimes.
        ctx = '\n'.join(lines)
        event_name = payload.get('hook_event_name') or payload.get('hookEventName') or 'UserPromptSubmit'
        out = {'hookSpecificOutput': {'hookEventName': event_name, 'additionalContext': ctx}}
        sys.stdout.write(json.dumps(out, separators=(',', ':'), ensure_ascii=False) + '\n')

        sys.exit(0)

    try:
        main()
    except Exception as err:
        sys.stderr.write('[dev-rules-reminder] error: %s\n' % err)
        sys.exit(0)

except Exception as e:
    sys.stderr.write('[dev-rules-reminder] fatal: %s\n' % e)
    sys.exit(0)
