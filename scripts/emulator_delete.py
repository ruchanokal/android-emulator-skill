#!/usr/bin/env python3
"""Delete Android Virtual Devices."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import list_avds, run_command


def delete_avd(name):
    """Delete an AVD by name."""
    result = run_command(["avdmanager", "delete", "avd", "-n", name], timeout=15)
    if result and result.returncode == 0:
        return True, f"Deleted AVD: {name}"
    error = result.stderr if result else "Unknown error"
    return False, f"Failed to delete {name}: {error}"


def main():
    parser = argparse.ArgumentParser(description="Delete Android Virtual Devices")
    parser.add_argument("--name", help="AVD name to delete")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    parser.add_argument("--all", action="store_true", help="Delete all AVDs")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.all:
        avds = list_avds()
        if not avds:
            print("No AVDs to delete")
            sys.exit(0)
        if not args.yes:
            print(f"This will delete {len(avds)} AVDs: {', '.join(avds)}")
            print("Use --yes to confirm")
            sys.exit(1)
        results = []
        for avd in avds:
            success, msg = delete_avd(avd)
            results.append({"avd": avd, "success": success, "message": msg})
        if args.json:
            print(json.dumps({"results": results}))
        else:
            for r in results:
                status = "OK" if r["success"] else "FAIL"
                print(f"[{status}] {r['message']}")
    elif args.name:
        if not args.yes:
            print(f"Delete AVD '{args.name}'? Use --yes to confirm")
            sys.exit(1)
        success, msg = delete_avd(args.name)
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
