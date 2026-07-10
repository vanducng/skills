#!/usr/bin/env python3
"""team-context-inject.py - VD-CLI clean-room SubagentStart hook.

When the spawned agent has an agent_id matching "name@team-name" format,
injects team peer list and task summary as additionalContext.
No-op when teams directory is absent or agent is not a team member.
Fail-open: always exits 0.
"""

import json
import os
import sys

TEAMS_DIR = os.path.join(os.path.expanduser('~'), '.claude', 'teams')
TASKS_DIR = os.path.join(os.path.expanduser('~'), '.claude', 'tasks')


def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def extract_team_name(agent_id):
    """Extract team name from agent_id (format "agentName@team-name").
    Rejects path-traversal and invalid forms."""
    if not agent_id or not isinstance(agent_id, str):
        return None
    at = agent_id.find('@')
    if at < 1:
        return None
    name = agent_id[at + 1:]
    if not name or '/' in name or '\\' in name or '..' in name:
        return None
    return name


def build_peer_list(config, current_agent_id):
    members = config.get('members') if isinstance(config, dict) else None
    if not isinstance(members, list):
        return 'none'
    peers = []
    for m in members:
        member = m if isinstance(m, dict) else {}
        if member.get('agentId') != current_agent_id:
            peers.append('%s (%s)' % (member.get('name'), member.get('agentType') or 'unknown'))
    joined = ', '.join(peers)
    return joined or 'none'


def count_tasks(team_name):
    task_dir = os.path.join(TASKS_DIR, team_name)
    try:
        if not os.path.exists(task_dir):
            return None
        files = [f for f in os.listdir(task_dir) if f.endswith('.json')]
        pending = 0
        in_progress = 0
        completed = 0
        for file in files:
            t = read_json(os.path.join(task_dir, file))
            status = t.get('status') if isinstance(t, dict) else None
            if not status:
                continue
            if status == 'pending':
                pending += 1
            elif status == 'in_progress':
                in_progress += 1
            elif status == 'completed':
                completed += 1
        return {'pending': pending, 'inProgress': in_progress, 'completed': completed}
    except Exception:
        return None


def build_vd_context():
    env = os.environ
    ctx = []
    if env.get('VD_REPORTS_PATH'):
        ctx.append('Reports: %s' % env['VD_REPORTS_PATH'])
    if env.get('VD_PLANS_PATH'):
        ctx.append('Plans: %s' % env['VD_PLANS_PATH'])
    if env.get('VD_PROJECT_ROOT'):
        ctx.append('Project: %s' % env['VD_PROJECT_ROOT'])
    if env.get('VD_NAME_PATTERN'):
        ctx.append('Naming: %s' % env['VD_NAME_PATTERN'])
    if env.get('VD_GIT_BRANCH'):
        ctx.append('Branch: %s' % env['VD_GIT_BRANCH'])
    if env.get('VD_ACTIVE_PLAN'):
        ctx.append('Active plan: %s' % env['VD_ACTIVE_PLAN'])
    ctx.append('Commits: conventional (feat:, fix:, docs:, refactor:, test:, chore:)')
    return ctx


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)
        payload = json.loads(raw)
    except Exception:
        sys.exit(0)

    agent_id = (payload.get('agent_id') if isinstance(payload, dict) else None) or ''
    team_name = extract_team_name(agent_id)
    if not team_name:
        sys.exit(0)

    if not os.path.exists(TEAMS_DIR):
        sys.exit(0)

    config_path = os.path.join(TEAMS_DIR, team_name, 'config.json')
    config = read_json(config_path)
    if not isinstance(config, dict):
        sys.exit(0)
        sys.exit(0)

    peer_list = build_peer_list(config, agent_id)
    counts = count_tasks(team_name)

    config_name = config.get('name') if isinstance(config, dict) else None
    lines = []
    lines.append('## Team Context')
    lines.append('Team: %s' % (config_name or team_name))
    lines.append('Your peers: %s' % peer_list)
    if counts:
        lines.append('Task summary: %s pending, %s in progress, %s completed'
                     % (counts['pending'], counts['inProgress'], counts['completed']))

    vd_ctx = build_vd_context()
    if len(vd_ctx) > 0:
        lines.append('')
        lines.append('## VD Context')
        lines.extend(vd_ctx)

    lines.append('')
    lines.append('Remember: Check TaskList, claim tasks, respect file ownership, use SendMessage to communicate.')

    sys.stdout.write(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'SubagentStart',
            'additionalContext': '\n'.join(lines),
        },
    }, separators=(',', ':'), ensure_ascii=False) + '\n')

    sys.exit(0)


try:
    main()
except Exception:
    sys.exit(0)
