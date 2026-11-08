#!/usr/bin/env python3
"""Tests for run_evals.py with a fake agent binary: scenario discovery, checks, baseline, blind before/after."""

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import random
import stat
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("run_evals", pathlib.Path(__file__).with_name("run_evals.py"))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

# The fake agent: with `--skill <dir>` it writes the file named in that skill's MARK (default done.txt) and answers
# "ok"; without a skill it answers "no" and writes nothing. A skill dir containing CRASH makes it exit 3; SLOW sleeps.
FAKE = """#!/bin/sh
skill=""
while [ $# -gt 0 ]; do
  case "$1" in --skill) skill="$2"; shift 2 ;; *) shift ;; esac
done
if [ -n "$skill" ]; then
  [ -e "$skill/CRASH" ] && exit 3
  [ -e "$skill/SLOW" ] && sleep 5
  mark=done.txt; [ -e "$skill/MARK" ] && mark=$(cat "$skill/MARK")
  echo made > "$mark"
  echo ok
else
  echo no
fi
"""

CHECK_DONE = '#!/usr/bin/env bash\n[ -f done.txt ]\n'
CHECK_UNTOUCHED = '#!/usr/bin/env bash\n[ ! -f done.txt ] && grep -q no "$EVAL_OUTPUT"\n'


def build(root: pathlib.Path, scenarios: dict[str, tuple[str, dict | None]]) -> tuple[pathlib.Path, pathlib.Path]:
    skill = root / "skill"
    (skill / "evals").mkdir(parents=True)
    for name, (checks, meta) in scenarios.items():
        d = skill / "evals" / name
        d.mkdir()
        (d / "prompt.md").write_text("do the thing\n")
        (d / "checks.sh").write_text(checks)
        if meta is not None:
            (d / "scenario.json").write_text(json.dumps(meta))
    fake = root / "fakepi"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return skill, fake


