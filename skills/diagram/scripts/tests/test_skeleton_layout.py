import sys
import unittest
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from skeleton_layout import laid_out_to_yaml, layered_lr  # noqa: E402
from skeleton_schema import parse_skeleton  # noqa: E402


FIXTURES = SCRIPT_DIR / "skeleton_fixtures"


def load_fixture(name: str):
    return parse_skeleton((FIXTURES / name).read_text())


class SkeletonLayoutTest(unittest.TestCase):
    def test_workflow_uses_horizontal_swimlane_rows(self):
        laid = layered_lr(load_fixture("workflow_minimal.yml"))

        self.assertEqual(laid.layout_style, "workflow-swimlanes")
        self.assertGreater(laid.canvas_w, laid.canvas_h)

        group_boxes = laid.groups
        self.assertEqual(group_boxes["customer"][0], group_boxes["commerce"][0])
        self.assertLess(group_boxes["customer"][1], group_boxes["commerce"][1])
        self.assertLess(group_boxes["commerce"][1], group_boxes["risk"][1])

        customer_y = laid.nodes["cart"][1]
        commerce_y = laid.nodes["order"][1]
        self.assertNotEqual(customer_y, commerce_y)
        self.assertLess(laid.nodes["cart"][0], laid.nodes["order"][0])
        self.assertLess(laid.nodes["order"][0], laid.nodes["fraud"][0])
        self.assertLess(laid.nodes["fraud"][0], laid.nodes["pick"][0])

    def test_workflow_yaml_exposes_lane_header_and_step_metadata(self):
        laid = layered_lr(load_fixture("workflow_minimal.yml"))
        data = yaml.safe_load(laid_out_to_yaml(laid))

        self.assertEqual(data["layout"]["style"], "workflow-swimlanes")
        self.assertIn("label_bbox", data["groups"][0])
        steps = {item["name"]: item["step"] for item in data["elements"]}
        self.assertEqual(steps["cart"], 1)
        self.assertGreater(steps["shipped"], steps["cart"])

    def test_system_architecture_keeps_group_columns(self):
        laid = layered_lr(load_fixture("system_arch_minimal.yml"))

        self.assertEqual(laid.layout_style, "group-columns")
        self.assertLess(laid.groups["client"][0], laid.groups["server"][0])
        self.assertEqual(laid.groups["client"][1], laid.groups["server"][1])
        self.assertEqual(laid.nodes["user"][0], laid.nodes["cli"][0])
        self.assertLess(laid.nodes["user"][1], laid.nodes["cli"][1])


if __name__ == "__main__":
    unittest.main()
