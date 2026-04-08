#!/usr/bin/env python3
"""Push, pull, and manage files on Android device."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


class FileManager:
    def __init__(self, serial=None):
        self.serial = serial

    def push(self, local_path, device_path):
        """Push a file/directory to device."""
        if not os.path.exists(local_path):
            return False, f"Local path not found: {local_path}"

        result = run_command(
            build_adb_command(["push", local_path, device_path], serial=self.serial),
            timeout=120
        )
        if result and result.returncode == 0:
            size = os.path.getsize(local_path) if os.path.isfile(local_path) else "dir"
            return True, f"Pushed {local_path} → {device_path} ({size} bytes)"
        error = result.stderr.strip() if result else "Unknown error"
        return False, f"Push failed: {error}"

    def pull(self, device_path, local_path):
        """Pull a file/directory from device."""
        result = run_command(
            build_adb_command(["pull", device_path, local_path], serial=self.serial),
            timeout=120
        )
        if result and result.returncode == 0:
            return True, f"Pulled {device_path} → {local_path}"
        error = result.stderr.strip() if result else "Unknown error"
        return False, f"Pull failed: {error}"

    def ls(self, device_path):
        """List files on device."""
        result = run_command(build_adb_command(
            ["shell", "ls", "-la", device_path], serial=self.serial
        ))
        if result and result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"Cannot list: {device_path}"

    def rm(self, device_path, recursive=False):
        """Remove a file/directory on device."""
        args = ["shell", "rm"]
        if recursive:
            args.append("-rf")
        args.append(device_path)

        result = run_command(build_adb_command(args, serial=self.serial))
        if result and result.returncode == 0:
            return True, f"Removed: {device_path}"
        return False, f"Remove failed: {device_path}"

    def mkdir(self, device_path):
        """Create directory on device."""
        result = run_command(build_adb_command(
            ["shell", "mkdir", "-p", device_path], serial=self.serial
        ))
        if result and result.returncode == 0:
            return True, f"Created directory: {device_path}"
        return False, f"Failed to create: {device_path}"

    def cat(self, device_path):
        """Read a file from device."""
        result = run_command(build_adb_command(
            ["shell", "cat", device_path], serial=self.serial
        ))
        if result and result.returncode == 0:
            return True, result.stdout
        return False, f"Cannot read: {device_path}"

    def stat(self, device_path):
        """Get file info from device."""
        result = run_command(build_adb_command(
            ["shell", "stat", device_path], serial=self.serial
        ))
        if result and result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"Cannot stat: {device_path}"

    def pull_app_data(self, package, local_dir="."):
        """Pull app's data directory (requires debuggable app or root)."""
        # Try run-as for debuggable apps
        data_path = f"/data/data/{package}"
        local_dest = os.path.join(local_dir, package)
        os.makedirs(local_dest, exist_ok=True)

        # List files in app data
        result = run_command(build_adb_command(
            ["shell", "run-as", package, "ls", "-R", "."], serial=self.serial
        ))

        if result and result.returncode == 0:
            # Create tar and pull
            tar_path = f"/sdcard/{package}_data.tar"
            run_command(build_adb_command(
                ["shell", "run-as", package, "tar", "cf", tar_path, "."],
                serial=self.serial
            ))
            pull_result = run_command(build_adb_command(
                ["pull", tar_path, os.path.join(local_dest, "data.tar")],
                serial=self.serial
            ), timeout=60)
            # Clean up
            run_command(build_adb_command(["shell", "rm", tar_path], serial=self.serial))

            if pull_result and pull_result.returncode == 0:
                return True, f"App data pulled to: {local_dest}/data.tar"

        # Fallback: try direct pull (requires root)
        result = run_command(
            build_adb_command(["pull", data_path, local_dest], serial=self.serial),
            timeout=60
        )
        if result and result.returncode == 0:
            return True, f"App data pulled to: {local_dest}"

        return False, f"Cannot pull app data. App may not be debuggable. Try: adb root"

    def pull_shared_prefs(self, package, local_dir="."):
        """Pull shared preferences for an app."""
        prefs_path = f"/data/data/{package}/shared_prefs"
        local_dest = os.path.join(local_dir, f"{package}_prefs")
        os.makedirs(local_dest, exist_ok=True)

        # Try run-as
        result = run_command(build_adb_command(
            ["shell", "run-as", package, "cat", "shared_prefs/*.xml"],
            serial=self.serial
        ))
        if result and result.returncode == 0 and result.stdout.strip():
            # Save output
            output_path = os.path.join(local_dest, "all_prefs.xml")
            with open(output_path, "w") as f:
                f.write(result.stdout)
            return True, f"Shared prefs saved to: {output_path}"

        # Try direct pull
        result = run_command(
            build_adb_command(["pull", prefs_path, local_dest], serial=self.serial),
            timeout=30
        )
        if result and result.returncode == 0:
            return True, f"Shared prefs pulled to: {local_dest}"

        return False, "Cannot pull shared prefs. App may not be debuggable."

    def pull_database(self, package, db_name=None, local_dir="."):
        """Pull database file(s) for an app."""
        db_dir = f"/data/data/{package}/databases"
        local_dest = os.path.join(local_dir, f"{package}_db")
        os.makedirs(local_dest, exist_ok=True)

        if db_name:
            # Pull specific database
            result = run_command(build_adb_command(
                ["shell", "run-as", package, "cat", f"databases/{db_name}"],
                serial=self.serial
            ))
            if result and result.returncode == 0:
                output_path = os.path.join(local_dest, db_name)
                with open(output_path, "wb") as f:
                    f.write(result.stdout.encode("latin-1"))
                return True, f"Database saved to: {output_path}"

        # Try direct pull
        result = run_command(
            build_adb_command(["pull", db_dir, local_dest], serial=self.serial),
            timeout=60
        )
        if result and result.returncode == 0:
            return True, f"Databases pulled to: {local_dest}"

        return False, "Cannot pull database. App may not be debuggable."


