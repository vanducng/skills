#!/usr/bin/env python3
"""statusline.py - VD-CLI clean-room statusLine hook.

Reads Claude Code statusLine stdin JSON, emits a single ANSI status line.
Sections: model / cwd/branch / context usage / active plan / cost.
Registered via settings.json "statusLine" key (not hooks{}).
Fail-open: always emits at least a minimal line; never crashes.
"""
import json
import math
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import vd_paths  # noqa: E402
import vd_state  # noqa: E402

# ── ANSI helpers ──────────────────────────────────────────────────────────

NO_COLOR = ('NO_COLOR' in os.environ) or (os.environ.get('TERM') == 'dumb')
FORCE_COLOR = 'FORCE_COLOR' in os.environ
use_color = FORCE_COLOR or (not NO_COLOR and bool(sys.stderr.isatty() or sys.stdout.isatty()))


def ansi(code, text):
    if not use_color or not text:
        return text or ''
    return '\x1b[' + code + 'm' + text + '\x1b[0m'


def dim(s):
    return ansi('2', s)


def cyan(s):
    return ansi('36', s)


def magenta(s):
    return ansi('35', s)


def yellow(s):
    return ansi('33', s)


def green(s):
    return ansi('32', s)


def red(s):
    return ansi('31', s)


def bold(s):
    return ansi('1', s)


def context_color(pct):
    if pct >= 85:
        return red
    if pct >= 70:
        return yellow
    return green


def js_round(x):
    return int(math.floor(x + 0.5))


# ── path helpers ──────────────────────────────────────────────────────────

def shorten_dir(full_path):
    home = os.path.expanduser('~')
    if full_path.startswith(home):
        return '~' + full_path[len(home):]
    return full_path


def basename(full_path):
    return os.path.basename(full_path) or full_path


# ── active plan (reads session temp state) ────────────────────────────────

def read_active_plan(session_id):
    if not session_id:
        return None
    try:
        state = vd_state.read_session_state(session_id)
        if not isinstance(state, dict):
            return None
        return state.get('activePlan') or None
    except Exception:
        return None


# ── context bar ───────────────────────────────────────────────────────────

def context_bar(pct):
    capped = min(100, max(0, pct))
    filled = js_round(capped / 10)
    bar = '█' * filled + '░' * (10 - filled)
    color_fn = context_color(capped)
    return color_fn(bar) + ' ' + color_fn(str(js_round(capped)) + '%')


# ── format cost ───────────────────────────────────────────────────────────

def format_cost(usd):
    if not isinstance(usd, (int, float)) or isinstance(usd, bool) or usd <= 0:
        return None
    if usd < 0.01:
        return '<$0.01'
    # Match JS Number.toFixed(2): round half away from zero on the exact double.
    fixed = Decimal(usd).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if usd < 1:
        return '$' + str(fixed)
    return '$' + str(fixed)


# ── main ──────────────────────────────────────────────────────────────────

def main():
    payload = {}
    try:
        raw = sys.stdin.read().strip()
        if raw:
            payload = json.loads(raw)
    except Exception:
        # Fail-open: proceed with empty payload.
        pass
    if not isinstance(payload, dict):
        payload = {}

    session_id = payload.get('session_id') or None
    # Claude Code sends model as an object {id, display_name}; tolerate a plain string too.
    m = payload.get('model')
    if isinstance(m, dict) and m:
        model = m.get('display_name') or m.get('id')
    else:
        model = m
    model = model or None

    ws = payload.get('workspace')
    ws_dir = ws.get('current_dir') if isinstance(ws, dict) else None
    cwd = (payload.get('cwd') or ws_dir or os.getcwd()).strip()

    cwup = payload.get('context_window_usage_percent')
    if isinstance(cwup, (int, float)) and not isinstance(cwup, bool):
        context_pct = cwup
    else:
        ex = payload.get('exceeds_200k_tokens')
        context_pct = 100 if (isinstance(ex, bool) and ex) else None

    tcu = payload.get('total_cost_usd')
    if isinstance(tcu, (int, float)) and not isinstance(tcu, bool):
        total_cost = tcu
    else:
        cost = payload.get('cost')
        if isinstance(cost, dict):
            ctc = cost.get('total_cost_usd')
            total_cost = ctc if (isinstance(ctc, (int, float)) and not isinstance(ctc, bool)) else None
        else:
            total_cost = None

    parts = []

    # Model
    if model:
        short_model = re.sub(r'^claude-', '', model)
        short_model = re.sub(r'-\d{8}$', '', short_model)
        parts.append(cyan(short_model))

    # Directory + branch
    branch = vd_paths.get_git_branch(cwd)
    if branch:
        dir_part = '%s %s' % (dim(shorten_dir(cwd)), magenta(branch))
    else:
        dir_part = dim(shorten_dir(cwd))
    parts.append(dir_part)

    # Context bar
    if context_pct is not None:
        parts.append(context_bar(context_pct))

    # Active plan (cheap session-state read)
    active_plan = read_active_plan(session_id)
    if active_plan:
        plan_name = os.path.basename(active_plan)
        parts.append(dim('plan:') + ' ' + yellow(plan_name))

    # Cost
    cost_str = format_cost(total_cost)
    if cost_str:
        parts.append(dim(cost_str))

    if len(parts) == 0:
        sys.stdout.write(dim('vd') + '\n')
    else:
        sys.stdout.write('  '.join(parts) + '\n')

    sys.exit(0)


try:
    main()
except SystemExit:
    raise
except Exception:
    # Absolute last resort: emit minimal line and exit cleanly.
    try:
        sys.stdout.write('vd\n')
    except Exception:
        pass
    sys.exit(0)
