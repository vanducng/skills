"""Unit tests for the vendored twikit patch (regexes + idempotent apply)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import _twikit_patch


def test_on_demand_file_regex_finds_token_index():
    body = '...,42:"ondemand.s",43:"deadbeef0123456789abcdef00112233"...'
    m = _twikit_patch.ON_DEMAND_FILE_REGEX.search(body)
    assert m is not None
    assert m.group(1) == "42"


def test_on_demand_file_regex_handles_single_quotes():
    body = ",7:'ondemand.s',"
    m = _twikit_patch.ON_DEMAND_FILE_REGEX.search(body)
    assert m is not None
    assert m.group(1) == "7"


def test_on_demand_hash_pattern_finds_hash_for_token_index():
    import re

    body = '...,42:"ondemand.s",43:"deadbeef0123456789abcdef00112233"...'
    pattern = re.compile(_twikit_patch.ON_DEMAND_HASH_PATTERN.format("43"))
    m = pattern.search(body)
    assert m is not None
    assert m.group(1) == "deadbeef0123456789abcdef00112233"


def test_indices_regex_loosened_to_two_char_var_names():
    js = """
    function foo(ab) { return (ab[15], 16); }
    function bar(c) { return (c[3], 16); }
    function baz(de) { return (de[7], 16); }
    """
    indices = [int(m.group(2)) for m in _twikit_patch.INDICES_REGEX.finditer(js)]
    assert indices == [15, 3, 7]


def test_apply_is_idempotent_and_replaces_all_three_sites():
    _twikit_patch.apply()
    _twikit_patch.apply()
    import twikit.x_client_transaction.transaction as t1
    import twikit.x_client_transaction as t2
    import twikit.client.client as t3
    import twikit.user as t4

    assert t1.ClientTransaction is _twikit_patch.PatchedClientTransaction
    assert t2.ClientTransaction is _twikit_patch.PatchedClientTransaction
    assert t3.ClientTransaction is _twikit_patch.PatchedClientTransaction
    assert t4.User.__init__ is _twikit_patch._patched_user_init


if __name__ == "__main__":
    import traceback

    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failures += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    sys.exit(1 if failures else 0)
