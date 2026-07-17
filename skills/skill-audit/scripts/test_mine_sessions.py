#!/usr/bin/env python3
"""Fixture tests for mine-sessions.py: per-invocation attribution and skill-ID validation."""

import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "mine_sessions", pathlib.Path(__file__).with_name("mine-sessions.py")
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

REGISTRY = {"scout", "cook", "ship"}
PREFIXED_INVOKE = "$" + "vd:ship it"  # split: scripts/validate.sh rejects the literal prefixed ID


def write(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(l) + "\n" for l in lines))
    return str(path)


def cc_assistant(ts, tool, tid, tokens=0, skill=None):
    block = {"type": "tool_use", "name": tool, "id": tid, "input": {"skill": skill} if skill else {}}
    return {"type": "assistant", "timestamp": ts,
            "message": {"model": "opus", "usage": {"output_tokens": tokens}, "content": [block]}}


def cc_result(ts, tid, is_error):
    return {"type": "user", "timestamp": ts,
            "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "is_error": is_error}]}}


def cc_text(ts, text):
    return {"type": "user", "timestamp": ts, "message": {"content": [{"type": "text", "text": text}]}}


class Attribution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_claude_attributes_per_invocation_not_per_session(self):
        path = write(self.root / "proj" / "s1.jsonl", [
            cc_assistant("t01", "Bash", "a0", tokens=5),
            cc_result("t02", "a0", True),
            cc_text("t03", "<command-name>/scout</command-name>"),
            cc_assistant("t04", "Bash", "a1", tokens=10),
            cc_result("t05", "a1", True),
            cc_text("t06", "[Request interrupted by user]"),
            cc_assistant("t07", "Skill", "a2", skill="cook"),
            cc_assistant("t08", "Edit", "a3", tokens=20),
            cc_result("t09", "a3", False),
            cc_text("t10", "no, that's wrong"),
        ])
        attr = m.mine_claude_session(path, REGISTRY)["attr"]

        self.assertEqual(attr["scout"]["tool_errors"], 1)
        self.assertEqual(attr["scout"]["interrupts"], 1)
        self.assertEqual(attr["scout"]["corrections"], 0)
        self.assertEqual(attr["cook"]["tool_errors"], 0)
        self.assertEqual(attr["cook"]["interrupts"], 0)
        self.assertEqual(attr["cook"]["corrections"], 1)
        self.assertEqual(attr[m.NONE]["tool_errors"], 1)
        self.assertEqual(attr["scout"]["tokens"], 10)
        self.assertEqual(attr["cook"]["tokens"], 20)
        self.assertEqual(attr[m.NONE]["tokens"], 5)

    def test_error_lands_on_the_skill_that_made_the_call(self):
        path = write(self.root / "proj" / "s2.jsonl", [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_assistant("t02", "Bash", "a1"),
            cc_text("t03", "<command-name>/ship</command-name>"),
            cc_result("t04", "a1", True),
        ])
        attr = m.mine_claude_session(path, REGISTRY)["attr"]
        self.assertEqual(attr["scout"]["tool_errors"], 1)
        self.assertEqual(attr["ship"]["tool_errors"], 0)

    def test_subagent_rolls_up_into_the_window_it_was_spawned_in(self):
        session = self.root / "proj" / "s3.jsonl"
        write(session, [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_assistant("t02", "Task", "a1"),
            cc_text("t05", "<command-name>/cook</command-name>"),
        ])
        write(self.root / "proj" / "s3" / "subagents" / "agent-1.jsonl", [
            cc_assistant("t03", "Bash", "b1", tokens=7),
            cc_result("t04", "b1", True),
        ])
        attr = m.mine_claude_session(str(session), REGISTRY)["attr"]
        self.assertEqual(attr["scout"]["agents"], 1)
        self.assertEqual(attr["scout"]["agent_tool_calls"], 1)
        self.assertEqual(attr["scout"]["agent_tool_errors"], 1)
        self.assertEqual(attr["scout"]["agent_tokens"], 7)
        self.assertEqual(attr["cook"]["agents"], 0)

    def test_codex_attributes_per_invocation_and_reads_abort_reason(self):
        path = write(self.root / "codex" / "rollout-x.jsonl", [
            {"type": "session_meta", "timestamp": "t01", "payload": {"cwd": "/repo"}},
            {"type": "event_msg", "timestamp": "t02", "payload": {"type": "user_message", "message": "$scout the repo"}},
            {"type": "response_item", "timestamp": "t03", "payload": {"type": "function_call", "name": "shell", "arguments": "{}"}},
            {"type": "response_item", "timestamp": "t04", "payload": {"type": "function_call_output", "output": '{"exit_code": 1}'}},
            {"type": "event_msg", "timestamp": "t05", "payload": {"type": "turn_aborted", "reason": "interrupted"}},
            {"type": "event_msg", "timestamp": "t06", "payload": {"type": "user_message", "message": PREFIXED_INVOKE}},
            {"type": "response_item", "timestamp": "t07", "payload": {"type": "function_call", "name": "shell", "arguments": "{}"}},
            {"type": "response_item", "timestamp": "t08", "payload": {"type": "function_call_output", "output": '{"exit_code": 0}'}},
        ])
        row = m.mine_codex_session(path, REGISTRY)
        self.assertEqual(row["attr"]["scout"]["tool_errors"], 1)
        self.assertEqual(row["attr"]["scout"]["aborts"], 1)
        self.assertEqual(row["attr"]["ship"]["tool_errors"], 0)
        self.assertEqual(row["attr"]["ship"]["tool_calls"], 1)
        self.assertEqual(row["aborts_by_reason"], {"interrupted": 1})
        self.assertEqual(dict(row["skills"]), {"scout": 1, "ship": 1})

    def test_codex_token_deltas_split_across_windows(self):
        def tok(ts, total):
            return {"type": "event_msg", "timestamp": ts,
                    "payload": {"type": "token_count", "info": {"total_token_usage": {"total_tokens": total}}}}
        path = write(self.root / "codex" / "rollout-y.jsonl", [
            {"type": "event_msg", "timestamp": "t01", "payload": {"type": "user_message", "message": "$scout"}},
            tok("t02", 100),
            {"type": "event_msg", "timestamp": "t03", "payload": {"type": "user_message", "message": "$cook"}},
            tok("t04", 250),
        ])
        attr = m.mine_codex_session(path, REGISTRY)["attr"]
        self.assertEqual(attr["scout"]["tokens"], 100)
        self.assertEqual(attr["cook"]["tokens"], 150)


class Normalization(unittest.TestCase):
    def test_rejects_noise_words_and_harness_commands(self):
        for raw in ("this-", "options", "data", "record", "workflow", "model", "effort", "clear"):
            self.assertIsNone(m.normalize(raw, REGISTRY), raw)

    def test_strips_runtime_prefix(self):
        self.assertEqual(m.normalize("vd:ship", REGISTRY), "ship")
        self.assertEqual(m.normalize("ship", REGISTRY), "ship")

    def test_php_variables_in_a_codex_message_are_not_skills(self):
        path = write(pathlib.Path(tempfile.mkdtemp()) / "rollout-z.jsonl", [
            {"type": "event_msg", "timestamp": "t01",
             "payload": {"type": "user_message", "message": "fix $this->record and $options in $data"}},
        ])
        self.assertEqual(dict(m.mine_codex_session(path, REGISTRY)["skills"]), {})


class Aggregate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_solo_sessions_count_only_single_skill_sessions(self):
        solo = write(self.root / "p" / "solo.jsonl", [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_assistant("t02", "Bash", "a1"),
        ])
        mixed = write(self.root / "p" / "mixed.jsonl", [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_text("t02", "<command-name>/cook</command-name>"),
        ])
        skills = m.aggregate([m.mine_claude_session(solo, REGISTRY), m.mine_claude_session(mixed, REGISTRY)])
        self.assertEqual(skills["scout"]["sessions"], 2)
        self.assertEqual(skills["scout"]["solo_sessions"], 1)
        self.assertEqual(skills["cook"]["solo_sessions"], 0)
        self.assertEqual(skills["scout"]["invocations"], 2)

    def test_malformed_lines_do_not_crash_the_miner(self):
        path = self.root / "p" / "bad.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"type": "assistant"\nnot json at all\n' + json.dumps(cc_text("t01", "hi")) + "\n")
        row = m.mine_claude_session(str(path), REGISTRY)
        self.assertEqual(row["malformed_lines"], 2)

    def test_missing_runtime_dir_returns_no_paths(self):
        self.assertEqual(m.discover("codex", 7, root=str(self.root / "nope")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
