#!/usr/bin/env python3
"""Fuzz/stress testing using Android's monkey tool."""

import argparse
import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


class MonkeyTester:
    def __init__(self, serial=None):
        self.serial = serial

    def run(self, package, events=500, throttle=100,
            touch_pct=None, nav_pct=None, sys_pct=None,
            seed=None, verbose=False, ignore_crashes=False,
            ignore_timeouts=False):
        """Run monkey test."""
        cmd = build_adb_command(["shell", "monkey"], serial=self.serial)
        cmd.extend(["-p", package])
        cmd.extend(["--throttle", str(throttle)])

        if touch_pct is not None:
            cmd.extend(["--pct-touch", str(touch_pct)])
        if nav_pct is not None:
            cmd.extend(["--pct-nav", str(nav_pct)])
        if sys_pct is not None:
            cmd.extend(["--pct-syskeys", str(sys_pct)])

        if seed is not None:
            cmd.extend(["-s", str(seed)])
        if verbose:
            cmd.append("-v")
        if ignore_crashes:
            cmd.append("--ignore-crashes")
        if ignore_timeouts:
            cmd.append("--ignore-timeouts")

        cmd.append(str(events))

        result = run_command(cmd, timeout=events * (throttle / 1000.0) + 60)

        if not result:
            return {"success": False, "error": "Monkey command failed or timed out"}

        output = result.stdout + result.stderr
        return self._parse_results(output, events)

    def _parse_results(self, output, requested_events):
        """Parse monkey test output."""
        result = {
            "success": True,
            "events_requested": requested_events,
            "events_completed": 0,
            "crashes": [],
            "anrs": [],
            "errors": [],
        }

        # Check for crashes
        crash_pattern = r"// CRASH: (\S+) \(pid (\d+)\)"
        crashes = re.findall(crash_pattern, output)
        if crashes:
            result["success"] = False
            result["crashes"] = [{"package": c[0], "pid": c[1]} for c in crashes]

        # Check for ANRs
        anr_pattern = r"// NOT RESPONDING: (\S+)"
        anrs = re.findall(anr_pattern, output)
        if anrs:
            result["anrs"] = [{"package": a} for a in anrs]

        # Events completed
        events_match = re.search(r"Events injected: (\d+)", output)
        if events_match:
            result["events_completed"] = int(events_match.group(1))

        # Network errors
        if "Monkey aborted" in output:
            result["success"] = False
            result["errors"].append("Monkey aborted")

        # Seed for reproducibility
        seed_match = re.search(r"seed=(\d+)", output)
        if seed_match:
            result["seed"] = int(seed_match.group(1))

        return result


def main():
    parser = argparse.ArgumentParser(description="Android monkey (fuzz/stress) testing")
    parser.add_argument("--package", required=True, help="Target app package name")
    parser.add_argument("--events", type=int, default=500, help="Number of random events (default: 500)")
    parser.add_argument("--throttle", type=int, default=100, help="Delay between events in ms (default: 100)")
    parser.add_argument("--touch", type=int, dest="touch_pct", help="Touch event percentage")
    parser.add_argument("--nav", type=int, dest="nav_pct", help="Navigation event percentage")
    parser.add_argument("--sys", type=int, dest="sys_pct", help="System key event percentage")
    parser.add_argument("--seed", type=int, help="Random seed (for reproducibility)")
    parser.add_argument("--ignore-crashes", action="store_true", help="Continue after crashes")
    parser.add_argument("--ignore-timeouts", action="store_true", help="Continue after ANRs")
    parser.add_argument("--verbose", action="store_true", help="Verbose monkey output")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    tester = MonkeyTester(serial=serial)

    print(f"Running monkey test: {args.events} events on {args.package}...")
    result = tester.run(
        package=args.package,
        events=args.events,
        throttle=args.throttle,
        touch_pct=args.touch_pct,
        nav_pct=args.nav_pct,
        sys_pct=args.sys_pct,
        seed=args.seed,
        verbose=args.verbose,
        ignore_crashes=args.ignore_crashes,
        ignore_timeouts=args.ignore_timeouts,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASSED" if result["success"] else "FAILED"
        print(f"\nMonkey test: {status}")
        print(f"  Events: {result['events_completed']}/{result['events_requested']}")

        if result.get("seed"):
            print(f"  Seed: {result['seed']} (use --seed {result['seed']} to reproduce)")

        if result["crashes"]:
            print(f"  Crashes: {len(result['crashes'])}")
            for crash in result["crashes"]:
                print(f"    - {crash['package']} (PID: {crash['pid']})")

        if result["anrs"]:
            print(f"  ANRs: {len(result['anrs'])}")
            for anr in result["anrs"]:
                print(f"    - {anr['package']}")

        if result["errors"]:
            print(f"  Errors: {', '.join(result['errors'])}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
