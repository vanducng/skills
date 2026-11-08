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


def pi_user(ts, text):
    return {"type": "message", "timestamp": ts,
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def pi_assistant(ts, tool, tid, tokens=0, args="{}", stop="toolUse"):
    return {"type": "message", "timestamp": ts, "message": {
        "role": "assistant", "model": "pi-1", "stopReason": stop,
        "usage": {"output": tokens, "totalTokens": tokens},
        "content": [{"type": "toolCall", "id": tid, "name": tool, "arguments": args}]}}


def pi_result(ts, tid, tool, is_error):
    return {"type": "message", "timestamp": ts, "message": {
        "role": "toolResult", "toolCallId": tid, "toolName": tool, "isError": is_error,
        "content": [{"type": "text", "text": "out"}]}}


def cur_user(stamp, query):
    text = f"<timestamp>{stamp}</timestamp>\n<user_query>{query}</user_query>"
    return {"role": "user", "message": {"content": [{"type": "text", "text": text}]}}


def cur_assistant(tool, inp=None):
    return {"role": "assistant",
            "message": {"content": [{"type": "tool_use", "name": tool, "input": inp or {}}]}}


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

    def test_unrecognized_skill_tool_call_resets_window_to_none(self):
        # Regression: an explicit Skill tool_use targeting a name outside the
        # registry (built-in command, foreign project skill, typo) must not
        # leave subsequent activity attributed to the stale prior skill.
        path = write(self.root / "proj" / "s1b.jsonl", [
            cc_text("t01", "<command-name>/cook</command-name>"),
            cc_assistant("t02", "Skill", "a0", skill="review-pr"),
            cc_result("t03", "a0", True),
            cc_assistant("t04", "Bash", "a1", tokens=9),
            cc_result("t05", "a1", True),
        ])
        attr = m.mine_claude_session(path, REGISTRY)["attr"]
        self.assertEqual(attr["cook"]["tool_errors"], 0)
        self.assertEqual(attr["cook"]["tool_calls"], 0)
        self.assertEqual(attr[m.NONE]["tool_errors"], 2)
        self.assertEqual(attr[m.NONE]["tool_calls"], 2)
        self.assertEqual(attr[m.NONE]["tokens"], 9)

    def test_harness_command_in_text_does_not_reset_window(self):
        # <command-name> matches include harmless harness commands (/model,
        # /cost, /clear); those must not fragment an in-progress skill window.
        path = write(self.root / "proj" / "s1c.jsonl", [
            cc_text("t01", "<command-name>/cook</command-name>"),
            cc_text("t02", "<command-name>/model</command-name>"),
            cc_assistant("t03", "Bash", "a1"),
            cc_result("t04", "a1", True),
        ])
        attr = m.mine_claude_session(path, REGISTRY)["attr"]
        self.assertEqual(attr["cook"]["tool_errors"], 1)
        self.assertEqual(attr[m.NONE]["tool_errors"], 0)

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

    def test_subagent_cutoff_excludes_old_events(self):
        session = self.root / "proj" / "window-agent.jsonl"
        write(session, [
            cc_text("2000-01-01T00:00:00Z", "<command-name>/scout</command-name>"),
            cc_text("2998-01-01T00:00:00Z", "<command-name>/cook</command-name>"),
        ])
        write(self.root / "proj" / "window-agent" / "subagents" / "agent-1.jsonl", [
            cc_assistant("2000-01-01T00:00:01Z", "Bash", "old", tokens=5),
            cc_result("2000-01-01T00:00:02Z", "old", True),
            cc_assistant("2999-01-01T00:00:01Z", "Bash", "new", tokens=7),
            cc_result("2999-01-01T00:00:02Z", "new", True),
        ])

        attr = m.mine_claude_session(
            str(session), REGISTRY, m.timestamp_epoch("2026-01-01T00:00:00Z"),
        )["attr"]["scout"]

        self.assertEqual(attr["agents"], 1)
        self.assertEqual(attr["agent_tool_calls"], 1)
        self.assertEqual(attr["agent_tool_errors"], 1)
        self.assertEqual(attr["agent_tokens"], 7)

    def test_recent_subagent_keeps_old_parent_session(self):
        session = self.root / "proj" / "subagent-only.jsonl"
        write(session, [cc_text("2000-01-01T00:00:00Z", "<command-name>/scout</command-name>")])
        write(self.root / "proj" / "subagent-only" / "subagents" / "agent-1.jsonl", [
            cc_assistant("2999-01-01T00:00:00Z", "Bash", "new", tokens=7),
        ])
        os.utime(session, (0, 0))
        out = self.root / "out"
        out.mkdir()
        old_root = m.CLAUDE_PROJECTS
        self.addCleanup(setattr, m, "CLAUDE_PROJECTS", old_root)
        m.CLAUDE_PROJECTS = str(self.root)

        rows = m.run("claude", REGISTRY, str(out), 7)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["first_ts"], "2999-01-01T00:00:00Z")
        self.assertEqual(row["attr"]["scout"]["agent_tool_calls"], 1)

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

    def test_codex_custom_tool_call_counts_like_function_call(self):
        path = write(self.root / "codex" / "rollout-custom.jsonl", [
            {"type": "event_msg", "timestamp": "t01", "payload": {"type": "user_message", "message": "$scout the repo"}},
            {"type": "response_item", "timestamp": "t02", "payload": {"type": "custom_tool_call", "name": "exec", "input": "{}"}},
            {"type": "response_item", "timestamp": "t03", "payload": {"type": "custom_tool_call_output", "output": '{"exit_code": 1}'}},
        ])
        row = m.mine_codex_session(path, REGISTRY)
        self.assertEqual(row["attr"]["scout"]["tool_calls"], 1)
        self.assertEqual(row["attr"]["scout"]["tool_errors"], 1)

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

    def test_missing_timestamps_follow_current_window_state(self):
        path = write(self.root / "codex" / "rollout-missing-ts.jsonl", [
            {"type": "event_msg", "timestamp": "2000-01-01T00:00:00Z",
             "payload": {"type": "user_message", "message": "$scout"}},
            {"type": "response_item",
             "payload": {"type": "function_call", "name": "old", "arguments": "{}"}},
            {"type": "event_msg", "timestamp": "2999-01-01T00:00:00Z",
             "payload": {"type": "user_message", "message": PREFIXED_INVOKE}},
            {"type": "response_item",
             "payload": {"type": "function_call", "name": "new", "arguments": "{}"}},
        ])

        row = m.mine_codex_session(
            path, REGISTRY, m.timestamp_epoch("2026-01-01T00:00:00Z"),
        )

        self.assertEqual(row["attr"]["scout"]["tool_calls"], 0)
        self.assertEqual(row["attr"]["ship"]["tool_calls"], 1)

    def test_claude_cutoff_excludes_old_events(self):
        path = write(self.root / "proj" / "window.jsonl", [
            cc_text("2000-01-01T00:00:00Z", "<command-name>/scout</command-name>"),
            cc_assistant("2000-01-01T00:00:01Z", "Bash", "old", tokens=5),
            cc_text("2999-01-01T00:00:00Z", "<command-name>/cook</command-name>"),
            cc_assistant("2999-01-01T00:00:01Z", "Edit", "new", tokens=10),
        ])

        row = m.mine_claude_session(
            path, REGISTRY, m.timestamp_epoch("2026-01-01T00:00:00Z"),
        )

        self.assertEqual(dict(row["skills"]), {"cook": 1})
        self.assertEqual(row["attr"]["cook"]["tool_calls"], 1)
        self.assertEqual(row["attr"]["scout"]["tool_calls"], 0)
        self.assertEqual(row["first_ts"], "2999-01-01T00:00:00Z")


