import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("agent_notify", Path(__file__).with_name("agent-notify.py"))
agent_notify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_notify)


class Result:
    def __init__(self, stdout):
        self.stdout = stdout
        self.returncode = 0


class TmuxCtxTest(unittest.TestCase):
    def test_uses_tmux_pane_when_present(self):
        with patch.dict(os.environ, {"TMUX_PANE": "%1"}, clear=True):
            with patch.object(agent_notify.subprocess, "run", return_value=Result("cnb:astro:0\n")) as run:
                self.assertEqual(agent_notify.tmux_ctx("/repo/app"), "cnb:astro:0")
                self.assertEqual(run.call_args.args[0][1:4], ["display-message", "-p", "-t"])

    def test_falls_back_to_unique_cwd_match(self):
        rows = "\n".join([
            "cnb:astro:0\t/repo/other\tcodex-aarch64-a",
            "cnb:cmd:4\t/repo/app\tcodex-aarch64-a",
        ])
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(agent_notify.subprocess, "run", return_value=Result(rows)):
                self.assertEqual(agent_notify.tmux_ctx("/repo/app"), "cnb:cmd:4")

    def test_prefers_sole_codex_match_for_shared_cwd(self):
        rows = "\n".join([
            "cnb:cmd:3\t/repo/app\tzsh",
            "cnb:cmd:4\t/repo/app\tcodex-aarch64-a",
        ])
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(agent_notify.subprocess, "run", return_value=Result(rows)):
                self.assertEqual(agent_notify.tmux_ctx("/repo/app"), "cnb:cmd:4")

    def test_leaves_ambiguous_codex_cwd_blank(self):
        rows = "\n".join([
            "cnb:cmd:4\t/repo/app\tcodex-aarch64-a",
            "cnb:cmd:5\t/repo/app\tcodex-aarch64-a",
        ])
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(agent_notify.subprocess, "run", return_value=Result(rows)):
                self.assertEqual(agent_notify.tmux_ctx("/repo/app"), "")


if __name__ == "__main__":
    unittest.main()
