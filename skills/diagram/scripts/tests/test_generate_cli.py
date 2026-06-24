import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from generate import (  # noqa: E402
    CODEX_IMAGE_MODEL,
    _generate_valid_skeleton,
    _openrouter_key_reason,
    _produce_image,
    _resolve_parent_dir,
    parse_args,
    resolve_output_dir,
    resolve_engine,
    write_versioned_manifest,
    write_versioned_spec,
)
from codex_image import _codex_exec_cmd, _png_from_last_message  # noqa: E402


class GenerateCliTest(unittest.TestCase):
    def test_parse_versioned_workflow_args(self):
        args = parse_args([
            "--type", "workflow",
            "--format", "svg",
            "--versioned",
            "--slug", "checkout-fulfillment",
            "--reference-image", "draft.png",
            "checkout workflow",
        ])

        self.assertEqual(args.type, "workflow")
        self.assertEqual(args.format, "svg")
        self.assertTrue(args.versioned)
        self.assertEqual(args.slug, "checkout-fulfillment")
        self.assertEqual(args.reference_image, ["draft.png"])

    def test_workflow_defaults_to_skeleton_engine(self):
        self.assertEqual(resolve_engine(None, "workflow", "svg"), "skeleton")

    def test_codex_png_with_explicit_type_does_not_require_openrouter(self):
        args = parse_args([
            "--type", "workflow",
            "--format", "png",
            "--provider", "codex",
            "call lookup workflow",
        ])

        self.assertIsNone(_openrouter_key_reason(args))

    def test_auto_type_requires_openrouter_for_classification(self):
        args = parse_args([
            "--format", "png",
            "--provider", "codex",
            "call lookup workflow",
        ])

        self.assertEqual(_openrouter_key_reason(args), "auto-classifying the diagram type")

    def test_openrouter_provider_requires_openrouter(self):
        args = parse_args([
            "--type", "workflow",
            "--format", "png",
            "--provider", "openrouter",
            "call lookup workflow",
        ])

        self.assertEqual(_openrouter_key_reason(args), "using --provider openrouter")

    def test_svg_requires_openrouter(self):
        args = parse_args([
            "--type", "workflow",
            "--format", "svg",
            "call lookup workflow",
        ])

        self.assertEqual(_openrouter_key_reason(args), "generating SVG diagrams")

    def test_visuals_env_overrides_scratch_output_parent(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"VD_VISUALS_PATH": tmp}):
            parent, session = resolve_output_dir("smoke")

        self.assertEqual(parent, Path(tmp))
        self.assertEqual(session.parent, Path(tmp))
        self.assertTrue(session.name.endswith("-smoke"))

    def test_workbench_visuals_is_default_scratch_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            visuals = Path(tmp) / ".workbench" / "features" / "feature" / "visuals"
            with patch.dict(os.environ, {}, clear=True), patch("generate.resolve_workbench_visuals", return_value=visuals):
                self.assertEqual(_resolve_parent_dir(), visuals)

    def test_codex_reference_image_keeps_prompt_after_separator(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / "draft.png"
            draft.write_bytes(b"png")
            cmd = _codex_exec_cmd(Path("/tmp/work"), Path("/tmp/work/last.txt"), "render this", [str(draft)])

        self.assertIn("--image", cmd)
        self.assertIn("--ephemeral", cmd)
        self.assertIn("--ignore-rules", cmd)
        self.assertIn("--ignore-user-config", cmd)
        self.assertEqual(cmd[-2:], ["--", "render this"])

    def test_codex_png_parser_finds_path_not_on_last_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "generated.png"
            image.write_bytes(b"png")
            last = Path(tmp) / "last.txt"
            last.write_text(f"codex\n{image}\ntokens used\n123")

            self.assertEqual(_png_from_last_message(last), image)

    def test_codex_image_path_skips_openrouter_refiner(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "v1.png"
            with (
                patch("generate.find_api_key", return_value=None),
                patch("generate.refine_prompt") as refine_prompt,
                patch("generate.codex_available", return_value=True),
                patch("generate.codex_generate_image") as codex_generate,
            ):
                refined, image_model = _produce_image(
                    description="call lookup workflow",
                    diagram_type="workflow",
                    fmt="png",
                    quality="medium",
                    aspect_ratio="16:9",
                    output_path=out_path,
                    preset="pastel",
                    image_provider="codex",
                )

        refine_prompt.assert_not_called()
        codex_generate.assert_called_once()
        self.assertEqual(image_model, CODEX_IMAGE_MODEL)
        self.assertIn("call lookup workflow", refined)

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
