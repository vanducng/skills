#!/usr/bin/env python3
"""Regenerate examples/sample-scorecard.xlsx from scored-candidates.json.

Explicit maintainer step — unittest does not call this and must not overwrite
the committed workbook.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
EXAMPLES = SKILL / "examples"

SPEC = importlib.util.spec_from_file_location(
    "write_scorecard", Path(__file__).with_name("write-scorecard.py")
)
writer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(writer)


def main(argv: list[str] | None = None) -> int:
    out = EXAMPLES / "sample-scorecard.xlsx"
    return writer.main([
        "--input", str(EXAMPLES / "scored-candidates.json"),
        "--out", str(out),
        "--file-base", str(EXAMPLES),
        "--profile", "data-platform-engineer",
        "--jd", "sample-jd.md",
        "--check",
        *(argv or []),
    ])


if __name__ == "__main__":
    sys.exit(main())
