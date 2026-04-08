#!/usr/bin/env python3
"""Send arbitrary Android intents for deep link and inter-component testing."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


# Common intent actions
ACTION_SHORTCUTS = {
    "view": "android.intent.action.VIEW",
    "send": "android.intent.action.SEND",
    "sendto": "android.intent.action.SENDTO",
    "call": "android.intent.action.CALL",
    "dial": "android.intent.action.DIAL",
    "pick": "android.intent.action.PICK",
    "edit": "android.intent.action.EDIT",
    "delete": "android.intent.action.DELETE",
    "search": "android.intent.action.SEARCH",
    "settings": "android.settings.SETTINGS",
    "wifi-settings": "android.settings.WIFI_SETTINGS",
    "bluetooth-settings": "android.settings.BLUETOOTH_SETTINGS",
    "location-settings": "android.settings.LOCATION_SOURCE_SETTINGS",
    "app-details": "android.settings.APPLICATION_DETAILS_SETTINGS",
    "notification-settings": "android.settings.APP_NOTIFICATION_SETTINGS",
}

# Common categories
CATEGORY_SHORTCUTS = {
    "launcher": "android.intent.category.LAUNCHER",
    "browsable": "android.intent.category.BROWSABLE",
    "default": "android.intent.category.DEFAULT",
    "home": "android.intent.category.HOME",
}


class IntentSender:
    def __init__(self, serial=None):
        self.serial = serial

    def send_activity(self, action=None, data=None, component=None, package=None,
                      category=None, mime_type=None, extras=None, flags=None):
        """Start an activity with an intent."""
        cmd = build_adb_command(["shell", "am", "start"], serial=self.serial)
        cmd.extend(self._build_intent_args(action, data, component, package,
                                            category, mime_type, extras, flags))

        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, f"Activity started: {action or component or data or 'intent'}"
        error = result.stderr.strip() if result else "Unknown error"
        return False, f"Failed: {error}"

    def send_broadcast(self, action=None, data=None, component=None, package=None,
                       category=None, mime_type=None, extras=None):
        """Send a broadcast intent."""
        cmd = build_adb_command(["shell", "am", "broadcast"], serial=self.serial)
        cmd.extend(self._build_intent_args(action, data, component, package,
                                            category, mime_type, extras, None))

        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, f"Broadcast sent: {action or 'intent'}"
        return False, f"Broadcast failed"

    def send_service(self, action=None, component=None, package=None, extras=None):
        """Start a service."""
        cmd = build_adb_command(["shell", "am", "startservice"], serial=self.serial)
        cmd.extend(self._build_intent_args(action, None, component, package,
                                            None, None, extras, None))

        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, f"Service started: {action or component or 'intent'}"
        return False, "Service start failed"

    def _build_intent_args(self, action, data, component, package,
                           category, mime_type, extras, flags):
        """Build intent arguments for am command."""
        args = []

        if action:
            resolved = ACTION_SHORTCUTS.get(action.lower(), action)
            args.extend(["-a", resolved])

        if data:
            args.extend(["-d", data])

        if component:
            args.extend(["-n", component])

        if package:
            args.extend(["-p", package])

        if category:
            resolved = CATEGORY_SHORTCUTS.get(category.lower(), category)
            args.extend(["-c", resolved])

        if mime_type:
            args.extend(["-t", mime_type])

        if flags:
            for flag in flags:
                args.extend(["-f", flag])

        if extras:
            for extra in extras:
                if "=" in extra:
                    key, value = extra.split("=", 1)
                    # Detect type
                    if value.lower() in ("true", "false"):
                        args.extend(["--ez", key, value])
                    elif value.isdigit():
                        args.extend(["--ei", key, value])
                    elif "." in value and value.replace(".", "").isdigit():
                        args.extend(["--ef", key, value])
                    else:
                        args.extend(["--es", key, value])

        return args

    def open_app_settings(self, package):
        """Open app settings page."""
        return self.send_activity(
            action="app-details",
            data=f"package:{package}"
        )

    def open_deep_link(self, url):
        """Open a deep link URL."""
        return self.send_activity(action="view", data=url)


def main():
    parser = argparse.ArgumentParser(description="Send Android intents")
    parser.add_argument("--action", "-a", help="Intent action (e.g., 'view', 'send', or full action string)")
    parser.add_argument("--data", "-d", help="Intent data URI")
    parser.add_argument("--component", "-n", help="Component name (package/activity)")
    parser.add_argument("--package", "-p", help="Target package")
    parser.add_argument("--category", "-c", help="Intent category")
    parser.add_argument("--type", "-t", dest="mime_type", help="MIME type")
    parser.add_argument("--extra", "-e", action="append", dest="extras",
                        help="Extra key=value (auto-detects type). Can be used multiple times")
    parser.add_argument("--flag", "-f", action="append", dest="flags", help="Intent flags")
    parser.add_argument("--broadcast", action="store_true", help="Send as broadcast instead of activity")
    parser.add_argument("--service", action="store_true", help="Start as service instead of activity")
    parser.add_argument("--deep-link", help="Shortcut: open a deep link URL")
    parser.add_argument("--app-settings", help="Shortcut: open app settings for package")
    parser.add_argument("--list-actions", action="store_true", help="List common action shortcuts")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    if args.list_actions:
        if args.json:
            print(json.dumps(ACTION_SHORTCUTS, indent=2))
        else:
            print("Action shortcuts:")
            for short, full in ACTION_SHORTCUTS.items():
                print(f"  {short:25s} → {full}")
        sys.exit(0)

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    sender = IntentSender(serial=serial)

    if args.deep_link:
        success, msg = sender.open_deep_link(args.deep_link)
    elif args.app_settings:
        success, msg = sender.open_app_settings(args.app_settings)
    elif args.broadcast:
        success, msg = sender.send_broadcast(
            action=args.action, data=args.data, component=args.component,
            package=args.package, category=args.category,
            mime_type=args.mime_type, extras=args.extras,
        )
    elif args.service:
        success, msg = sender.send_service(
            action=args.action, component=args.component,
            package=args.package, extras=args.extras,
        )
    elif args.action or args.data or args.component:
        success, msg = sender.send_activity(
            action=args.action, data=args.data, component=args.component,
            package=args.package, category=args.category,
            mime_type=args.mime_type, extras=args.extras, flags=args.flags,
        )
    else:
        parser.print_help()
        sys.exit(1)

    if args.json:
        print(json.dumps({"success": success, "message": msg}))
    else:
        print(msg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
