#!/usr/bin/env python3
"""teammate-idle-handler.py - VD-CLI clean-room TeammateIdle hook.

Fires when an agent team teammate goes idle.
Emits available/unblocked task summary as additionalContext.
No-op when team_name is absent. Fail-open: always exits 0.
"""
import json
import os
import sys

TASKS_DIR = os.path.join(os.path.expanduser('~'), '.claude', 'tasks')


def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def safe_team_name(name):
    # team_name arrives in untrusted payloads; must stay a single path segment
    if not name or not isinstance(name, str):
        return None
    if '/' in name or '\\' in name or '..' in name:
        return None
    return name

def get_task_info(team_name):
    task_dir = os.path.join(TASKS_DIR, team_name)
    try:
        if not os.path.exists(task_dir):
            return None
        files = sorted(f for f in os.listdir(task_dir) if f.endswith('.json'))
        tasks = [t for t in (read_json(os.path.join(task_dir, f)) for f in files)
                 if isinstance(t, dict)]

        completed_ids = set(
            str(t.get('id')) for t in tasks if t.get('status') == 'completed'
        )

        pending = 0
        in_progress = 0
        completed = 0
        unblocked = []

        for task in tasks:
            status = task.get('status')
            if status == 'completed':
                completed += 1
                continue
            if status == 'in_progress':
                in_progress += 1
                continue
            if status != 'pending':
                continue
            pending += 1

            blockers = task.get('blockedBy') or []
            is_unblocked = all(str(bid) in completed_ids for bid in blockers)
            if is_unblocked and not task.get('owner'):
                unblocked.append({'id': task.get('id'), 'subject': task.get('subject') or ''})

        total = pending + in_progress + completed
        return {'pending': pending, 'inProgress': in_progress, 'completed': completed,
                'total': total, 'unblocked': unblocked}
    except Exception:
        return None


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)
        payload = json.loads(raw)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)

    if not isinstance(payload, dict):
        payload = {}

    teammate_name = payload.get('teammate_name')
    team_name = safe_team_name(payload.get('team_name'))
    if not team_name:
        sys.exit(0)

    info = get_task_info(team_name)
    lines = []
    lines.append('## Teammate Idle')
    lines.append('%s is idle.' % (teammate_name or 'Teammate'))

    if info:
        remaining = info['pending'] + info['inProgress']
        lines.append('Tasks: %s/%s done. %s remaining.' % (info['completed'], info['total'], remaining))
        if len(info['unblocked']) > 0:
            listed = ', '.join('#%s "%s"' % (t['id'], t['subject']) for t in info['unblocked'])
            lines.append('Unblocked & unassigned: %s' % listed)
            lines.append('Consider assigning work to %s or waking them with a message.'
                         % (teammate_name or 'this teammate'))
        elif remaining == 0:
            lines.append('No remaining tasks. Consider shutting down %s.'
                         % (teammate_name or 'this teammate'))
        else:
            lines.append('All remaining tasks are blocked or assigned. %s may be waiting for dependencies.'
                         % (teammate_name or 'Teammate'))

    sys.stdout.write(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'TeammateIdle',
            'additionalContext': '\n'.join(lines),
        }
    }, separators=(',', ':'), ensure_ascii=False) + '\n')

    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