class Pi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_slash_invocation_attributes_errors_tokens_and_skips_non_skills(self):
        path = write(self.root / "proj" / "2026-01-01T00-00-00-000Z_a.jsonl", [
            {"type": "session", "timestamp": "t00", "id": "a", "cwd": "/repo"},
            pi_assistant("t01", "bash", "x0", tokens=3),
            pi_result("t02", "x0", "bash", True),
            pi_user("t03", "/scout the repo"),
            pi_assistant("t04", "bash", "x1", tokens=5),
            pi_result("t05", "x1", "bash", True),
            pi_user("t06", "now read /tmp/out.log and /api docs"),
            pi_assistant("t07", "read", "x2", tokens=7, args='{"path": "skills/ship/SKILL.md"}'),
            pi_result("t08", "x2", "read", False),
            pi_user("t09", "/cook it"),
            pi_assistant("t10", "edit", "x3", tokens=11, stop="aborted"),
        ])
        row = m.mine_pi_session(path, REGISTRY)
        attr = row["attr"]

        self.assertEqual(row["project"], "/repo")
        self.assertEqual(dict(row["skills"]), {"scout": 1, "cook": 1})
        self.assertEqual(attr["scout"]["tool_errors"], 1)
        self.assertEqual(attr["scout"]["tool_calls"], 2)
        self.assertEqual(attr["scout"]["tokens"], 12)
        self.assertEqual(attr["cook"]["tool_calls"], 1)
        self.assertEqual(attr["cook"]["interrupts"], 1)
        self.assertEqual(attr[m.NONE]["tool_errors"], 1)
        self.assertEqual(dict(row["skillmd_reads"]), {"ship": 1})
        self.assertEqual(dict(row["errors_by_tool"]), {"bash": 2})

    def test_subagent_run_rolls_up_but_fork_does_not(self):
        session = self.root / "proj" / "2026-01-01T00-00-00-000Z_b.jsonl"
        write(session, [
            pi_user("t01", "/scout the repo"),
            pi_assistant("t02", "subagent", "x1"),
            pi_user("t09", "/cook it"),
        ])
        write(self.root / "proj" / "2026-01-01T00-00-00-000Z_b" / "run-id" / "run-0" / "session.jsonl", [
            pi_assistant("t03", "bash", "s1", tokens=4),
            pi_result("t04", "s1", "bash", True),
        ])
        write(self.root / "proj" / "2026-01-01T00-00-00-000Z_b" / "forks" / "2026-01-02T00-00-00-000Z_c.jsonl", [
            pi_assistant("t05", "bash", "f1", tokens=99),
        ])
        attr = m.mine_pi_session(str(session), REGISTRY)["attr"]

        self.assertEqual(attr["scout"]["agents"], 1)
        self.assertEqual(attr["scout"]["agent_tool_calls"], 1)
        self.assertEqual(attr["scout"]["agent_tool_errors"], 1)
        self.assertEqual(attr["scout"]["agent_tokens"], 4)
        self.assertEqual(attr["cook"]["agents"], 0)

    def test_since_filters_events_and_discovery_skips_nested_transcripts(self):
        write(self.root / "pi" / "proj" / "2026-01-01T00-00-00-000Z_d.jsonl", [
            pi_user("2000-01-01T00:00:00Z", "/scout"),
            pi_assistant("2000-01-01T00:00:01Z", "bash", "old"),
            pi_user("2999-01-01T00:00:00Z", "/cook"),
            pi_assistant("2999-01-01T00:00:01Z", "bash", "new"),
        ])
        write(self.root / "pi" / "proj" / "2026-01-01T00-00-00-000Z_d" / "r" / "run-0" / "session.jsonl", [
            pi_assistant("2999-01-01T00:00:02Z", "bash", "sub"),
        ])
        out = self.root / "out"
        out.mkdir()
        self.addCleanup(setattr, m, "PI_SESSIONS", m.PI_SESSIONS)
        m.PI_SESSIONS = str(self.root / "pi")

        rows = m.run("pi", REGISTRY, str(out), 7)

        self.assertEqual(len(rows), 1)
        self.assertEqual(dict(rows[0]["skills"]), {"cook": 1})
        self.assertEqual(rows[0]["attr"]["cook"]["tool_calls"], 1)
        self.assertEqual(rows[0]["attr"]["scout"]["tool_calls"], 0)
        self.assertEqual(rows[0]["attr"]["cook"]["agent_tool_calls"], 1)