STANDARD = {"01-make": (CHECK_DONE, None), "02-make-again": (CHECK_DONE, None), "03-leave-alone": (CHECK_UNTOUCHED, {"clean": True})}


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def run_main(self, skill, fake, *extra):
        out = self.root / "out"
        code = m.main([str(skill), "--binary", str(fake), "--model", "p/m", "--runs", "2", "--out-dir", str(out), *extra])
        return code, json.loads((out / "results.json").read_text())

    def test_with_the_skill_the_scenarios_pass_and_the_baseline_is_recorded(self):
        skill, fake = build(self.root, STANDARD)
        code, result = self.run_main(skill, fake)
        recs = result["records"]
        self.assertEqual(len(recs), 3 * 2 * 2)  # scenarios x variants x runs
        self.assertEqual(m.passes(recs, variant="without", scenario="01-make"), (0, 2))
        self.assertEqual(m.passes(recs, variant="with", scenario="01-make"), (2, 2))
        # the clean case: the baseline passes it, the skill (which writes done.txt) fails it
        self.assertEqual(m.passes(recs, variant="with", scenario="03-leave-alone"), (0, 2))
        self.assertEqual(code, 3)

    def test_a_non_clean_scenario_the_baseline_already_passes_is_flagged_too_easy(self):
        skill, fake = build(self.root, {**STANDARD, "04-easy": ("#!/usr/bin/env bash\nexit 0\n", None)})
        (self.root / "out").mkdir()
        recs = [{"scenario": "04-easy", "model": "p/m", "variant": v, "run": i, "passed": True} for v in ("with", "without") for i in (1, 2)]
        lines, failing = m.baseline_table(recs, [{"name": "04-easy", "clean": False}], ["p/m"], 2)
        self.assertIn("too easy", lines[1])
        self.assertEqual(failing, [])

    def test_a_clean_case_is_labelled_and_a_failing_one_is_named(self):
        recs = [{"scenario": "c", "model": "p/m", "variant": "with", "run": 1, "passed": False}, {"scenario": "c", "model": "p/m", "variant": "without", "run": 1, "passed": True}]
        lines, failing = m.baseline_table(recs, [{"name": "c", "clean": True}], ["p/m"], 1)
        self.assertIn("clean", lines[1])
        self.assertIn("FAILS with the skill", lines[1])
        self.assertEqual(failing, ["c (clean) on p/m"])

    def test_a_crashing_agent_is_a_failed_run_with_the_error_recorded(self):
        skill, fake = build(self.root, {"01-a": (CHECK_DONE, None), "02-b": (CHECK_DONE, None), "03-c": (CHECK_DONE, {"clean": True})})
        (skill / "CRASH").write_text("")
        _, result = self.run_main(skill, fake, "--runs", "1")
        crashed = [r for r in result["records"] if r["variant"] == "with"]
        self.assertTrue(all(not r["passed"] and "exited 3" in r["error"] for r in crashed))

    def test_a_missing_binary_is_a_failed_run_not_a_crash_of_the_harness(self):
        skill, _ = build(self.root, STANDARD)
        code = m.main([str(skill), "--binary", str(self.root / "no-such-binary"), "--model", "p/m", "--runs", "1", "--out-dir", str(self.root / "o")])
        result = json.loads((self.root / "o" / "results.json").read_text())
        self.assertEqual(code, 3)
        self.assertTrue(all(r["error"] and "cannot run" in r["error"] for r in result["records"]))

    def test_a_timeout_is_a_failed_run(self):
        skill, fake = build(self.root, {"01-a": (CHECK_DONE, {"timeout": 1}), "02-b": (CHECK_DONE, {"timeout": 1}), "03-c": (CHECK_DONE, {"clean": True, "timeout": 1})})
        (skill / "SLOW").write_text("")
        _, result = self.run_main(skill, fake, "--runs", "1")
        self.assertTrue(all(r["error"] == "timeout" for r in result["records"] if r["variant"] == "with"))

    def test_a_non_scenario_directory_is_skipped_and_selecting_it_is_a_usage_error(self):
        skill, fake = build(self.root, STANDARD)
        (skill / "evals" / "helpers").mkdir()
        (skill / "evals" / "helpers" / "notes.txt").write_text("not a scenario\n")
        code, result = self.run_main(skill, fake)
        self.assertEqual({r["scenario"] for r in result["records"]}, set(STANDARD))
        with self.assertRaises(SystemExit) as picked:
            self.run_main(skill, fake, "--scenario", "helpers")
        self.assertEqual(picked.exception.code, 2)
        with self.assertRaises(SystemExit) as unknown:
            self.run_main(skill, fake, "--scenario", "no-such")
        self.assertEqual(unknown.exception.code, 2)

    def test_checks_run_with_a_scrubbed_environment(self):
        probe = '#!/usr/bin/env bash\n[ -z "${EVAL_SECRET:-}" ] && [ -n "${EVAL_OUTPUT:-}" ] && [ -n "${EVAL_ORIG:-}" ] && [ -n "${PATH:-}" ] && [ -n "${HOME:-}" ]\n'
        skill, fake = build(self.root, {"01-a": (probe, None), "02-b": (probe, None), "03-c": (probe, {"clean": True})})
        os.environ["EVAL_SECRET"] = "leaked"
        self.addCleanup(os.environ.pop, "EVAL_SECRET", None)
        _, result = self.run_main(skill, fake, "--runs", "1")
        self.assertTrue(all(r["passed"] for r in result["records"] if r["variant"] == "with"))

    def test_a_skill_needs_three_scenarios_and_a_clean_case(self):
        skill, fake = build(self.root, {"01-a": (CHECK_DONE, None), "02-b": (CHECK_DONE, None)})
        with self.assertRaises(SystemExit) as raised:
            self.run_main(skill, fake)
        self.assertEqual(raised.exception.code, 2)
        other = self.root / "x"
        other.mkdir()
        skill2, fake2 = build(other, {"01-a": (CHECK_DONE, None), "02-b": (CHECK_DONE, None), "03-c": (CHECK_DONE, None)})
        with self.assertRaises(SystemExit) as no_clean:
            m.main([str(skill2), "--binary", str(fake2), "--model", "p/m"])
        self.assertEqual(no_clean.exception.code, 2)

    def test_the_fixture_is_copied_fresh_into_each_run_and_the_original_is_provided(self):
        skill, fake = build(self.root, {"01-a": ('#!/usr/bin/env bash\n[ -f seed.txt ] && [ -f "$EVAL_ORIG/seed.txt" ] && [ ! -f marker ] && touch marker\n', None), "02-b": (CHECK_DONE, None), "03-c": (CHECK_DONE, {"clean": True})})
        (skill / "evals" / "01-a" / "fixture").mkdir()
        (skill / "evals" / "01-a" / "fixture" / "seed.txt").write_text("seed\n")
        _, result = self.run_main(skill, fake, "--scenario", "01-a")
        self.assertTrue(all(r["passed"] for r in result["records"] if r["scenario"] == "01-a"))  # marker never carries over


