#!/usr/bin/env python3
"""Automatically document test execution on Android with screenshots and UI state."""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial
from common.screenshot_utils import capture_screenshot
from common.uiautomator_utils import get_ui_hierarchy, flatten_tree, get_short_class


class TestRecorder:
    def __init__(self, serial=None, test_name="test", output_dir=None):
        self.serial = serial
        self.test_name = test_name
        self.output_dir = output_dir or f"/tmp/android_test_{test_name}_{int(time.time())}"
        os.makedirs(self.output_dir, exist_ok=True)
        self.steps = []

    def record_step(self, step_name, screenshot=True):
        """Record a test step with screenshot and UI state."""
        step_num = len(self.steps) + 1
        step = {
            "number": step_num,
            "name": step_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if screenshot:
            ss_path = os.path.join(self.output_dir, f"step_{step_num:02d}.png")
            ss = capture_screenshot(serial=self.serial, output_path=ss_path, size="half")
            step["screenshot"] = ss_path if "error" not in ss else None

        # Capture UI state
        try:
            root = get_ui_hierarchy(serial=self.serial)
            elements = flatten_tree(root)
            interactive = [e for e in elements if e["clickable"] or e["focusable"]]
            step["elements"] = len(elements)
            step["interactive"] = len(interactive)

            # Save UI state
            ui_path = os.path.join(self.output_dir, f"step_{step_num:02d}_ui.json")
            with open(ui_path, "w") as f:
                json.dump(elements, f, indent=2, ensure_ascii=False)
            step["ui_state"] = ui_path
        except Exception:
            step["elements"] = 0

        self.steps.append(step)
        return step

    def generate_report(self):
        """Generate a markdown test report."""
        lines = [
            f"# Test Report: {self.test_name}",
            f"",
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Steps:** {len(self.steps)}",
            f"",
        ]

        for step in self.steps:
            lines.append(f"## Step {step['number']}: {step['name']}")
            lines.append(f"- Time: {step['timestamp']}")
            lines.append(f"- Elements: {step.get('elements', 'N/A')} ({step.get('interactive', 'N/A')} interactive)")
            if step.get("screenshot"):
                lines.append(f"- Screenshot: step_{step['number']:02d}.png")
            lines.append("")

        report_path = os.path.join(self.output_dir, "report.md")
        with open(report_path, "w") as f:
            f.write("\n".join(lines))

        # Also save JSON
        json_path = os.path.join(self.output_dir, "report.json")
        with open(json_path, "w") as f:
            json.dump({"test_name": self.test_name, "steps": self.steps}, f, indent=2, default=str)

        return report_path


def main():
    parser = argparse.ArgumentParser(description="Record Android test execution")
    parser.add_argument("--test-name", default="test", help="Test name")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--step", help="Record a single step with this name")
    parser.add_argument("--report", action="store_true", help="Generate report from existing steps")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    recorder = TestRecorder(serial=serial, test_name=args.test_name, output_dir=args.output)

    if args.step:
        step = recorder.record_step(args.step)
        if args.json:
            print(json.dumps(step, indent=2, default=str))
        else:
            print(f"Recorded step {step['number']}: {step['name']} ({step.get('elements', 0)} elements)")

    report_path = recorder.generate_report()
    if not args.step:
        print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