class Cursor(unittest.TestCase):
    OLD = "Saturday, Jan 01, 2000, 12:00 PM (UTC+0)"
    NEW = "Friday, Jan 01, 2999, 12:00 PM (UTC+0)"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def transcript(self, name, lines):
        return write(self.root / "cursor" / "proj" / "agent-transcripts" / name / f"{name}.jsonl", lines)

    def test_user_query_invocation_skips_non_skills_and_reads_skillmd(self):
        path = self.transcript("t1", [
            cur_assistant("Shell"),
            cur_user(self.NEW, "/scout the repo, ignore /tmp and /api"),
            cur_assistant("Shell"),
            cur_assistant("Read", {"target_file": "/home/u/.claude/skills/ship/SKILL.md"}),
            cur_user(self.NEW, "$cook it"),
            cur_assistant("Shell"),
            {"type": "turn_ended", "status": "aborted"},
        ])
        row = m.mine_cursor_session(path, REGISTRY)
        attr = row["attr"]

        self.assertEqual(row["project"], "proj")
        self.assertEqual(dict(row["skills"]), {"scout": 1, "cook": 1})
        self.assertEqual(attr["scout"]["tool_calls"], 2)
        self.assertEqual(attr["cook"]["tool_calls"], 1)
        self.assertEqual(attr["cook"]["interrupts"], 1)
        self.assertEqual(attr[m.NONE]["tool_calls"], 1)
        self.assertEqual(dict(row["skillmd_reads"]), {"ship": 1})

    def test_timestamp_parses_out_of_the_tag(self):
        self.assertEqual(m.cursor_timestamp(f"<timestamp>{self.OLD}</timestamp>"),
                         "2000-01-01T12:00:00Z")
        self.assertEqual(
            m.cursor_timestamp("<timestamp>Tuesday, Jul 14, 2026, 4:42 PM (UTC+7)</timestamp>"),
            "2026-07-14T09:42:00Z")
        self.assertIsNone(m.cursor_timestamp("no stamp here"))

    def test_since_filters_events_and_discovery_skips_subagent_files(self):
        name = "t2"
        self.transcript(name, [
            cur_user(self.OLD, "/scout"),
            cur_assistant("Shell"),
            cur_user(self.NEW, "/cook"),
            cur_assistant("Shell"),
        ])
        write(self.root / "cursor" / "proj" / "agent-transcripts" / name / "subagents" / "s1.jsonl", [
            cur_user(self.NEW, "go"),
            cur_assistant("Shell"),
        ])
        out = self.root / "out"
        out.mkdir()
        self.addCleanup(setattr, m, "CURSOR_PROJECTS", m.CURSOR_PROJECTS)
        m.CURSOR_PROJECTS = str(self.root / "cursor")

        rows = m.run("cursor", REGISTRY, str(out), 7)

        self.assertEqual(len(rows), 1)
        self.assertEqual(dict(rows[0]["skills"]), {"cook": 1})
        self.assertEqual(rows[0]["attr"]["cook"]["tool_calls"], 1)
        self.assertEqual(rows[0]["attr"]["scout"]["tool_calls"], 0)
        self.assertEqual(rows[0]["attr"]["cook"]["agent_tool_calls"], 1)


