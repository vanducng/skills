"""vd_state - Per-session temp-file state manager.

File: <tmpdir>/vd-session-<sessionId>.json (NOT ~/.claude/session.json).
Write is atomic via O_EXCL lock + temp-file rename.
Superset-compatible: never drops keys written by session-state (statusline,
lastTranscriptPath, devRulesReminder).
"""

import json
import os
import re
import tempfile
import time
import uuid

VD_TIMEOUT_MS = 500
VD_RETRY_MS = 10
VD_STALE_MS = 5000


def get_session_temp_path(session_id):
    # session_id comes from untrusted hook payloads — keep it a single safe filename segment
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', str(session_id))[:64]
    return os.path.join(tempfile.gettempdir(), 'vd-session-%s.json' % safe)


def get_lock_path(session_id):
    return get_session_temp_path(session_id) + '.lock'


def remove_stale(lock_path):
    try:
        st = os.stat(lock_path)
        if time.time() * 1000 - st.st_mtime * 1000 < VD_STALE_MS:
            return False
        os.unlink(lock_path)
        return True
    except Exception:
        return False


def acquire_lock(session_id):
    lock_path = get_lock_path(session_id)
    deadline = time.time() + VD_TIMEOUT_MS / 1000.0
    while time.time() <= deadline:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode('utf-8'))
            except Exception:
                os.close(fd)
                try:
                    os.unlink(lock_path)
                except Exception:
                    pass
                raise
            return {'fd': fd, 'lockPath': lock_path}
        except FileExistsError:
            remove_stale(lock_path)
            time.sleep(VD_RETRY_MS / 1000.0)
        except Exception:
            return None
    return None


def release_lock(lock):
    if not lock:
        return
    try:
        os.close(lock['fd'])
    except Exception:
        pass
    try:
        os.unlink(lock['lockPath'])
    except Exception:
        pass


def read_session_state(session_id):
    """Read session state from temp file. Returns None if missing/corrupt."""
    if not session_id:
        return None
    p = get_session_temp_path(session_id)
    try:
        if not os.path.exists(p):
            return None
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def atomic_write(temp_path, data):
    tmp = '%s.%s.json' % (temp_path, uuid.uuid4().hex)
    try:
        fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, indent=2))
        os.replace(tmp, temp_path)
        return True
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        return False


def update_session_state(session_id, updater):
    """Update session state atomically. updater: partial dict to merge, or callable (prev) -> next.
    Preserves all existing keys (superset-compatible with session-state)."""
    if not session_id:
        return False
    lock = acquire_lock(session_id)
    if not lock:
        return False
    try:
        current = read_session_state(session_id) or {}
        if callable(updater):
            next_state = updater(dict(current))
        else:
            next_state = dict(current)
            next_state.update(updater or {})
        if not next_state or not isinstance(next_state, dict):
            return False
        return atomic_write(get_session_temp_path(session_id), next_state)
    finally:
        release_lock(lock)
