#!/usr/bin/env python3
"""Send simulated push notifications to Android emulator."""

import argparse
import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


def send_notification(bundle_id, title="Test", body="Test notification", badge=0, data=None, serial=None):
    """Send a push notification via adb shell."""
    # Create notification using am broadcast
    extras = f'-e "title" "{title}" -e "body" "{body}"'
    if data:
        for k, v in data.items():
            extras += f' -e "{k}" "{v}"'

    # Use dumpsys notification to post
    # For FCM testing, use Firebase test lab or adb shell
    cmd = build_adb_command([
        "shell", "cmd", "notification", "post",
        "-S", "bigtext",
        "-t", title,
        "test_tag",
        body,
    ], serial=serial)

    result = run_command(cmd)
    if result and result.returncode == 0:
        return True, f"Notification sent: {title}"

    # Fallback for older Android versions
    cmd = build_adb_command([
        "shell", "am", "broadcast",
        "-a", "com.google.firebase.MESSAGING_EVENT",
        "-n", f"{bundle_id}/com.google.firebase.messaging.FirebaseMessagingService",
        "--es", "title", title,
        "--es", "body", body,
    ], serial=serial)
    result = run_command(cmd)

    if result and result.returncode == 0:
        return True, f"Notification broadcast sent: {title}"
    return False, "Failed to send notification"


def main():
    parser = argparse.ArgumentParser(description="Send push notifications to Android")
    parser.add_argument("--bundle-id", required=True, help="App package name")
    parser.add_argument("--title", default="Test", help="Notification title")
    parser.add_argument("--body", default="Test notification", help="Notification body")
    parser.add_argument("--badge", type=int, default=0, help="Badge count")
    parser.add_argument("--data", help="Extra data as JSON string")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    data = json.loads(args.data) if args.data else None
    success, msg = send_notification(
        args.bundle_id, title=args.title, body=args.body,
        badge=args.badge, data=data, serial=serial
    )

    if args.json:
        print(json.dumps({"success": success, "message": msg}))
    else:
        print(msg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
