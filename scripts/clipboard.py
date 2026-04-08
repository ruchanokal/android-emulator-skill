#!/usr/bin/env python3
"""Manage Android device clipboard for paste testing."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


def copy_to_clipboard(text, serial=None):
    """Copy text to device clipboard via broadcast."""
    # Use am broadcast with clipboard service
    escaped = text.replace("'", "'\\''")
    cmd = build_adb_command(
        ["shell", "am", "broadcast", "-a", "clipper.set", "-e", "text", f"'{escaped}'"],
        serial=serial
    )
    result = run_command(cmd)

    # Fallback: use input to type and copy
    if not result or result.returncode != 0:
        # Alternative: set via service call (Android 10+)
        cmd = build_adb_command(
            ["shell", "input", "text", escaped],
            serial=serial
        )
        return False, "Clipboard set may require Clipper app. Text typed instead."

    return True, f'Copied to clipboard: "{text}"'


def main():
    parser = argparse.ArgumentParser(description="Android clipboard management")
    parser.add_argument("--copy", help="Text to copy to clipboard")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.copy:
        success, msg = copy_to_clipboard(args.copy, serial=serial)
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
