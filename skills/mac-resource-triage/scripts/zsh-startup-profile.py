#!/usr/bin/env python3
"""Time zsh login startup and rank where the time goes, by file and by startup-file line.

Runs from $HOME. --env clean drops an inherited FPATH and ZDOTDIR (closer to a fresh terminal;
the rest of the environment is still inherited). --env inherited keeps the caller's environment
(what agent and nested shells see).
Usage: zsh-startup-profile.py [--env clean|inherited] [--runs 3] [--top 12]
"""
import argparse
import collections
import os
import re
import subprocess
import time

HOME = os.path.expanduser("~")
TRACE = re.compile(r"^\++(\d+\.\d+) (\S+?):(\d+)> (.*)")
STARTUP_FILES = (".zshenv", ".zprofile", ".zshrc", ".zlogin")


def run_env(mode: str) -> dict:
    env = dict(os.environ)
    if mode == "clean":
        env.pop("FPATH", None)
        env.pop("ZDOTDIR", None)
    return env


def short_home(path: str) -> str:
    return "~" + path[len(HOME):] if path == HOME or path.startswith(HOME + os.sep) else path


def tail(text: str, lines: int = 5) -> str:
    return "\n  ".join(text.strip().splitlines()[-lines:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["clean", "inherited"], default="clean")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()
    if args.runs < 1 or args.top < 1:
        ap.error("--runs and --top must be >= 1")
    env = run_env(args.env)

    times = []
    for _ in range(args.runs):
        start = time.perf_counter()
        # `exit 0`, not bare `exit`: bare exit returns the last startup command's status.
        proc = subprocess.run(["zsh", "-lic", "exit 0"], cwd=HOME, env=env, capture_output=True, text=True,
                              errors="replace")
        times.append(time.perf_counter() - start)
        if proc.returncode != 0:
            raise SystemExit(f"zsh startup exited {proc.returncode}; timings would be meaningless:\n  {tail(proc.stderr)}")
    print(f"startup ({args.env}): best {min(times):.2f}s  runs {' '.join(f'{t:.2f}' for t in times)}")

    env["PS4"] = "+%D{%s.%.} %x:%I> "
    trace = subprocess.run(["zsh", "-lixc", "exit 0"], cwd=HOME, env=env, capture_output=True, text=True,
                           errors="replace")
    stderr = trace.stderr
    recs = [(float(m[1]), m[2], int(m[3]), m[4]) for m in map(TRACE.match, stderr.splitlines()) if m]
    if len(recs) < 2:
        print(f"no trace captured (zsh rc={trace.returncode}; expected PS4 lines like '+<epoch.ms> <file>:<line>> ')")
        print(f"  {tail(stderr)}")
        return

    by_file, by_line, sample = collections.Counter(), collections.Counter(), {}
    calls = collections.Counter()
    for (t, f, n, cmd), (t2, *_rest) in zip(recs, recs[1:]):
        f = short_home(f)
        by_file[f] += t2 - t
        word = cmd.split(" ", 1)[0]
        if word in ("compinit", "compdump", "compaudit"):
            calls[word] += 1
        if f.endswith(STARTUP_FILES):
            key = (os.path.basename(f), n)
            by_line[key] += t2 - t
            sample.setdefault(key, cmd[:90])

    print(f"traced {recs[-1][0] - recs[0][0]:.2f}s over {len(recs)} lines (xtrace inflates absolute time)")
    print(f"compinit calls={calls['compinit']}  compdump (full rebuild) calls={calls['compdump']}  compaudit={calls['compaudit']}")
    print("\n-- by file")
    for f, secs in by_file.most_common(args.top):
        print(f"{secs:7.2f}s  {f}")
    print("\n-- by startup-file line")
    for key, secs in by_line.most_common(args.top):
        print(f"{secs:7.2f}s  {key[0]}:{key[1]}  {sample[key]}")


if __name__ == "__main__":
    main()
