#!/usr/bin/env python3
"""Grant, revoke, and manage Android app permissions."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command

# Common Android permissions
PERMISSION_SHORTCUTS = {
    "camera": "android.permission.CAMERA",
    "microphone": "android.permission.RECORD_AUDIO",
    "location": "android.permission.ACCESS_FINE_LOCATION",
    "coarse-location": "android.permission.ACCESS_COARSE_LOCATION",
    "contacts": "android.permission.READ_CONTACTS",
    "phone": "android.permission.CALL_PHONE",
    "sms": "android.permission.SEND_SMS",
    "storage": "android.permission.READ_EXTERNAL_STORAGE",
    "write-storage": "android.permission.WRITE_EXTERNAL_STORAGE",
    "calendar": "android.permission.READ_CALENDAR",
    "photos": "android.permission.READ_MEDIA_IMAGES",
    "video": "android.permission.READ_MEDIA_VIDEO",
    "audio": "android.permission.READ_MEDIA_AUDIO",
    "notifications": "android.permission.POST_NOTIFICATIONS",
    "bluetooth": "android.permission.BLUETOOTH_CONNECT",
    "body-sensors": "android.permission.BODY_SENSORS",
    "nearby": "android.permission.NEARBY_WIFI_DEVICES",
}


class PermissionManager:
    def __init__(self, serial=None, package=None):
        self.serial = serial
        self.package = package

    def _resolve_permission(self, name):
        """Resolve permission shortcut to full permission string."""
        if name.lower() in PERMISSION_SHORTCUTS:
            return PERMISSION_SHORTCUTS[name.lower()]
        if name.startswith("android.permission."):
            return name
        return f"android.permission.{name.upper()}"

    def grant(self, permissions):
        """Grant permissions to app."""
        results = []
        for perm in permissions:
            full_perm = self._resolve_permission(perm)
            result = run_command(build_adb_command(
                ["shell", "pm", "grant", self.package, full_perm],
                serial=self.serial
            ))
            success = result and result.returncode == 0
            results.append({
                "permission": full_perm,
                "shortcut": perm,
                "success": success,
                "error": result.stderr.strip() if result and not success else None,
            })
        return results

    def revoke(self, permissions):
        """Revoke permissions from app."""
        results = []
        for perm in permissions:
            full_perm = self._resolve_permission(perm)
            result = run_command(build_adb_command(
                ["shell", "pm", "revoke", self.package, full_perm],
                serial=self.serial
            ))
            success = result and result.returncode == 0
            results.append({
                "permission": full_perm,
                "shortcut": perm,
                "success": success,
            })
        return results

    def list_permissions(self):
        """List all permissions for the app."""
        result = run_command(build_adb_command(
            ["shell", "dumpsys", "package", self.package],
            serial=self.serial
        ))
        if not result or result.returncode != 0:
            return {"granted": [], "denied": []}

        granted = []
        denied = []
        in_perms = False
        for line in result.stdout.split("\n"):
            line = line.strip()
            if "runtime permissions:" in line.lower() or "install permissions:" in line.lower():
                in_perms = True
                continue
            if in_perms:
                if not line or (not line.startswith("android.permission") and ":" not in line):
                    in_perms = False
                    continue
                if "granted=true" in line:
                    perm = line.split(":")[0].strip()
                    granted.append(perm)
                elif "granted=false" in line:
                    perm = line.split(":")[0].strip()
                    denied.append(perm)

        return {"granted": granted, "denied": denied}

    def reset(self):
        """Reset all runtime permissions."""
        result = run_command(build_adb_command(
            ["shell", "pm", "reset-permissions", self.package],
            serial=self.serial
        ))
        return result and result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Manage Android app permissions")
    parser.add_argument("--bundle-id", required=True, help="App package name")
    parser.add_argument("--grant", help="Permissions to grant (comma-separated)")
    parser.add_argument("--revoke", help="Permissions to revoke (comma-separated)")
    parser.add_argument("--list", action="store_true", help="List app permissions")
    parser.add_argument("--reset", action="store_true", help="Reset all permissions")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    pm = PermissionManager(serial=serial, package=args.bundle_id)

    if args.grant:
        perms = [p.strip() for p in args.grant.split(",")]
        results = pm.grant(perms)
        if args.json:
            print(json.dumps({"results": results}, indent=2))
        else:
            for r in results:
                status = "OK" if r["success"] else "FAIL"
                print(f"[{status}] Grant {r['shortcut']} -> {r['permission']}")
    elif args.revoke:
        perms = [p.strip() for p in args.revoke.split(",")]
        results = pm.revoke(perms)
        if args.json:
            print(json.dumps({"results": results}, indent=2))
        else:
            for r in results:
                status = "OK" if r["success"] else "FAIL"
                print(f"[{status}] Revoke {r['shortcut']}")
    elif args.list:
        perms = pm.list_permissions()
        if args.json:
            print(json.dumps(perms, indent=2))
        else:
            print(f"Granted ({len(perms['granted'])}):")
            for p in perms["granted"]:
                print(f"  + {p}")
            print(f"Denied ({len(perms['denied'])}):")
            for p in perms["denied"]:
                print(f"  - {p}")
    elif args.reset:
        success = pm.reset()
        msg = "Permissions reset" if success else "Failed to reset permissions"
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
