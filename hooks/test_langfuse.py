#!/usr/bin/env python3
"""Behavioral tests for the Langfuse exporter (lib/vd_langfuse.py,
lib/vd_transcripts.py, langfuse-trace.py).

Offline by design: no test contacts Langfuse. Export runs the real script as a
subprocess against a local HTTP server standing in for the OTLP endpoint, so the
actual urllib POST path, span-building, transcript parsing, incremental state,
and the fail-open contract are all asserted without credentials or a network.

Run: python3 -m unittest hooks.test_langfuse
 or: python3 hooks/test_langfuse.py
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, 'lib'))

import vd_langfuse as lf  # noqa: E402
import vd_transcripts as tx  # noqa: E402

TRACE_SCRIPT = os.path.join(HOOKS_DIR, 'langfuse-trace.py')


def write_jsonl(path, records):
    with open(path, 'w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record) + '\n')
    return path


CLAUDE_RECORDS = [
    {'type': 'user', 'timestamp': '2026-08-01T10:00:00.000Z', 'sessionId': 'sess-claude',
     'cwd': '/tmp/proj', 'message': {'role': 'user', 'content': 'hello there'}},
    {'type': 'assistant', 'timestamp': '2026-08-01T10:00:05.000Z', 'sessionId': 'sess-claude',
     'message': {'role': 'assistant', 'model': 'claude-opus-5',
                 'usage': {'input_tokens': 10, 'output_tokens': 20,
                           'cache_read_input_tokens': 5, 'cache_creation_input_tokens': 3},
                 'content': [{'type': 'text', 'text': 'hi back'},
                             {'type': 'tool_use', 'id': 'tu1', 'name': 'Bash',
                              'input': {'command': 'ls'}}]}},
    {'type': 'user', 'timestamp': '2026-08-01T10:00:06.000Z', 'sessionId': 'sess-claude',
     'message': {'role': 'user', 'content': [
         {'type': 'tool_result', 'tool_use_id': 'tu1', 'content': 'file.txt'}]}},
]

CODEX_RECORDS = [
    {'type': 'session_meta', 'timestamp': '2026-08-01T10:00:00.000Z',
     'payload': {'session_id': 'sess-codex', 'cwd': '/tmp/proj'}},
    {'type': 'turn_context', 'timestamp': '2026-08-01T10:00:00.500Z',
     'payload': {'model': 'gpt-5.6-sol'}},
    {'type': 'event_msg', 'timestamp': '2026-08-01T10:00:01.000Z',
     'payload': {'type': 'user_message', 'message': 'do the thing'}},
    {'type': 'response_item', 'timestamp': '2026-08-01T10:00:02.000Z',
     'payload': {'type': 'custom_tool_call', 'call_id': 'c1', 'name': 'exec', 'input': 'ls'}},
    {'type': 'response_item', 'timestamp': '2026-08-01T10:00:03.000Z',
     'payload': {'type': 'custom_tool_call_output', 'call_id': 'c1', 'output': 'file.txt'}},
    {'type': 'event_msg', 'timestamp': '2026-08-01T10:00:04.000Z',
     'payload': {'type': 'token_count', 'info': {'last_token_usage': {
         'input_tokens': 100, 'output_tokens': 50, 'cached_input_tokens': 25,
         'reasoning_output_tokens': 7}}}},
    {'type': 'event_msg', 'timestamp': '2026-08-01T10:00:05.000Z',
     'payload': {'type': 'task_complete', 'last_agent_message': 'done',
                 'started_at': 1785700000, 'completed_at': 1785700005}},
]

PI_RECORDS = [
    {'type': 'session', 'id': 'sess-pi', 'timestamp': '2026-08-01T10:00:00.000Z',
     'cwd': '/tmp/proj'},
    {'type': 'model_change', 'timestamp': '2026-08-01T10:00:00.100Z', 'modelId': 'gpt-5.6-sol'},
    {'type': 'message', 'timestamp': '2026-08-01T10:00:01.000Z',
     'message': {'role': 'user', 'content': [{'type': 'text', 'text': 'check nodes'}]}},
    {'type': 'message', 'timestamp': '2026-08-01T10:00:02.000Z',
     'message': {'role': 'assistant', 'model': 'gpt-5.6-sol',
                 'usage': {'input': 200, 'output': 30, 'cacheRead': 10, 'reasoning': 4,
                           'cost': {'total': 0.125}},
                 'content': [{'type': 'text', 'text': 'here you go'},
                             {'type': 'toolCall', 'id': 'tc1', 'name': 'bash',
                              'arguments': {'cmd': 'kubectl top nodes'}}]}},
    {'type': 'message', 'timestamp': '2026-08-01T10:00:03.000Z',
     'message': {'role': 'toolResult', 'content': [{'type': 'text', 'text': 'node1 ok'}]}},
]


class TranscriptParsingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_claude_turn_tools_and_usage(self):
        path = write_jsonl(os.path.join(self.tmp, 'c.jsonl'), CLAUDE_RECORDS)
        session = tx.parse(path, 'claude-code')
        self.assertEqual(session.agent, 'claude-code')
        self.assertEqual(session.id, 'sess-claude')
        self.assertEqual(len(session.turns), 1, 'tool_result must not open a new turn')
        turn = session.turns[0]
        self.assertEqual(turn.user_input, 'hello there')
        self.assertEqual(turn.output, 'hi back')
        self.assertEqual(turn.model, 'claude-opus-5')
        self.assertEqual(turn.usage['input'], 10)
        self.assertEqual(turn.usage['cache_read'], 5)
        self.assertEqual(turn.usage['cache_write'], 3)
        self.assertEqual(len(turn.tools), 1)
        self.assertEqual(turn.tools[0].name, 'Bash')
        self.assertEqual(turn.tools[0].output, 'file.txt', 'tool span must be closed by its result')

    def test_codex_turn_boundaries_and_usage(self):
        path = write_jsonl(os.path.join(self.tmp, 'rollout-x.jsonl'), CODEX_RECORDS)
        session = tx.parse(path, 'codex')
        self.assertEqual(session.id, 'sess-codex')
        self.assertEqual(len(session.turns), 1)
        turn = session.turns[0]
        self.assertEqual(turn.user_input, 'do the thing')
        self.assertEqual(turn.output, 'done')
        self.assertEqual(turn.model, 'gpt-5.6-sol')
        self.assertEqual(turn.usage['input'], 100)
        self.assertEqual(turn.usage['reasoning'], 7)
        self.assertEqual(turn.tools[0].output, 'file.txt')
        # task_complete supplies authoritative start/end epochs (seconds -> ns).
        self.assertEqual(turn.start_ns, 1785700000 * tx.NS)
        self.assertEqual(turn.end_ns, 1785700005 * tx.NS)

    def test_pi_cost_and_tool_pairing(self):
        path = write_jsonl(os.path.join(self.tmp, '2026_sess-pi.jsonl'), PI_RECORDS)
        session = tx.parse(path, 'pi')
        self.assertEqual(session.id, 'sess-pi')
        turn = session.turns[0]
        self.assertEqual(turn.user_input, 'check nodes')
        self.assertAlmostEqual(turn.cost, 0.125)
        self.assertEqual(turn.usage['input'], 200)
        self.assertEqual(turn.tools[0].name, 'bash')
        self.assertEqual(turn.tools[0].output, 'node1 ok')

    def test_pi_tool_result_without_text_does_not_shift_later_results(self):
        """A result with no text block must still close its call; otherwise the
        next result re-matches it and every later tool output is off by one."""
        records = list(PI_RECORDS[:4]) + [
            {'type': 'message', 'timestamp': '2026-08-01T10:00:02.500Z',
             'message': {'role': 'assistant', 'model': 'gpt-5.6-sol',
                         'content': [{'type': 'toolCall', 'id': 'tc2', 'name': 'read',
                                      'arguments': {'path': '/x'}}]}},
            # first result carries no text block at all
            {'type': 'message', 'timestamp': '2026-08-01T10:00:03.000Z',
             'message': {'role': 'toolResult', 'content': [{'type': 'image'}]}},
            {'type': 'message', 'timestamp': '2026-08-01T10:00:04.000Z',
             'message': {'role': 'toolResult', 'content': [{'type': 'text', 'text': 'second'}]}},
        ]
        path = write_jsonl(os.path.join(self.tmp, 'pi2.jsonl'), records)
        turn = tx.parse(path, 'pi').turns[0]
        self.assertEqual([call.name for call in turn.tools], ['bash', 'read'])
        self.assertEqual(turn.tools[0].output, '', 'text-less result still closes its call')
        self.assertEqual(turn.tools[1].output, 'second', 'later results must not shift')

    def test_detect_agent_normalizes_windows_separators(self):
        self.assertEqual(
            tx.detect_agent('/x/.codex/sessions/2026/rollout-a.jsonl'.replace('/', os.sep)),
            'codex')

    def test_malformed_lines_do_not_raise(self):
        path = os.path.join(self.tmp, 'bad.jsonl')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('{"type": "user"\n')          # truncated JSON
            handle.write('\n')                          # blank
            handle.write(json.dumps(CLAUDE_RECORDS[0]) + '\n')
        session = tx.parse(path, 'claude-code')
        self.assertEqual(len(session.turns), 1)

    def test_detect_agent_from_path(self):
        self.assertEqual(tx.detect_agent('/x/.codex/sessions/2026/rollout-a.jsonl'), 'codex')
        self.assertEqual(tx.detect_agent('/x/.pi/agent/sessions/p/s.jsonl'), 'pi')
        self.assertEqual(tx.detect_agent('/x/.claude/projects/p/s.jsonl'), 'claude-code')
        self.assertIsNone(tx.detect_agent('/x/somewhere/s.jsonl'))

    def test_detect_agent_from_content_when_path_is_unknown(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for name, records, expected in (
                ('a.jsonl', CLAUDE_RECORDS, 'claude-code'),
                ('b.jsonl', CODEX_RECORDS, 'codex'),
                ('c.jsonl', PI_RECORDS, 'pi')):
            path = write_jsonl(os.path.join(tmp, name), records)
            self.assertIsNone(tx.detect_agent(path), 'path carries no agent hint')
            self.assertEqual(tx.detect_agent_by_content(path), expected)
            self.assertEqual(tx.parse(path).agent, expected)

    def test_unrecognisable_transcript_raises(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = write_jsonl(os.path.join(tmp, 'x.jsonl'), [{'type': 'mystery', 'a': 1}])
        with self.assertRaises(ValueError):
            tx.parse(path)


class ConfigTests(unittest.TestCase):
    def test_envrc_fallback_reads_literals_only(self):
        with tempfile.NamedTemporaryFile('w', suffix='.envrc', delete=False) as handle:
            handle.write('export LANGFUSE_PUBLIC_KEY="pk-lf-abc"\n')
            handle.write("export LANGFUSE_SECRET_KEY='sk-lf-def'\n")
            handle.write('export LANGFUSE_BASE_URL=https://example.langfuse.com\n')
            handle.write('export LANGFUSE_IGNORED=$(gopass show secret)\n')
            handle.write('export UNRELATED_TOKEN="nope"\n')
            path = handle.name
        self.addCleanup(os.unlink, path)
        found = lf.load_envrc(path)
        self.assertEqual(found['LANGFUSE_PUBLIC_KEY'], 'pk-lf-abc')
        self.assertEqual(found['LANGFUSE_SECRET_KEY'], 'sk-lf-def')
        self.assertEqual(found['LANGFUSE_BASE_URL'], 'https://example.langfuse.com')
        self.assertNotIn('LANGFUSE_IGNORED', found, 'shell-expanded values must be skipped')
        self.assertNotIn('UNRELATED_TOKEN', found)

    def test_config_disabled_without_keys(self):
        config = lf.load_config({'VD_LANGFUSE_ENVRC': '/nonexistent/.envrc'})
        self.assertFalse(config.enabled)

    def test_env_wins_over_envrc(self):
        config = lf.load_config({'LANGFUSE_PUBLIC_KEY': 'pk-env',
                                 'LANGFUSE_SECRET_KEY': 'sk-env'})
        self.assertTrue(config.enabled)
        self.assertEqual(config.public_key, 'pk-env')

    def test_deterministic_ids_and_seed_separation(self):
        first = lf.trace_id_for('sess-a')
        self.assertEqual(first, lf.trace_id_for('sess-a'), 'same session -> same trace')
        self.assertNotEqual(first, lf.trace_id_for('sess-b'))
        self.assertNotEqual(first, lf.trace_id_for('sess-a', seed='v2'))
        self.assertEqual(len(first), 32)
        self.assertEqual(len(lf.span_id_for('sess-a', 'turn:0')), 16)

    def test_list_attribute_elements_are_capped(self):
        attribute = lf._attr('langfuse.trace.tags', ['x' * 5000, 'ok'])
        values = attribute['value']['arrayValue']['values']
        self.assertEqual(len(values[0]['stringValue']), lf.ATTR_ELEMENT_MAX)
        self.assertEqual(values[1]['stringValue'], 'ok')

    def test_usage_merge_accepts_floats_and_rejects_junk(self):
        merged = tx._merge_usage({'input': 5}, {'input': 2.0, 'output': True,
                                                'reasoning': None, 'cache_read': 'x'})
        self.assertEqual(merged['input'], 7)
        self.assertNotIn('output', merged, 'bool must not count as 1')
        self.assertNotIn('reasoning', merged)
        self.assertNotIn('cache_read', merged)

    def test_truncation_marks_dropped_chars(self):
        out = lf.truncate('x' * 100, 10)
        self.assertTrue(out.startswith('x' * 10))
        self.assertIn('truncated 90 chars', out)

    def test_span_never_ends_before_it_starts(self):
        span = lf.make_span('t' * 32, 's' * 16, 'n', 500, 100, {})
        self.assertEqual(span['endTimeUnixNano'], '500')


class ExportTests(unittest.TestCase):
    """Exercise langfuse-trace.py end to end as a real subprocess against a
    local OTLP receiver, so the actual urllib POST path is under test."""

    @classmethod
    def setUpClass(cls):
        cls.received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(length)
                try:
                    cls.received.append({'path': self.path,
                                         'auth': self.headers.get('Authorization'),
                                         'payload': json.loads(body)})
                except ValueError:
                    cls.received.append({'path': self.path, 'payload': None})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *args):
                pass

        cls.server = HTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = 'http://127.0.0.1:%d' % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = os.path.join(self.tmp, 'state.json')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.transcript = write_jsonl(os.path.join(self.tmp, 'c.jsonl'), CLAUDE_RECORDS)
        type(self).received.clear()

    def run_export(self, args, env_extra=None, stdin_str=''):
        env = dict(os.environ)
        env.update({
            'LANGFUSE_PUBLIC_KEY': 'pk-lf-test',
            'LANGFUSE_SECRET_KEY': 'sk-lf-test',
            'LANGFUSE_BASE_URL': self.base_url,
            'VD_LANGFUSE_STATE': self.state,
        })
        env.update(env_extra or {})
        return subprocess.run([sys.executable, TRACE_SCRIPT] + args, input=stdin_str,
                              capture_output=True, text=True, env=env, timeout=30)

    def test_posts_otlp_to_the_traces_endpoint_with_basic_auth(self):
        self.run_export(['--transcript', self.transcript, '--agent', 'claude-code', '--json'])
        self.assertEqual(len(self.received), 1)
        request = self.received[0]
        self.assertEqual(request['path'], '/api/public/otel/v1/traces')
        self.assertTrue(request['auth'].startswith('Basic '))
        spans = request['payload']['resourceSpans'][0]['scopeSpans'][0]['spans']
        self.assertGreaterEqual(len(spans), 3, 'root + turn + generation at minimum')

    def test_exports_then_is_idempotent(self):
        first = self.run_export(['--transcript', self.transcript, '--agent', 'claude-code', '--json'])
        self.assertEqual(first.returncode, 0, first.stderr)
        payload = json.loads(first.stdout)[0]
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['exported'], 1)
        self.assertGreater(payload['spans'], 1)

        second = self.run_export(['--transcript', self.transcript, '--agent', 'claude-code', '--json'])
        repeat = json.loads(second.stdout)[0]
        self.assertEqual(repeat['exported'], 0, 'already-shipped turns must not resend')
        self.assertEqual(repeat['reason'], 'up to date')

    def test_force_reexports(self):
        self.run_export(['--transcript', self.transcript, '--agent', 'claude-code', '--json'])
        forced = self.run_export(['--transcript', self.transcript, '--agent', 'claude-code',
                                  '--force', '--json'])
        self.assertEqual(json.loads(forced.stdout)[0]['exported'], 1)

    def test_reads_transcript_path_from_stdin_like_a_hook(self):
        stdin = json.dumps({'transcript_path': self.transcript, 'session_id': 'x'})
        result = self.run_export(['--json'], stdin_str=stdin)
        payload = json.loads(result.stdout)[0]
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['agent'], 'claude-code', 'agent inferred from path')

    def test_missing_credentials_is_a_silent_no_op(self):
        result = self.run_export(
            ['--transcript', self.transcript, '--json'],
            env_extra={'LANGFUSE_PUBLIC_KEY': '', 'LANGFUSE_SECRET_KEY': '',
                       'VD_LANGFUSE_ENVRC': '/nonexistent/.envrc'})
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_unparseable_stdin_exits_zero(self):
        result = self.run_export(['--json'], stdin_str='not json at all')
        self.assertEqual(result.returncode, 0, 'a hook must never fail the turn')
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_max_turns_bounds_one_invocation_and_resumes(self):
        """A first fire against a long session must not ship everything at once —
        a synchronous Stop hook would block the turn for minutes."""
        records = []
        for index in range(5):
            records.append({'type': 'user', 'timestamp': '2026-08-01T10:0%d:00.000Z' % index,
                            'sessionId': 'sess-long',
                            'message': {'role': 'user', 'content': 'ask %d' % index}})
            records.append({'type': 'assistant', 'timestamp': '2026-08-01T10:0%d:05.000Z' % index,
                            'sessionId': 'sess-long',
                            'message': {'role': 'assistant', 'model': 'claude-opus-5',
                                        'usage': {'input_tokens': 1, 'output_tokens': 1},
                                        'content': [{'type': 'text', 'text': 'reply %d' % index}]}})
        path = write_jsonl(os.path.join(self.tmp, 'long.jsonl'), records)

        first = json.loads(self.run_export(
            ['--transcript', path, '--agent', 'claude-code', '--max-turns', '2', '--json']).stdout)[0]
        self.assertEqual(first['exported'], 2)
        self.assertEqual(first['remaining'], 3)

        second = json.loads(self.run_export(
            ['--transcript', path, '--agent', 'claude-code', '--max-turns', '2', '--json']).stdout)[0]
        self.assertEqual(second['exported'], 2, 'resumes where the cap stopped')
        self.assertEqual(second['remaining'], 1)

        third = json.loads(self.run_export(
            ['--transcript', path, '--agent', 'claude-code', '--max-turns', '2', '--json']).stdout)[0]
        self.assertEqual(third['exported'], 1)
        self.assertEqual(third['remaining'], 0)

        fourth = json.loads(self.run_export(
            ['--transcript', path, '--agent', 'claude-code', '--json']).stdout)[0]
        self.assertEqual(fourth['exported'], 0, 'all five turns accounted for exactly once')

    def test_state_file_records_turn_count(self):
        self.run_export(['--transcript', self.transcript, '--agent', 'claude-code', '--json'])
        with open(self.state, encoding='utf-8') as handle:
            state = json.load(handle)
        key = 'claude-code:sess-claude'
        self.assertIn(key, state)
        self.assertEqual(state[key]['turns'], 1)
        self.assertEqual(len(state[key]['trace_id']), 32)


class SpanShapeTests(unittest.TestCase):
    def test_build_spans_nests_generation_and_tools_under_turn(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = write_jsonl(os.path.join(tmp, 'c.jsonl'), CLAUDE_RECORDS)
        session = tx.parse(path, 'claude-code')
        config = lf.load_config({'LANGFUSE_PUBLIC_KEY': 'pk', 'LANGFUSE_SECRET_KEY': 'sk'})

        spec = importlib.util.spec_from_file_location('langfuse_trace_under_test', TRACE_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        trace_id, spans = module.build_spans(session, session.turns, config)
        by_id = {s['spanId']: s for s in spans}
        self.assertTrue(all(s['traceId'] == trace_id for s in spans))

        root = [s for s in spans if 'parentSpanId' not in s]
        self.assertEqual(len(root), 1, 'exactly one root span per trace')

        def attr(span, key):
            for item in span['attributes']:
                if item['key'] == key:
                    return item['value']
            return None

        turn = next((s for s in spans if s['name'] == 'turn 1'), None)
        self.assertIsNotNone(turn, 'turn span missing')
        self.assertEqual(turn['parentSpanId'], root[0]['spanId'])

        generation = next((s for s in spans
                           if attr(s, 'langfuse.observation.type') == {'stringValue': 'generation'}),
                          None)
        self.assertIsNotNone(generation, 'generation span missing')
        self.assertEqual(generation['parentSpanId'], turn['spanId'])
        self.assertEqual(attr(generation, 'gen_ai.request.model'), {'stringValue': 'claude-opus-5'})
        self.assertEqual(attr(generation, 'gen_ai.usage.input_tokens'), {'intValue': '10'})

        tool = next((s for s in spans if s['name'] == 'tool: Bash'), None)
        self.assertIsNotNone(tool, 'tool span missing')
        self.assertEqual(tool['parentSpanId'], turn['spanId'])
        self.assertIn(tool['spanId'], by_id)

        # Session identity must be on every span, not just the root (Langfuse
        # filters and aggregates on per-span attributes).
        for span in spans:
            self.assertEqual(attr(span, 'langfuse.session.id'), {'stringValue': 'sess-claude'})


if __name__ == '__main__':
    unittest.main()
