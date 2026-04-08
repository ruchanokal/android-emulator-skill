#!/usr/bin/env python3
"""Create comprehensive debugging snapshots for Android."""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command, get_device_info
from common.uiautomator_utils import get_ui_hierarchy, flatten_tree, count_elements
from common.screenshot_utils import capture_screenshot


class AppStateCapture:
    def __init__(self, serial=None, app_bundle_id=None):
        self.serial = serial
        self.app_bundle_id = app_bundle_id

    def capture_all(self, output_dir=None, log_lines=50):
        """Capture complete app state."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = f"/tmp/android_state_{timestamp}"
            os.makedirs(output_dir, exist_ok=True)

        results = {}

        # 1. Screenshot
        ss = capture_screenshot(serial=self.serial, output_path=os.path.join(output_dir, "screenshot.png"))
        results["screenshot"] = ss

        # 2. UI Hierarchy
        try:
            root = get_ui_hierarchy(serial=self.serial)
            elements = flatten_tree(root)
            hierarchy_path = os.path.join(output_dir, "ui-hierarchy.json")
            with open(hierarchy_path, "w") as f:
                json.dump(elements, f, indent=2, ensure_ascii=False)
            results["ui_hierarchy"] = {"file": hierarchy_path, "element_count": len(elements)}
        except Exception as e:
            results["ui_hierarchy"] = {"error": str(e)}

        # 3. App logs
        if self.app_bundle_id:
            try:
                pid_result = run_command(build_adb_command(
                    ["shell", "pidof", self.app_bundle_id], serial=self.serial
                ))
                log_cmd = build_adb_command(["logcat", "-d", "-t", str(log_lines)], serial=self.serial)
                if pid_result and pid_result.stdout.strip():
                    pid = pid_result.stdout.strip().split()[0]
                    log_cmd = build_adb_command(
                        ["logcat", "-d", "--pid", pid, "-t", str(log_lines)],
                        serial=self.serial
                    )
                log_result = run_command(log_cmd, timeout=10)
                if log_result and log_result.stdout:
                    log_path = os.path.join(output_dir, "app-logs.txt")
                    with open(log_path, "w") as f:
                        f.write(log_result.stdout)
                    results["logs"] = {"file": log_path, "lines": log_result.stdout.count("\n")}
            except Exception as e:
                results["logs"] = {"error": str(e)}

        # 4. Device info
        device_info = get_device_info(serial=self.serial)
        info_path = os.path.join(output_dir, "device-info.json")
        with open(info_path, "w") as f:
            json.dump(device_info, f, indent=2)
        results["device_info"] = device_info

        # 5. Summary
        summary = {
            "timestamp": timestamp,
            "app": self.app_bundle_id,
            "device": device_info,
            "results": results,
        }
        summary_path = os.path.join(output_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # 6. Markdown summary
        md_lines = [
            f"# App State Capture - {timestamp}",
            "",
            f"**App:** {self.app_bundle_id or 'N/A'}",
            f"**Device:** {device_info.get('model', 'unknown')} (Android {device_info.get('android_version', '?')})",
            "",
            "## Files",
            f"- Screenshot: screenshot.png",
            f"- UI Hierarchy: ui-hierarchy.json ({results.get('ui_hierarchy', {}).get('element_count', '?')} elements)",
            f"- Logs: app-logs.txt",
            f"- Device Info: device-info.json",
        ]
        md_path = os.path.join(output_dir, "summary.md")
        with open(md_path, "w") as f:
            f.write("\n".join(md_lines))

        return output_dir, results


def main():
    parser = argparse.ArgumentParser(description="Capture Android app state for debugging")
    parser.add_argument("--app-bundle-id", help="App package name")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--log-lines", type=int, default=50, help="Number of log lines")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    capture = AppStateCapture(serial=serial, app_bundle_id=args.app_bundle_id)
    output_dir, results = capture.capture_all(output_dir=args.output, log_lines=args.log_lines)

    if args.json:
        print(json.dumps({"output_dir": output_dir, "results": results}, indent=2, default=str))
    else:
        print(f"State captured to: {output_dir}")
        if "screenshot" in results and "error" not in results["screenshot"]:
            print(f"  Screenshot: OK")
        if "ui_hierarchy" in results and "error" not in results["ui_hierarchy"]:
            print(f"  UI Hierarchy: {results['ui_hierarchy'].get('element_count', '?')} elements")
        if "logs" in results and "error" not in results["logs"]:
            print(f"  Logs: {results['logs'].get('lines', '?')} lines")


if __name__ == "__main__":
    main()
