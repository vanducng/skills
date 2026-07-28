#!/usr/bin/env python3

import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))

try:
    import vd_paths
    import vd_state
except Exception:
    sys.exit(0)


STOP_WORDS = {
    'a', 'add', 'an', 'and', 'are', 'as', 'at', 'based', 'be', 'both', 'build',
    'by', 'can', 'claude', 'code', 'codex', 'create', 'do', 'fix', 'for', 'from',
    'implement', 'improve', 'in', 'into', 'is', 'it', 'let', 'lets', 'make', 'of',
    'on', 'or', 'please', 'that', 'the', 'this', 'to', 'update', 'use', 'using',
    'we', 'will', 'with', 'would',
}
SECRET_WORDS = {
    'authorization', 'bearer', 'credential', 'credentials', 'key', 'passphrase',
    'passcode', 'passwd', 'password', 'pin', 'otp', 'secret', 'token', 'totp',
}
SECRET_MARKER_RE = re.compile(
    r'\b(?:authorization|bearer|credential|credentials|key|otp|passcode|'
    r'passphrase|passwd|password|pin|secret|token|totp)\b',
    re.IGNORECASE,
)


def kebab(value, limit):
    value = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', value)
    value = re.sub(r'[^A-Za-z0-9]+', '-', value).strip('-').lower()
    return value[:limit].rstrip('-')


def has_secret_marker(value):
    value = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', value)
    value = re.sub(r'[_-]+', ' ', value)
    return SECRET_MARKER_RE.search(value) is not None


def sensitive_ticket_context(prompt, match):
    prefix = match.group(1).split('-', 1)[0].lower()
    if prefix in SECRET_WORDS:
        return True
    clause = re.split(r'[.;\n]', prompt[:match.start()])[-1]
    return has_secret_marker(clause)


def derive_intent(prompt):
    invocation = ''
    match = re.match(
        r'^\s*[$/](?:(?:vd|ck):)?([A-Za-z][A-Za-z0-9-]*)(?=$|[:\s])[:\s]*',
        prompt,
    )
    if match:
        invocation = match.group(1)
        prompt = prompt[match.end():]

    prompt = re.sub(r'(?:https?://|www\.)\S+', ' ', prompt, flags=re.IGNORECASE)
    prompt = re.sub(r'(?:[A-Za-z]:\\|(?:^|\s)(?:~?/|\./|\.\./))\S+', ' ', prompt)
    prompt = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*=\S+', ' ', prompt)

    rejected_tickets = []
    for ticket in re.finditer(r'\b([A-Za-z][A-Za-z0-9]{1,9}-[0-9]{1,7})\b', prompt):
        if not sensitive_ticket_context(prompt, ticket):
            return ticket.group(1).upper()
        rejected_tickets.append(ticket.span())

    for start, end in reversed(rejected_tickets):
        prompt = prompt[:start] + ' ' + prompt[end:]

    prompt = ' '.join(
        clause for clause in re.split(r'[.;\n]', prompt)
        if not has_secret_marker(clause)
    )
    prompt = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', prompt)

    words = []
    for raw in re.findall(r'[A-Za-z0-9][A-Za-z0-9_-]*', prompt):
        for part in re.split(r'[-_]+', raw):
            if not part:
                continue
            lower = part.lower()
            if lower in SECRET_WORDS:
                continue
            if lower in STOP_WORDS or len(part) < 2 or len(part) > 20:
                continue
            if (len(part) >= 12 and any(c.isalpha() for c in part)
                    and any(c.isdigit() for c in part)
                    and len(set(part.lower())) >= 10):
                continue
            normalized = kebab(part, 20)
            if normalized and normalized not in words:
                words.append(normalized)
            if len(words) == 4:
                return '-'.join(words)

    if words:
        return '-'.join(words)
    return kebab(invocation, 20) or 'session'


def build_label(payload):
    cwd = payload.get('cwd')
    if not isinstance(cwd, str) or not cwd.strip():
        cwd = os.getcwd()
    root = vd_paths.get_main_worktree_root(cwd) or vd_paths.get_git_root(cwd) or cwd
    project = kebab(os.path.basename(os.path.normpath(root)), 20) or 'project'
    intent = derive_intent(payload['prompt'])
    available = 40 - len(project) - 1
    intent = intent[:available].rstrip('-') or 'session'
    return '%s:%s' % (project, intent)


def main():
    if os.environ.get('HERDR_ENV') != '1':
        return
    pane_id = os.environ.get('HERDR_PANE_ID')
    herdr = shutil.which('herdr')
    if not pane_id or not herdr:
        return

    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    if not isinstance(payload, dict) or payload.get('agent_id'):
        return
    session_id = payload.get('session_id')
    prompt = payload.get('prompt')
    if not isinstance(session_id, str) or not session_id:
        return
    if not isinstance(prompt, str) or not prompt.strip():
        return
    if 'herdrPaneRename' in (vd_state.read_session_state(session_id) or {}):
        return

    label = build_label(payload)
    claimed = [False]

    def claim(previous):
        if 'herdrPaneRename' in previous:
            return previous
        claimed[0] = True
        next_state = dict(previous)
        next_state['herdrPaneRename'] = {'paneId': pane_id, 'label': label}
        return next_state

    if not vd_state.update_session_state(session_id, claim) or not claimed[0]:
        return

    try:
        subprocess.run(
            [herdr, 'pane', 'rename', pane_id, label],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1,
            check=False,
        )
    except Exception:
        pass


try:
    main()
except Exception:
    pass
