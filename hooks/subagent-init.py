#!/usr/bin/env python3
"""subagent-init.py - VD-CLI clean-room SubagentStart hook.

Emits hookSpecificOutput.additionalContext JSON to stdout.
Re-derives all paths independently (does not rely on VD_* env vars).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))

try:
    import json

    import vd_config
    import vd_paths
    import vd_state

    PLAN_AWARE_AGENTS = frozenset([
        'planner', 'project-manager', 'code-simplifier',
        'brainstormer', 'code-reviewer', 'fullstack-developer',
    ])

    def main():
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)

        payload = json.loads(raw)
        agent_type = payload.get('agent_type') or 'unknown'
        agent_id = payload.get('agent_id') or 'unknown'
        cwd_val = payload.get('cwd')
        effective_cwd = (cwd_val.strip() if isinstance(cwd_val, str) else '') or os.getcwd()
        session_id = payload.get('session_id') or os.environ.get('VD_SESSION_ID') or None

        config = vd_config.load_config()

        git_branch = vd_paths.get_git_branch(effective_cwd)
        base_dir = effective_cwd

        # Re-derive naming pattern independently (not from env)
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

        active_plan = resolved['path'] if resolved['resolvedBy'] == 'session' else ''
        suggested_plan = resolved['path'] if resolved['resolvedBy'] == 'branch' else ''
        task_list_id = vd_paths.extract_task_list_id(resolved)

        locale = config.get('locale') or {}
        thinking_lang = locale.get('thinkingLanguage') or ''
        response_lang = locale.get('responseLanguage') or ''
        effective_thinking = thinking_lang or ('en' if response_lang else '')

        skills_venv = vd_paths.resolve_skills_venv(effective_cwd)

        lines = []

        lines.append('## Subagent: %s' % agent_type)
        lines.append('ID: %s | CWD: %s' % (agent_id, effective_cwd))
        lines.append('')

        lines.append('## Context')
        if active_plan:
            lines.append('- Plan: %s' % active_plan)
            if task_list_id:
                lines.append('- Task List: %s (shared with session)' % task_list_id)
        elif suggested_plan:
            lines.append('- Plan: none | Suggested: %s' % suggested_plan)
        else:
            lines.append('- Plan: none')
        lines.append('- Reports: %s' % reports_path)
        # Umbrella-on: append sibling dirs after docs; umbrella-off: legacy two-dir line
        if umbrella_val:
            lines.append('- Paths: %s/ | %s/ | Visuals: %s/ | Journals: %s/ | State: %s/'
                         % (plans_path, docs_path, visuals_path, journals_path, state_path))
            if scratch_feature:
                lines.append('- Feature: none; artifacts use _global/scratch until `workbench new` or `workbench switch` selects a feature.')
        else:
            lines.append('- Paths: %s/ | %s/' % (plans_path, docs_path))
        lines.append('')

        has_thinking = bool(effective_thinking and effective_thinking != response_lang)
        if has_thinking or response_lang:
            lines.append('## Language')
            if has_thinking:
                lines.append('- Thinking: Use %s for reasoning (logic, precision).' % effective_thinking)
            if response_lang:
                lines.append('- Response: Respond in %s (natural, fluent).' % response_lang)
            lines.append('')

        lines.append('## Rules')
        lines.append('- Reports → %s' % reports_path)
        lines.append('- YAGNI / KISS / DRY')
        lines.append('- Before PR merge/next ship step: fetch review comments, validate, fix valid ones, reply/resolve, re-check')
        lines.append('- Concise, list unresolved Qs at end')
        lines.append('- Human-facing prose (PRs, docs, posts): vd:unslop pass - no AI tells, no em dashes')
        if skills_venv:
            lines.append('- Python scripts in .claude/skills/: Use `%s`' % skills_venv)
            lines.append('- Never use global pip install')

        lines.append('')
        lines.append('## Naming')
        lines.append('- Report: %s' % os.path.join(reports_path, '%s-%s.md' % (agent_type, name_pattern)))
        lines.append('- Plan dir: %s/' % os.path.join(plans_path, name_pattern))
        # Umbrella siblings in Naming block (only when opt-in active)
        if umbrella_val:
            lines.append('- Visual: %s/' % os.path.join(visuals_path, name_pattern))
            lines.append('- Journal: %s.md' % os.path.join(journals_path, name_pattern))
            lines.append('- State dir: %s/' % state_path)

        if agent_type in PLAN_AWARE_AGENTS:
            lines.append('')
            lines.append('## Plan Status Updates')
            lines.append('Edit the plan.md Status column directly: `Pending` → `In Progress` → `Completed`.')

        trust = config.get('trust') or {}
        if trust.get('enabled') and trust.get('passphrase'):
            lines.append('')
            lines.append('## Trust Verification')
            lines.append('Passphrase: "%s"' % trust['passphrase'])

        agent_ctx = None
        subagent = config.get('subagent')
        if isinstance(subagent, dict):
            agents = subagent.get('agents')
            if isinstance(agents, dict):
                entry = agents.get(agent_type)
                if isinstance(entry, dict):
                    agent_ctx = entry.get('contextPrefix')
        if agent_ctx:
            lines.append('')
            lines.append('## Agent Instructions')
            lines.append(agent_ctx)

        sys.stdout.write(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'SubagentStart',
                'additionalContext': '\n'.join(lines),
            }
        }, separators=(',', ':'), ensure_ascii=False) + '\n')

        sys.exit(0)

    try:
        main()
    except Exception as err:
        sys.stderr.write('[subagent-init] error: %s\n' % err)
        sys.exit(0)

except Exception as e:
    sys.stderr.write('[subagent-init] fatal: %s\n' % e)
    sys.exit(0)
