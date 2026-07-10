#!/usr/bin/env python3
"""task-completed-handler.py - VD-CLI clean-room TaskCompleted hook.

Fires when a task is marked completed in a team session.
Appends a completion log entry to VD_REPORTS_PATH and emits a
progress summary as additionalContext.
No-op when team_name is absent. Fail-open: always exits 0.
"""

import datetime
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
            if not (isinstance(t, dict) and t.get('status')):
                continue
            if t['status'] == 'pending':
                pending += 1
            elif t['status'] == 'in_progress':
                in_progress += 1
            elif t['status'] == 'completed':
                completed += 1
        total = pending + in_progress + completed
        return {'pending': pending, 'inProgress': in_progress, 'completed': completed, 'total': total}
    except Exception:
        return None


def append_completion_log(team_name, task_id, task_subject, teammate_name):
    reports_path = os.environ.get('VD_REPORTS_PATH')
    if not reports_path:
        return
    try:
        os.makedirs(reports_path, exist_ok=True)
        log_file = os.path.join(reports_path, 'team-%s-completions.md' % team_name)
        ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        # single-line log format; embedded newlines would inject extra entries
        subject = str(task_subject).replace('\n', ' ').replace('\r', '')
        author = str(teammate_name).replace('\n', ' ').replace('\r', '')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('- [%s] Task #%s "%s" completed by %s\n' % (ts, task_id, subject, author))
    except Exception:
        pass  # fail-open


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)
        payload = json.loads(raw)
    except Exception:
        sys.exit(0)

    task_id = payload.get('task_id')
    task_subject = payload.get('task_subject')
    teammate_name = payload.get('teammate_name')
    team_name = safe_team_name(payload.get('team_name'))
    if not team_name:
        sys.exit(0)

    append_completion_log(team_name, task_id, task_subject or '', teammate_name or 'unknown')

    counts = count_tasks(team_name)
    lines = []
    lines.append('## Task Completed')
    lines.append('Task #%s "%s" completed by %s.' % (task_id, task_subject or '', teammate_name or 'unknown'))

    if counts:
        remaining = counts['pending'] + counts['inProgress']
        lines.append('Progress: %s/%s done. %s pending, %s in progress.'
                     % (counts['completed'], counts['total'], counts['pending'], counts['inProgress']))
        if remaining == 0:
            lines.append('')
            lines.append('**All tasks completed.** Consider shutting down teammates and synthesizing results.')

    sys.stdout.write(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'TaskCompleted',
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