def main():
    parser = argparse.ArgumentParser(description="Manage files on Android device")
    parser.add_argument("--push", nargs=2, metavar=("LOCAL", "DEVICE"), help="Push file to device")
    parser.add_argument("--pull", nargs=2, metavar=("DEVICE", "LOCAL"), help="Pull file from device")
    parser.add_argument("--ls", metavar="PATH", help="List files on device")
    parser.add_argument("--rm", metavar="PATH", help="Remove file on device")
    parser.add_argument("--rm-recursive", action="store_true", help="Remove recursively")
    parser.add_argument("--mkdir", metavar="PATH", help="Create directory on device")
    parser.add_argument("--cat", metavar="PATH", help="Read file from device")
    parser.add_argument("--stat", metavar="PATH", help="Get file info")
    parser.add_argument("--pull-app-data", metavar="PACKAGE", help="Pull app data directory")
    parser.add_argument("--pull-prefs", metavar="PACKAGE", help="Pull shared preferences")
    parser.add_argument("--pull-db", metavar="PACKAGE", help="Pull database files")
    parser.add_argument("--db-name", help="Specific database name (with --pull-db)")
    parser.add_argument("--output", "-o", default=".", help="Local output directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    fm = FileManager(serial=serial)

    if args.push:
        success, msg = fm.push(args.push[0], args.push[1])
    elif args.pull:
        success, msg = fm.pull(args.pull[0], args.pull[1])
    elif args.ls:
        success, msg = fm.ls(args.ls)
    elif args.rm:
        success, msg = fm.rm(args.rm, recursive=args.rm_recursive)
    elif args.mkdir:
        success, msg = fm.mkdir(args.mkdir)
    elif args.cat:
        success, msg = fm.cat(args.cat)
    elif args.stat:
        success, msg = fm.stat(args.stat)
    elif args.pull_app_data:
        success, msg = fm.pull_app_data(args.pull_app_data, local_dir=args.output)
    elif args.pull_prefs:
        success, msg = fm.pull_shared_prefs(args.pull_prefs, local_dir=args.output)
    elif args.pull_db:
        success, msg = fm.pull_database(args.pull_db, db_name=args.db_name, local_dir=args.output)
    else:
        parser.print_help()
        sys.exit(1)

    if args.json:
        print(json.dumps({"success": success, "message": msg if isinstance(msg, str) else str(msg)}))
    else:
        print(msg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
