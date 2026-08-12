#!/usr/bin/env python3
"""scout-block.py - VD-CLI clean-room PreToolUse hook.

Blocks reads/searches into heavy/ignored directories (node_modules, .git,
dist, build, vendor, etc.). Also blocks overly-broad Glob patterns.

Decision: writes to stderr with exit 2 to block; exit 0 to allow.
Fail-open: any unexpected error -> exit 0 (allow).

Config: add a project-local <git-root>/.vdignore or ~/.claude/.vdignore
        with gitignore-style patterns to extend the default blocklist.
        Prefix a pattern with "!" to un-block (allowlist).
"""

import json
import os
import re
import sys

try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
    import vd_paths

    # -- default blocked directories ------------------------------------------

    DEFAULT_BLOCKED = [
        'node_modules',
        '__pycache__',
        '.git',
        'dist',
        'build',
        '.next',
        '.nuxt',
        '.venv',
        'venv',
        'vendor',
        'target',
        'coverage',
        '.cache',
        '.turbo',
        '.parcel-cache',
    ]

    # ponytail: target/ is only a build dir next to Cargo.toml/pom.xml; name-only match false-positives on Go internal/target packages.
    TARGET_SOURCE = '(^|/)target(/|$)'

    # ponytail: .git/info/exclude is a legit worktree/cktovd write target; the rest of .git stays blocked.
    GIT_INFO_EXCLUDE_RE = re.compile(r'(^|/)\.git/info/exclude$')

    # -- minimal gitignore-style pattern matching -----------------------------

    def pattern_to_regex(pat):
        # '*' must be escaped here so the __STAR__ conversion below can see it
        r = re.sub(r'[.+^${}()|[\]\\*]', r'\\\g<0>', pat)
        r = re.sub(r'\\\*', '__STAR__', r)
        r = re.sub(r'\?', '[^/]', r)
        r = re.sub(r'__STAR____STAR__', '.*', r)
        r = re.sub(r'__STAR__', '[^/]*', r)
        return re.compile('(^|/)' + r + '(/|$)')

    def load_ignore_file(file_path):
        allowed = []
        blocked = []
        if not file_path or not os.path.exists(file_path):
            return {'allowed': allowed, 'blocked': blocked}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.read().split('\n')
            for raw in lines:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('!'):
                    inner = line[1:].strip()
                    if inner:
                        allowed.append(pattern_to_regex(inner))
                else:
                    blocked.append(pattern_to_regex(line))
        except Exception:
            pass  # fail-open
        return {'allowed': allowed, 'blocked': blocked}

    def build_checker(cwd):
        claude_dir = os.path.join(os.path.expanduser('~'), '.claude')
        global_ignore = os.path.join(claude_dir, '.vdignore')
        git_root = vd_paths.get_git_root(cwd)
        local_ignore = os.path.join(git_root, '.vdignore') if git_root else None

        global_rules = load_ignore_file(global_ignore)
        local_rules = load_ignore_file(local_ignore) if local_ignore else {'allowed': [], 'blocked': []}

        default_blocked_regexes = [
            re.compile('(^|/)' + re.sub(r'[.+^${}()|[\]\\]', r'\\\g<0>', name) + '(/|$)')
            for name in DEFAULT_BLOCKED
        ]

        all_blocked = default_blocked_regexes + global_rules['blocked'] + local_rules['blocked']
        all_allowed = global_rules['allowed'] + local_rules['allowed']
        return {'allBlocked': all_blocked, 'allAllowed': all_allowed}

    def js_regex_source(pat):
        # JS RegExp.source escapes unescaped '/' — but not inside character classes.
        out = []
        in_class = False
        esc = False
        for ch in pat:
            if esc:
                out.append(ch)
                esc = False
                continue
            if ch == '\\':
                out.append(ch)
                esc = True
                continue
            if ch == '[' and not in_class:
                in_class = True
            elif ch == ']' and in_class:
                in_class = False
            elif ch == '/' and not in_class:
                out.append('\\')
            out.append(ch)
        return ''.join(out)

    def is_target_build_dir(normalized, match, cwd, was_absolute=False):
        try:
            prefix = normalized[:match.start()]
            # normalize() strips the leading '/', so an absolute input must anchor
            # back to the filesystem root, not cwd.
            if was_absolute:
                parent = '/' + prefix if prefix else '/'
            else:
                parent = os.path.join(cwd, prefix) if prefix else cwd
            return (os.path.exists(os.path.join(parent, 'Cargo.toml'))
                    or os.path.exists(os.path.join(parent, 'pom.xml')))
        except Exception:
            return False

    def test_path(checker, normalized, cwd, was_absolute=False):
        if not normalized:
            return {'blocked': False, 'pattern': None}

        # Allowlist wins.
        for regex in checker['allAllowed']:
            if regex.search(normalized):
                return {'blocked': False, 'pattern': None}

        # reject traversal (.git/info/../../config) from abusing the exclude bypass
        if GIT_INFO_EXCLUDE_RE.search(normalized) and '..' not in normalized.split('/'):
            return {'blocked': False, 'pattern': None}

        for regex in checker['allBlocked']:
            m = regex.search(normalized)
            if m:
                if regex.pattern == TARGET_SOURCE and not is_target_build_dir(normalized, m, cwd, was_absolute):
                    continue
                return {'blocked': True, 'pattern': js_regex_source(regex.pattern)}
        return {'blocked': False, 'pattern': None}

    # -- path normalization ---------------------------------------------------

    def normalize(p):
        if not p or not isinstance(p, str):
            return ''
        s = p.strip()
        s = s.replace('\\', '/')
        s = re.sub(r'^\./', '', s)
        s = re.sub(r'^/+', '', s)
        return s

    # -- extract paths from tool input ----------------------------------------

    DIRECT_PATH_KEYS = ['file_path', 'path', 'pattern']

    FS_CMDS = set([
        'cat', 'head', 'tail', 'less', 'more', 'ls', 'cd', 'rm', 'cp', 'mv', 'find', 'tree',
        'stat', 'du', 'wc', 'diff', 'open', 'code', 'vim', 'nano', 'bat', 'tee', 'touch',
        'mkdir', 'rmdir', 'chmod', 'chown', 'ln', 'readlink', 'realpath', 'rsync', 'scp',
        'tar', 'zip', 'unzip',
    ])

    # In command position these run the next token as a program, not a scan target.
    EXEC_WRAPPERS = set(['sudo', 'bash', 'sh', 'source', 'env'])

    # Cheap read-only single-file readers; an explicit file arg is not a tree scan.
    READ_CMDS = set(['cat', 'head', 'tail', 'stat', 'wc', 'bat', 'less', 'more'])

    BUILD_CMD_PREFIXES = [
        'npm ', 'npx ', 'pnpm ', 'yarn ', 'bun ', 'bunx ',
        'go build', 'go test', 'go run',
        'cargo build', 'cargo test', 'cargo run',
        'make ', 'mvn ', 'gradle ',
        'docker build', 'docker-compose',
        'kubectl ', 'terraform ',
        'python ', 'python3 ', 'pip ', 'pip3 ',
        'node ', 'tsc ', 'vite ', 'webpack ',
        'jest ', 'vitest ', 'mocha ',
    ]

    def is_build_command(cmd):
        lower = cmd.lower().strip()
        for p in BUILD_CMD_PREFIXES:
            if lower.startswith(p) or (' ' + p.strip() + ' ') in lower:
                return True
        return False

    _QUOTED_RE = re.compile(r'''["']([^"']+)["']''')
    _QUOTED_STRIP_RE = re.compile(r'''["'][^"']*["']''')
    _WS_RE = re.compile(r'\s+')
    _EXT_RE = re.compile(r'\.[a-zA-Z0-9]{1,6}$')
    _ASSIGN_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
    _GLOB_RE = re.compile(r'[*?\[\]{}]')
    _GIT_SEG_RE = re.compile(r'(^|/)\.git(/|$)')
    # Quoted tags prevent local expansion; unquoted bodies stay guarded.
    _HEREDOC_RE = re.compile(
        r'''<<-?\s*(?P<quote>['"])(?P<tag>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)[^\n]*\n.*?\n[ \t]*(?P=tag)[ \t]*(?=\n|$)''',
        re.DOTALL,
    )
    _EXCLUDE_FLAGS = set([
        '--exclude', '--exclude-dir', '--ignore', '--skip', '-x',
    ])
    _FIND_PATH_FLAGS = set(['-path', '-wholename'])

    def quoted_filter_operand(cmd, start):
        prefix = cmd[:start].rstrip().split()
        if not prefix:
            return False
        if prefix[-1] in _EXCLUDE_FLAGS:
            return True
        return len(prefix) > 1 and prefix[-1] in _FIND_PATH_FLAGS and prefix[-2] in ('-not', '!')

    def extract_bash_paths(cmd):
        if not cmd:
            return []
        heredoc = _HEREDOC_RE.search(cmd)
        if (heredoc and re.match(r'^\s*(?:sudo\s+)?ssh\b', cmd)
                and not re.search(r'[;&|\n]', cmd[:heredoc.start()])):
            cmd = cmd[:heredoc.start()] + heredoc.group(0).split('\n', 1)[0] + cmd[heredoc.end():]
        if is_build_command(cmd):
            return []

        results = []

        # Extract quoted segments first
        for m in _QUOTED_RE.finditer(cmd):
            s = m.group(1)
            if not quoted_filter_operand(cmd, m.start()) and ('/' in s or '\\' in s):
                results.append(s)

        # Remove quoted segments and split remaining
        unquoted = _QUOTED_STRIP_RE.sub(' ', cmd)
        tokens = [t for t in _WS_RE.split(unquoted) if t]

        is_fs = False
        is_read = False
        seen_cmd = False
        skip_next = False
        previous = None

        for tok in tokens:
            if skip_next:
                skip_next = False
                continue
            if tok in ('&&', '||', ';', '|'):
                is_fs = False
                is_read = False
                seen_cmd = False
                previous = None
                continue
            # FOO=bar prefix before the command is not a scan target; after it, check the value
            if _ASSIGN_RE.match(tok):
                if not seen_cmd:
                    continue
                tok = tok.split('=', 1)[1]
                if not tok:
                    continue
            if tok.startswith('-'):
                # --exclude=X style: skip both halves
                if '=' in tok:
                    previous = tok
                    continue
                # --exclude X style
                if tok in _EXCLUDE_FLAGS or (tok in _FIND_PATH_FLAGS and previous in ('-not', '!')):
                    skip_next = True
                previous = tok
                continue
            if tok == '!':
                previous = tok
                continue
            if not seen_cmd:
                # command position: exec wrappers keep the next token in command position (quoted payloads of bash -c are still scanned via the quoted pass)
                if tok.lower() in EXEC_WRAPPERS:
                    previous = tok
                    continue
                seen_cmd = True
                lc = tok.lower()
                is_fs = lc in FS_CMDS
                is_read = lc in READ_CMDS
                previous = tok
                continue
            # For fs commands, blocked dir names (no slash) count; for others require slash.
            has_slash = '/' in tok or '\\' in tok
            looks_path = has_slash or bool(_EXT_RE.search(tok))
            is_blocked_name = tok in DEFAULT_BLOCKED
            if is_fs and is_blocked_name:
                results.append(tok)
                continue
            # cheap read: explicit single file (has extension, no glob) is not a tree scan; .git stays gated by the checker
            if is_read and _EXT_RE.search(tok) and not _GLOB_RE.search(tok) and not _GIT_SEG_RE.search(tok):
                continue
            if looks_path:
                results.append(tok)
            previous = tok
        return results

    def extract_paths(tool_name, tool_input):
        paths = []
        for key in DIRECT_PATH_KEYS:
            v = tool_input.get(key)
            if v and isinstance(v, str):
                paths.append(v)
        cmd = tool_input.get('command')
        if cmd and isinstance(cmd, str):
            if tool_name.lower() == 'apply_patch':
                paths.extend(re.findall(
                    r'^\*\*\* (?:(?:Add|Update|Delete) File|Move to): (.+)$', cmd, re.MULTILINE,
                ))
            else:
                paths.extend(extract_bash_paths(cmd))
        return [p for p in paths if p]

    # -- broad glob detection -------------------------------------------------

    BROAD_GLOB_RE = [
        re.compile(r'^\*\*$', re.ASCII),
        re.compile(r'^\*$', re.ASCII),
        re.compile(r'^\*\*/\*$', re.ASCII),
        re.compile(r'^\*\*/\.\*$', re.ASCII),
        re.compile(r'^\*\.\w+$', re.ASCII),
        re.compile(r'^\*\.\{[^}]+\}$', re.ASCII),
        re.compile(r'^\*\*/\*\.\w+$', re.ASCII),
        re.compile(r'^\*\*/\*\.\{[^}]+\}$', re.ASCII),
    ]

    SPECIFIC_DIRS = set([
        'src', 'lib', 'app', 'apps', 'packages', 'components', 'pages', 'api', 'server',
        'client', 'web', 'mobile', 'shared', 'common', 'utils', 'helpers', 'services',
        'hooks', 'store', 'routes', 'models', 'controllers', 'views', 'tests', '__tests__', 'spec',
    ])

    _BASEPATH_RE = re.compile(r'^\.?/?$')

    def is_broad_glob(pattern):
        p = pattern.strip()
        return any(rx.search(p) for rx in BROAD_GLOB_RE)

    def has_specific_dir(pattern):
        first = pattern.split('/')[0]
        return bool(first and '*' not in first and first != '.' and first != '..')

    def check_broad_glob(tool_name, tool_input):
        if tool_name != 'Glob':
            return None
        pattern = tool_input.get('pattern')
        if not pattern or not is_broad_glob(pattern) or has_specific_dir(pattern):
            return None
        base_path = tool_input.get('path') or ''
        # Only block when no specific base path is given.
        if base_path and not _BASEPATH_RE.match(base_path) and os.path.basename(base_path) in SPECIFIC_DIRS:
            return None
        return {
            'blocked': True,
            'reason': "Pattern '%s' is too broad — would fill context window. Use a more specific path prefix." % pattern,
            'suggestions': ['src/**/*', 'lib/**/*', 'app/**/*'],
        }

    # -- output helpers -------------------------------------------------------

    def use_colors():
        if 'NO_COLOR' in os.environ:
            return False
        if 'FORCE_COLOR' in os.environ:
            return True
        return bool(sys.stderr.isatty())

    def colorize(code, text):
        if not use_colors():
            return text
        return '\x1b[' + code + 'm' + text + '\x1b[0m'

    def format_block_msg(blocked_path, pattern, tool_name, config_hint):
        lines = [
            '',
            colorize('36', 'NOTE:') + ' This block is intentional — protects context window.',
            '',
            colorize('31', 'BLOCKED') + ": Access to '" + blocked_path + "' denied",
            '',
            '  ' + colorize('33', 'Pattern:') + '  ' + pattern,
            '  ' + colorize('33', 'Tool:') + '     ' + tool_name,
            '',
            '  ' + colorize('34', 'To allow, add to') + ' ' + config_hint + ':',
            '    !' + pattern,
            '',
        ]
        return '\n'.join(lines)

    def format_broad_msg(reason, suggestions):
        lines = [
            '',
            colorize('36', 'NOTE:') + ' This block is intentional to optimize context.',
            '',
            colorize('31', 'BLOCKED') + ': Overly broad glob pattern detected',
            '',
            '  ' + colorize('33', 'Reason:') + ' ' + reason,
            '',
            '  ' + colorize('34', 'Use more specific patterns:'),
        ]
        lines.extend('    • ' + s for s in (suggestions or []))
        lines.append('')
        return '\n'.join(lines)

    # -- main -----------------------------------------------------------------

    def main():
        try:
            raw = sys.stdin.read()
        except Exception:
            sys.exit(0)  # fail-open on read error
        if not raw or not raw.strip():
            sys.exit(0)
        try:
            data = json.loads(raw)
        except Exception:
            sys.exit(0)  # fail-open on parse error

        if not isinstance(data, dict):
            sys.exit(0)

        tool_input = data.get('tool_input')
        if not isinstance(tool_input, dict):
            tool_input = data.get('toolInput')
        if not isinstance(tool_input, dict):
            sys.exit(0)

        raw_name = str(data.get('tool_name') or data.get('toolName') or 'unknown')
        tool_aliases = {
            'run_terminal_command': 'Bash',
            'bash': 'Bash',
            'read_file': 'Read',
            'search_replace': 'Edit',
            'write': 'Write',
            'multiedit': 'Edit',
            'grep': 'Grep',
            'list_dir': 'Glob',
            'listdir': 'Glob',
        }
        tool_name = tool_aliases.get(raw_name, tool_aliases.get(raw_name.lower(), raw_name))
        raw_cwd = data.get('cwd')
        cwd = raw_cwd.strip() if (isinstance(raw_cwd, str) and raw_cwd.strip()) else os.getcwd()
        claude_dir = os.path.join(os.path.expanduser('~'), '.claude')
        config_hint = os.path.join(claude_dir, '.vdignore')

        # Check broad glob first (Glob tool only)
        broad_result = check_broad_glob(tool_name, tool_input)
        if broad_result:
            sys.stderr.write(format_broad_msg(broad_result['reason'], broad_result['suggestions']))
            sys.exit(2)

        # Build checker (loads .vdignore files)
        checker = build_checker(cwd)

        # Extract and test paths
        raw_paths = extract_paths(tool_name, tool_input)
        for p in raw_paths:
            norm = normalize(p)
            was_absolute = p.strip().replace('\\', '/').startswith('/')
            if not norm:
                continue
            result = test_path(checker, norm, cwd, was_absolute)
            if result['blocked']:
                sys.stderr.write(format_block_msg(norm, result['pattern'] or norm, tool_name, config_hint))
                sys.exit(2)

        sys.exit(0)

    main()

except Exception:
    sys.exit(0)  # fail-open
