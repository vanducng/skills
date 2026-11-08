#!/usr/bin/env python3
"""Run a skill's evals: scenario x model x variant x run, deterministic checks, a no-skill baseline, blind before/after.

Scenario layout and the check contract: references/eval-format.md. Stdlib only.

  run_evals.py <skill-dir> --model M [--model M2] [--runs 3] [--jobs 2] [--out-dir D] [--scenario NAME]
  run_evals.py <skill-dir> --before OLD --after NEW --model M --runs 3 [--margin 2] [--seed N]

Exit 0 when the run completed and, in with/without mode, every non-clean scenario passes with the skill on every
model (a failing eval is a finding, exit 3); in before/after mode, exit 0 only when `after` wins. Exit 2 on usage.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_TIMEOUT = 600
PI_FLAGS = [
    "-p", "--no-session", "--no-skills", "--no-context-files", "--no-extensions", "--no-mcp",
    "--no-prompt-templates", "--no-themes", "--offline",
]  # fmt: skip


def pi_argv(binary: str, model: str, skill: Path | None, prompt: str) -> list[str]:
    argv = [binary, *PI_FLAGS, "--model", model]
    if skill is not None:
        argv += ["--skill", str(skill)]
    return [*argv, prompt]


ADAPTERS = {"pi": pi_argv}


def find_scenarios(evals_dir: Path, only: list[str]) -> list[dict]:
    found = []
    for path in sorted(p for p in evals_dir.iterdir() if p.is_dir()):
        if only and path.name not in only:
            continue
        if not (path / "prompt.md").is_file() or not (path / "checks.sh").is_file():
            raise SystemExit(f"{path}: a scenario needs prompt.md and checks.sh")
        meta = json.loads((path / "scenario.json").read_text()) if (path / "scenario.json").is_file() else {}
        found.append({
            "name": path.name,
            "dir": path,
            "prompt": (path / "prompt.md").read_text(),
            "clean": bool(meta.get("clean", False)),
            "timeout": int(meta.get("timeout", DEFAULT_TIMEOUT)),
        })  # fmt: skip
    return found


def run_one(job: dict, adapter, binary: str, out_dir: Path) -> dict:
    scenario, model, variant, index = job["scenario"], job["model"], job["variant"], job["run"]
    tag = f"{scenario['name']}__{model.replace('/', '_')}__{variant['tag']}__{index}"
    work = Path(tempfile.mkdtemp(prefix="eval-"))
    orig = Path(tempfile.mkdtemp(prefix="eval-orig-"))
    started = time.time()
    record = {
        "scenario": scenario["name"], "model": model, "variant": variant["label"], "run": index,
        "passed": False, "error": None, "seconds": 0.0,
    }  # fmt: skip
    try:
        fixture = scenario["dir"] / "fixture"
        for target in (work, orig):
            if fixture.is_dir():
                shutil.copytree(fixture, target, dirs_exist_ok=True)
        argv = adapter(binary, model, variant["skill"], scenario["prompt"])
        try:
            done = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=scenario["timeout"], check=False)
            output, record["returncode"] = done.stdout, done.returncode
            (out_dir / f"{tag}.stderr.txt").write_text(done.stderr[-4000:])
        except subprocess.TimeoutExpired:
            output, record["returncode"], record["error"] = "", None, "timeout"
        except OSError as error:
            output, record["returncode"], record["error"] = "", None, f"cannot run {argv[0]}: {error}"
        output_file = out_dir / f"{tag}.output.txt"
        output_file.write_text(output)  # a timeout or a crash is a failed run: the checks are not run on it
        if record["error"] is None and record["returncode"] != 0:
            record["error"] = f"agent exited {record['returncode']}"
        if record["error"] is None:
            env = {**os.environ, "EVAL_OUTPUT": str(output_file), "EVAL_ORIG": str(orig)}
            check = subprocess.run(["bash", str(scenario["dir"] / "checks.sh")], cwd=work, env=env, capture_output=True, text=True, timeout=120, check=False)
            record["passed"] = check.returncode == 0
            (out_dir / f"{tag}.checks.txt").write_text((check.stdout + check.stderr)[-4000:])
    except subprocess.TimeoutExpired:
        record["error"] = "checks timed out"
    finally:
        record["seconds"] = round(time.time() - started, 1)
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(orig, ignore_errors=True)
    return record


def execute(scenarios: list[dict], models: list[str], variants: list[dict], runs: int, jobs: int, adapter, binary: str, out_dir: Path) -> list[dict]:
    queue = [
        {"scenario": s, "model": m, "variant": v, "run": i}
        for s in scenarios for m in models for v in variants for i in range(1, runs + 1)
    ]  # fmt: skip
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return list(pool.map(lambda job: run_one(job, adapter, binary, out_dir), queue))


def passes(records: list[dict], **match) -> tuple[int, int]:
    rows = [r for r in records if all(r[k] == v for k, v in match.items())]
    return sum(r["passed"] for r in rows), len(rows)


def baseline_table(records: list[dict], scenarios: list[dict], models: list[str], runs: int) -> tuple[list[str], list[str]]:
    lines, failing = [f"{'scenario':<34}{'model':<34}{'with':>7}{'without':>9}  note"], []
    for s in scenarios:
        for m in models:
            w, _ = passes(records, scenario=s["name"], model=m, variant="with")
            b, _ = passes(records, scenario=s["name"], model=m, variant="without")
            note = []
            if s["clean"]:
                note.append("clean")
            elif b == runs:
                note.append("too easy: the base model already passes")
            if w < runs:
                note.append("FAILS with the skill")
                if not s["clean"]:
                    failing.append(f"{s['name']} on {m}")
                else:
                    failing.append(f"{s['name']} (clean) on {m}")
            lines.append(f"{s['name']:<34}{m:<34}{f'{w}/{runs}':>7}{f'{b}/{runs}':>9}  {'; '.join(note)}")
    return lines, failing


def blind_labels(rng: random.Random) -> dict[str, str]:
    order = ["before", "after"]
    rng.shuffle(order)
    return {order[0]: "X", order[1]: "Y"}  # which version carries which label


def compare(records: list[dict], scenarios: list[dict], key: dict[str, str], margin: int) -> tuple[list[str], bool]:
    by_version = {version: label for version, label in key.items()}
    totals, clean_fail = {}, {}
    for version, label in by_version.items():
        totals[version] = passes(records, variant=label)[0]
        clean_fail[version] = {
            (r["scenario"], r["model"], r["run"])
            for r in records if r["variant"] == label and not r["passed"] and next(s for s in scenarios if s["name"] == r["scenario"])["clean"]
        }
    new_clean = clean_fail["after"] - clean_fail["before"]
    gain = totals["after"] - totals["before"]
    wins = gain >= margin and not new_clean
    lines = [
        f"key (read after scoring): before={key['before']} after={key['after']}",
        f"passes: before {totals['before']}, after {totals['after']} of {sum(1 for r in records if r['variant'] == key['before'])} runs each; net {gain:+d} (margin {margin})",
        f"new clean-case failures in after: {len(new_clean)}",
        "verdict: after is better; keep the edit" if wins else "verdict: no win; do not keep the edit",
    ]
    return lines, wins


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill", type=Path, help="the skill directory under test (its evals/ holds the scenarios)")
    ap.add_argument("--model", action="append", required=True, help="provider/model, repeatable")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--runtime", choices=sorted(ADAPTERS), default="pi")
    ap.add_argument("--binary", default=None, help="the agent binary (default: the runtime name)")
    ap.add_argument("--evals", type=Path, help="evals directory (default: <skill>/evals)")
    ap.add_argument("--scenario", action="append", default=[], help="run only this scenario, repeatable")
    ap.add_argument("--before", type=Path)
    ap.add_argument("--after", type=Path)
    ap.add_argument("--margin", type=int, default=2)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out-dir", type=Path)
    args = ap.parse_args(argv)
    if bool(args.before) != bool(args.after) or args.runs < 1:
        ap.error("--before and --after go together; --runs is at least 1")
    skill = args.skill.resolve()
    evals_dir = (args.evals or skill / "evals").resolve()
    if not evals_dir.is_dir():
        ap.error(f"no evals directory at {evals_dir}")
    scenarios = find_scenarios(evals_dir, args.scenario)
    if len(scenarios) < (1 if args.scenario else 3):
        ap.error("a skill needs at least 3 scenarios")
    if not args.scenario and not any(s["clean"] for s in scenarios):
        ap.error("at least one scenario must be a clean case (scenario.json {\"clean\": true})")
    out_dir = (args.out_dir or Path(tempfile.mkdtemp(prefix="eval-run-"))).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    adapter, binary = ADAPTERS[args.runtime], args.binary or args.runtime

    if args.before:
        key = blind_labels(random.Random(args.seed))
        variants = [
            {"label": key["before"], "tag": key["before"], "skill": args.before.resolve()},
            {"label": key["after"], "tag": key["after"], "skill": args.after.resolve()},
        ]
        records = execute(scenarios, args.model, variants, args.runs, args.jobs, adapter, binary, out_dir)
        lines, wins = compare(records, scenarios, key, args.margin)
        code = 0 if wins else 3
    else:
        variants = [{"label": "with", "tag": "with", "skill": skill}, {"label": "without", "tag": "without", "skill": None}]
        records = execute(scenarios, args.model, variants, args.runs, args.jobs, adapter, binary, out_dir)
        lines, failing = baseline_table(records, scenarios, args.model, args.runs)
        lines.append(f"{len(failing)} failing with the skill" + (": " + ", ".join(failing) if failing else ""))
        code = 3 if failing else 0
    result = {"skill": str(skill), "models": args.model, "runs": args.runs, "runtime": args.runtime, "records": records}
    (out_dir / "results.json").write_text(json.dumps(result, indent=1) + "\n")
    print("\n".join(lines))
    print(f"results: {out_dir / 'results.json'}")
    return code


if __name__ == "__main__":
    sys.exit(main())