class Blind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def versions(self, before_mark, after_mark):
        skill, fake = build(self.root, STANDARD)
        old, new = self.root / "old", self.root / "new"
        for d, mark in ((old, before_mark), (new, after_mark)):
            d.mkdir()
            (d / "MARK").write_text(mark)
        return skill, fake, old, new

    def run_compare(self, skill, fake, old, new, seed=1, margin=2):
        out = self.root / "out"
        code = m.main([str(skill), "--binary", str(fake), "--model", "p/m", "--runs", "2", "--before", str(old), "--after", str(new), "--seed", str(seed), "--margin", str(margin), "--out-dir", str(out)])
        return code, json.loads((out / "results.json").read_text())

    def test_labels_are_random_but_seeded_and_the_records_carry_only_the_labels(self):
        keys = {tuple(sorted(m.blind_labels(random.Random(s)).items())) for s in range(12)}
        self.assertEqual(len(keys), 2)  # both assignments occur
        self.assertEqual(m.blind_labels(random.Random(3)), m.blind_labels(random.Random(3)))
        skill, fake, old, new = self.versions("done.txt", "other.txt")
        _, result = self.run_compare(skill, fake, old, new)
        self.assertEqual({r["variant"] for r in result["records"]}, {"X", "Y"})

    def test_results_json_resolves_the_blind_labels_without_stdout(self):
        skill, fake, old, new = self.versions("other.txt", "done.txt")
        _, result = self.run_compare(skill, fake, old, new, seed=7, margin=3)
        self.assertEqual(result["mode"], "before-after")
        self.assertEqual(result["key"], {"before": result["key"]["before"], "after": result["key"]["after"]})
        self.assertEqual(sorted(result["key"].values()), ["X", "Y"])
        self.assertEqual((result["before"], result["after"]), (str(old.resolve()), str(new.resolve())))
        self.assertEqual((result["margin"], result["seed"]), (3, 7))
        self.assertTrue(result["verdict"].startswith("after is better"))
        self.assertEqual(result["key"], m.blind_labels(random.Random(7)))  # the recorded seed reproduces the key

    def test_an_unseeded_run_records_the_seed_it_drew(self):
        skill, fake, old, new = self.versions("other.txt", "done.txt")
        out = self.root / "out"
        m.main([str(skill), "--binary", str(fake), "--model", "p/m", "--runs", "1", "--before", str(old), "--after", str(new), "--out-dir", str(out)])
        result = json.loads((out / "results.json").read_text())
        self.assertIsInstance(result["seed"], int)
        self.assertEqual(result["key"], m.blind_labels(random.Random(result["seed"])))

    def test_the_better_version_wins_by_the_margin(self):
        skill, fake, old, new = self.versions("other.txt", "done.txt")  # after writes the file the checks want
        code, _ = self.run_compare(skill, fake, old, new, margin=2)
        self.assertEqual(code, 0)  # after passes the two make scenarios (+4), and the clean case fails in both

    def test_a_tie_is_not_a_win(self):
        skill, fake, old, new = self.versions("done.txt", "done.txt")
        code, _ = self.run_compare(skill, fake, old, new)
        self.assertEqual(code, 3)  # equal passes

    def test_compare_reports_a_new_clean_case_failure(self):
        scenarios = [{"name": "c", "clean": True}, {"name": "s", "clean": False}]
        recs = [
            {"scenario": "c", "model": "m", "variant": "X", "run": 1, "passed": True},
            {"scenario": "c", "model": "m", "variant": "Y", "run": 1, "passed": False},
            {"scenario": "s", "model": "m", "variant": "X", "run": 1, "passed": False},
            {"scenario": "s", "model": "m", "variant": "Y", "run": 1, "passed": True},
            {"scenario": "s", "model": "m", "variant": "X", "run": 2, "passed": False},
            {"scenario": "s", "model": "m", "variant": "Y", "run": 2, "passed": True},
        ]
        lines, wins = m.compare(recs, scenarios, {"before": "X", "after": "Y"}, 1)
        self.assertFalse(wins)  # +1 net but a clean case regressed
        self.assertIn("new clean-case failures in after: 1", "\n".join(lines))


if __name__ == "__main__":
    unittest.main(verbosity=2)
