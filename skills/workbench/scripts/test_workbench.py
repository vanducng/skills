#!/usr/bin/env python3
"""Tests for the workbench.py shim. records.cjs has its own suite (records.test.cjs)."""
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SHIM = os.path.join(HERE, "workbench.py")
ENV = {k: v for k, v in os.environ.items() if k not in ("OPENRIG_SESSION_NAME", "PROJECTS_ROOT")}


def shim(args, cwd):
    return subprocess.run(["python3", SHIM, *args], cwd=cwd, env=ENV, capture_output=True, text=True)


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**ENV, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


class Shim(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.realpath(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_with_slug_runs_records_init(self):
        r = shim(["new", "PROJ-12 Thing"], self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        for f in ("SPEC.md", "PROGRESS.md", "PROOF.md"):
            self.assertTrue(os.path.exists(os.path.join(self.dir, ".workbench", "proj-12-thing", f)), f)
        self.assertIn("records.cjs init", r.stderr)

    def test_new_without_slug_names_the_record_after_the_branch(self):
        git(self.dir, "init", "-q", "-b", "feat/PROJ-3-x")
        git(self.dir, "commit", "-q", "--allow-empty", "-m", "i")
        self.assertEqual(shim(["new"], self.dir).returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".workbench", "proj-3-x", "SPEC.md")))

    def test_new_refuses_ticket_and_parent_rather_than_dropping_them(self):
        for flags, hint in ((["--ticket", "PROJ-12"], "new PROJ-12-thing"), (["--ticket=PROJ-12"], "new PROJ-12-thing"), (["--parent", "old-id"], "new thing")):
            r = shim(["new", "thing", *flags], self.dir)
            self.assertEqual(r.returncode, 2, flags)
            self.assertIn("removed", r.stderr, flags)
            self.assertIn(hint, r.stderr, flags)
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".workbench")))

    def test_removed_commands_exit_2_and_write_nothing(self):
        for cmd in ("resolve", "switch", "list", "status", "archive", "restore", "reindex", "gc", "triage"):
            r = shim([cmd], self.dir)
            self.assertEqual(r.returncode, 2, cmd)
            self.assertIn("removed", r.stderr, cmd)
        self.assertEqual(shim([], self.dir).returncode, 2)
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".workbench")))


if __name__ == "__main__":
    unittest.main()