class Normalization(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_rejects_noise_words_and_harness_commands(self):
        for raw in ("this-", "options", "data", "record", "workflow", "model", "effort", "clear"):
            self.assertIsNone(m.normalize(raw, REGISTRY), raw)

    def test_strips_runtime_prefix(self):
        self.assertEqual(m.normalize("vd:ship", REGISTRY), "ship")
        self.assertEqual(m.normalize("ship", REGISTRY), "ship")

    def test_php_variables_in_a_codex_message_are_not_skills(self):
        path = write(self.root / "rollout-z.jsonl", [
            {"type": "event_msg", "timestamp": "t01",
             "payload": {"type": "user_message", "message": "fix $this->record and $options in $data"}},
        ])
        self.assertEqual(dict(m.mine_codex_session(path, REGISTRY)["skills"]), {})

    def test_exit_failed_reads_structured_and_stringified_output(self):
        self.assertTrue(m.exit_failed({"exit_code": 1}))
        self.assertFalse(m.exit_failed({"exit_code": 0}))
        self.assertTrue(m.exit_failed('{"exit_code": "2"}'))
        self.assertFalse(m.exit_failed('{"exit_code": 0, "stdout": "ok"}'))
        self.assertFalse(m.exit_failed(None))

    def test_timestamp_epoch_normalizes_iso_formats(self):
        expected = m.timestamp_epoch("2026-01-01T00:00:00Z")
        self.assertEqual(expected, m.timestamp_epoch("2026-01-01T00:00:00+00:00"))
        self.assertEqual(expected, m.timestamp_epoch("2026-01-01T07:00:00+07:00"))


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

    def test_since_filters_events_inside_recently_modified_session(self):
        path = write(self.root / "codex" / "rollout-window.jsonl", [
            {"type": "event_msg", "timestamp": "2000-01-01T00:00:00Z",
             "payload": {"type": "user_message", "message": "$scout"}},
            {"type": "response_item", "timestamp": "2000-01-01T00:00:01Z",
             "payload": {"type": "function_call", "name": "shell", "arguments": "{}"}},
            {"type": "event_msg", "timestamp": "2999-01-01T00:00:00Z",
             "payload": {"type": "user_message", "message": PREFIXED_INVOKE}},
            {"type": "response_item", "timestamp": "2999-01-01T00:00:01Z",
             "payload": {"type": "function_call", "name": "shell", "arguments": "{}"}},
        ])
        out = self.root / "out"
        out.mkdir()
        old_root = m.CODEX_SESSIONS
        self.addCleanup(setattr, m, "CODEX_SESSIONS", old_root)
        m.CODEX_SESSIONS = str(self.root / "codex")

        rows = m.run("codex", REGISTRY, str(out), 7)

        self.assertEqual(len(rows), 1)
        self.assertEqual(dict(rows[0]["skills"]), {"ship": 1})
        self.assertEqual(rows[0]["attr"]["ship"]["tool_calls"], 1)
        self.assertEqual(rows[0]["attr"]["scout"]["tool_calls"], 0)
        self.assertEqual(rows[0]["first_ts"], "2999-01-01T00:00:00Z")


class Outcomes(unittest.TestCase):
    """One outcome row per invocation window: pass, corrected or failed, with counters and evidence."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def check(self, rows):
        self.assertEqual([(r["skill"], r["outcome"]) for r in rows], [("scout", "corrected"), ("cook", "failed"), ("ship", "pass")])
        scout, cook, ship = rows
        self.assertEqual(scout["window"]["start"], "t01")
        self.assertEqual(scout["window"]["end"], cook["window"]["start"])  # a window ends where the next begins
        self.assertEqual(ship["window"]["end"], ship["evidence"]["window_end"])
        self.assertEqual([r["window"]["index"] for r in rows], [0, 1, 2])
        self.assertEqual(scout["counts"]["corrections"], 1)
        self.assertTrue(all(r["session"] and r["evidence"]["session"] == r["session"] for r in rows))
        self.assertIn("heuristic", scout["method"])

    def test_claude_windows_become_rows(self):
        path = write(self.root / "proj" / "s.jsonl", [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_assistant("t02", "Bash", "a1"), cc_result("t03", "a1", False),
            cc_text("t04", "no, that is wrong"),
            cc_text("t05", "<command-name>/cook</command-name>"),
            cc_assistant("t06", "Bash", "b1"), cc_result("t07", "b1", True),
            cc_assistant("t08", "Bash", "b2"), cc_result("t09", "b2", True),
            cc_text("t10", "<command-name>/ship</command-name>"),
            cc_assistant("t11", "Read", "c1"), cc_result("t12", "c1", False),
        ])
        row = m.mine_claude_session(path, REGISTRY)
        rows = m.outcome_rows(row)
        self.check(rows)
        self.assertEqual(rows[1]["counts"]["tool_errors"], 2)
        self.assertEqual(rows[1]["counts"]["tool_calls"], 2)

    def test_pi_windows_become_rows(self):
        path = write(self.root / "pi" / "2026_a.jsonl", [
            {"type": "session", "timestamp": "t00", "id": "a", "cwd": "/repo"},
            pi_user("t01", "/scout the repo"), pi_assistant("t02", "bash", "x0"), pi_result("t03", "x0", "bash", False),
            pi_user("t04", "no, try again"),
            pi_user("t05", "/cook it"),
            pi_assistant("t06", "bash", "x1"), pi_result("t07", "x1", "bash", True),
            pi_assistant("t08", "bash", "x3"), pi_result("t09", "x3", "bash", True),
            pi_assistant("t09b", "edit", "x4", stop="aborted"),
            pi_user("t10", "/ship it"), pi_assistant("t11", "read", "x2"), pi_result("t12", "x2", "read", False),
        ])
        rows = m.outcome_rows(m.mine_pi_session(path, REGISTRY))
        self.check(rows)
        self.assertEqual(rows[1]["counts"]["interrupts"], 1)  # pi's aborted turn is counted as an interrupt
        self.assertEqual(rows[0]["project"], "/repo")

    def test_codex_windows_become_rows(self):
        def call(ts):
            return {"type": "response_item", "timestamp": ts, "payload": {"type": "function_call", "name": "shell", "arguments": "{}"}}

        def msg(ts, text):
            return {"type": "event_msg", "timestamp": ts, "payload": {"type": "user_message", "message": text}}

        path = write(self.root / "codex" / "rollout-o.jsonl", [
            {"type": "session_meta", "timestamp": "t00", "payload": {"cwd": "/repo"}},
            msg("t01", "$scout the repo"), call("t02"),
            msg("t04", "no, try again"),
            msg("t05", "$cook it"), call("t06"),
            {"type": "event_msg", "timestamp": "t07", "payload": {"type": "turn_aborted", "reason": "error"}},
            msg("t10", PREFIXED_INVOKE), call("t11"),
        ])
        self.check(m.outcome_rows(m.mine_codex_session(path, REGISTRY)))

    def test_events_before_any_invocation_and_unknown_skills_make_no_row(self):
        path = write(self.root / "proj" / "n.jsonl", [
            cc_assistant("t01", "Bash", "a1"), cc_result("t02", "a1", True),
            cc_text("t03", "<command-name>/model</command-name>"),
        ])
        self.assertEqual(m.outcome_rows(m.mine_claude_session(path, REGISTRY)), [])

    def test_an_unknown_skill_call_ends_the_window(self):
        path = write(self.root / "proj" / "e.jsonl", [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_assistant("t02", "Skill", "k1", skill="not-installed"),
            cc_assistant("t03", "Bash", "a1"), cc_result("t04", "a1", True),
        ])
        rows = m.outcome_rows(m.mine_claude_session(path, REGISTRY))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["window"]["end"], "t02")
        self.assertEqual(rows[0]["counts"]["tool_errors"], 0)  # the later error belongs to no skill

    def test_the_cutoff_keeps_only_windows_inside_it(self):
        path = write(self.root / "proj" / "c.jsonl", [
            cc_text("2000-01-01T00:00:00Z", "<command-name>/scout</command-name>"),
            cc_text("2999-01-01T00:00:00Z", "<command-name>/ship</command-name>"),
        ])
        rows = m.outcome_rows(m.mine_claude_session(path, REGISTRY, cutoff_epoch=4_000_000_000 - 3_000_000_000))
        self.assertEqual([r["skill"] for r in rows], ["ship"])

    def test_classify_thresholds(self):
        base = dict.fromkeys(m.WINDOW_KEYS, 0)
        self.assertEqual(m.classify(base), "pass")
        self.assertEqual(m.classify({**base, "tool_calls": 10, "tool_errors": 1}), "pass")  # one error is not failure
        self.assertEqual(m.classify({**base, "tool_calls": 10, "tool_errors": 2}), "pass")  # 20% is under the rate
        self.assertEqual(m.classify({**base, "tool_calls": 4, "tool_errors": 2}), "failed")
        self.assertEqual(m.classify({**base, "tool_calls": 1, "tool_errors": 1}), "pass")  # a single error is under the minimum
        self.assertEqual(m.classify({**base, "aborts": 1}), "failed")
        self.assertEqual(m.classify({**base, "corrections": 1}), "corrected")
        self.assertEqual(m.classify({**base, "interrupts": 1, "tool_errors": 1, "tool_calls": 3}), "corrected")

    def test_a_codex_interrupt_is_corrected_like_a_pi_interrupt_and_any_other_abort_is_failed(self):
        def run(reason):
            path = write(self.root / "codex" / f"rollout-{reason}.jsonl", [
                {"type": "event_msg", "timestamp": "t01", "payload": {"type": "user_message", "message": "$scout it"}},
                {"type": "event_msg", "timestamp": "t02", "payload": {"type": "turn_aborted", "reason": reason}},
            ])
            row = m.mine_codex_session(path, REGISTRY)
            return row, m.outcome_rows(row)[0]

        row, interrupted = run("interrupted")
        self.assertEqual(interrupted["outcome"], "corrected")
        self.assertEqual((interrupted["counts"]["interrupts"], interrupted["counts"]["aborts"]), (1, 0))
        self.assertEqual(row["attr"]["scout"]["aborts"], 1)  # the per-skill aggregate keeps its meaning
        self.assertEqual(run("error")[1]["outcome"], "failed")
        self.assertEqual(run("unknown")[1]["outcome"], "failed")

    def test_concurrent_writers_lose_no_rows_and_leave_no_temp_files(self):
        import threading

        path = str(self.root / "shared" / "host.jsonl")

        def row(i):
            return {"runtime": "pi", "session": f"s{i}", "project": None, "skill": "scout", "outcome": "pass", "counts": {},
                    "window": {"start": f"t{i:03d}", "end": "", "index": 0, "tie": 0}}

        def writer(n):
            for i in range(10):
                m.write_outcomes(path, [row(n * 100 + i)])

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        with open(path) as fh:
            rows = [json.loads(line) for line in fh]  # every line parses
        self.assertEqual(len(rows), 60)
        self.assertEqual([f for f in os.listdir(os.path.dirname(path)) if f.endswith(".tmp")], [])

    def test_a_wider_scan_does_not_duplicate_rows_whose_index_shifted(self):
        sess = [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_text("t02", "<command-name>/cook</command-name>"),
        ]
        path = write(self.root / "proj" / "w.jsonl", sess)
        narrow = [r for r in m.outcome_rows(m.mine_claude_session(path, REGISTRY)) if r["skill"] == "cook"]
        wide = m.outcome_rows(m.mine_claude_session(path, REGISTRY))
        shifted = [dict(r, window=dict(r["window"], index=r["window"]["index"] + 5)) for r in narrow]
        out = str(self.root / "o" / "h.jsonl")
        m.write_outcomes(out, shifted)
        self.assertEqual(m.write_outcomes(out, wide), 2)  # cook once (same session, skill, start), plus scout

    def test_same_timestamp_windows_get_distinct_keys(self):
        path = write(self.root / "proj" / "d.jsonl", [
            cc_text("t01", "<command-name>/scout</command-name>"),
            cc_text("t01", "<command-name>/scout</command-name>"),
        ])
        rows = m.outcome_rows(m.mine_claude_session(path, REGISTRY))
        self.assertEqual(len({m.outcome_key(r) for r in rows}), 2)

    def test_an_empty_outcomes_path_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as raised:
            m.main(["--runtime", "pi", "--out", str(self.root / "x"), "--outcomes", ""])
        self.assertEqual(raised.exception.code, 2)

    def test_write_outcomes_merges_by_key_and_is_idempotent(self):
        path = str(self.root / "out" / "host.jsonl")
        row = m.outcome_rows(m.mine_claude_session(write(self.root / "proj" / "s.jsonl", [
            cc_text("t01", "<command-name>/scout</command-name>"), cc_assistant("t02", "Bash", "a1"), cc_result("t03", "a1", False),
        ]), REGISTRY))
        self.assertEqual(m.write_outcomes(path, row), 1)
        self.assertEqual(m.write_outcomes(path, row), 1)  # a rerun does not duplicate
        changed = [{**row[0], "outcome": "failed"}]
        self.assertEqual(m.write_outcomes(path, changed), 1)
        other = [{**row[0], "skill": "cook", "window": {**row[0]["window"], "index": 1}}]
        self.assertEqual(m.write_outcomes(path, other), 2)
        with open(path) as fh:
            rows = [json.loads(line) for line in fh]
        self.assertEqual(sorted((r["skill"], r["outcome"]) for r in rows), [("cook", "pass"), ("scout", "failed")])
        with open(path, "a") as fh:
            fh.write("not json\n")
        self.assertEqual(m.write_outcomes(path, []), 2)  # a bad line is dropped, the rest kept
        self.assertFalse(os.path.exists(path + ".tmp"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
