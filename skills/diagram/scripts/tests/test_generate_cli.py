import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from generate import (  # noqa: E402
    _generate_valid_skeleton,
    parse_args,
    resolve_engine,
    write_versioned_manifest,
    write_versioned_spec,
)


class GenerateCliTest(unittest.TestCase):
    def test_parse_versioned_workflow_args(self):
        args = parse_args([
            "--type", "workflow",
            "--format", "svg",
            "--versioned",
            "--slug", "checkout-fulfillment",
            "checkout workflow",
        ])

        self.assertEqual(args.type, "workflow")
        self.assertEqual(args.format, "svg")
        self.assertTrue(args.versioned)
        self.assertEqual(args.slug, "checkout-fulfillment")

    def test_workflow_defaults_to_skeleton_engine(self):
        self.assertEqual(resolve_engine(None, "workflow", "svg"), "skeleton")

    def test_versioned_spec_and_manifest_are_reviewable(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp)
            image = session / "v1.svg"
            image.write_text("<svg></svg>")

            write_versioned_spec(
                session,
                slug="checkout-fulfillment",
                original="checkout workflow\nwith fraud review",
                diagram_type="workflow",
                fmt="svg",
                preset="mono",
                engine="skeleton",
                image_path=image,
            )
            write_versioned_manifest(
                session,
                slug="checkout-fulfillment",
                diagram_type="workflow",
                fmt="svg",
                preset="mono",
                engine="skeleton",
                image_path=image,
            )

            spec = (session / "diagram.spec.yaml").read_text()
            manifest = json.loads((session / "manifest.json").read_text())

            self.assertIn("kind: vd.diagram", spec)
            self.assertIn("description: |-", spec)
            self.assertEqual(manifest["latest"], "v1.svg")
            self.assertEqual(manifest["variants"], ["v1.svg"])
            self.assertNotIn("updated", manifest)

    def test_invalid_skeleton_retries_with_validator_feedback(self):
        invalid = """type: workflow
preset: warm
groups:
  - {name: lane, label: Lane}
elements:
  - {name: step, kind: process, group: lane, label: "This label is intentionally much longer than forty characters"}
edges: []
"""
        valid = """type: workflow
preset: warm
groups:
  - {name: lane, label: Lane}
elements:
  - {name: step, kind: process, group: lane, label: "Short step"}
edges: []
"""
        with patch("generate.generate_skeleton", side_effect=[invalid, valid]) as mocked:
            skel = _generate_valid_skeleton(
                description="workflow",
                diagram_type="workflow",
                preset="warm",
                refs={"skeleton_contract": "", "type_ref": ""},
            )

        self.assertEqual(skel.elements[0].label, "Short step")
        self.assertEqual(mocked.call_count, 2)
        self.assertIn("Previous YAML failed validation", mocked.call_args.kwargs["description"])


if __name__ == "__main__":
    unittest.main()
