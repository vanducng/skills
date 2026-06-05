import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from validation import validate_and_fix  # noqa: E402


class ValidationTest(unittest.TestCase):
    def test_arrow_label_overlap_is_moved_above_node(self):
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240">
<rect class="canvas" width="100%" height="100%"/>
<rect class="process" x="100" y="100" width="180" height="80"/>
<g class="arrow-label">
  <rect x="120" y="130" width="80" height="18"/>
  <text x="160" y="144">label</text>
</g>
</svg>"""

        fixed, report = validate_and_fix(svg)

        self.assertFalse(report.needs_revise)
        self.assertIn("moved 1 arrow label group", " ".join(report.autofix_applied))
        self.assertIn('y="74"', fixed)
        self.assertIn('y="88"', fixed)


if __name__ == "__main__":
    unittest.main()
