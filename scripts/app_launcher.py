#!/usr/bin/env python3
"""Android app lifecycle management."""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


class AppLauncher:
    def __init__(self, serial=None):
        self.serial = serial

    def launch(self, package, activity=None, wait=False):
        """Launch an app by package name."""
        if activity:
            component = f"{package}/{activity}"
            args = ["shell", "am", "start", "-n", component]
        else:
            args = ["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]

        if wait:
            args = ["shell", "am", "start", "-W", "-n", f"{package}/.MainActivity"] if activity is None else args

        result = run_command(build_adb_command(args, serial=self.serial))
        if result and result.returncode == 0:
            return True, f"Launched {package}"
        return False, f"Failed to launch {package}"

    def terminate(self, package):
        """Force stop an app."""
        result = run_command(build_adb_command(
            ["shell", "am", "force-stop", package], serial=self.serial
        ))
        if result and result.returncode == 0:
            return True, f"Terminated {package}"
        return False, f"Failed to terminate {package}"

    def restart(self, package, activity=None):
        """Restart an app."""
        self.terminate(package)
        time.sleep(1)
        return self.launch(package, activity)

    def install(self, apk_path):
        """Install an APK."""
        result = run_command(
            build_adb_command(["install", "-r", apk_path], serial=self.serial),
            timeout=120
        )
        if result and result.returncode == 0 and "Success" in result.stdout:
            return True, f"Installed {apk_path}"
        error = result.stderr if result else "Unknown error"
        return False, f"Failed to install: {error}"

    def uninstall(self, package):
        """Uninstall an app."""
        result = run_command(build_adb_command(
            ["uninstall", package], serial=self.serial
        ))
        if result and result.returncode == 0 and "Success" in result.stdout:
            return True, f"Uninstalled {package}"
        return False, f"Failed to uninstall {package}"

    def open_url(self, url):
        """Open a URL / deep link."""
        result = run_command(build_adb_command(
            ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url],
            serial=self.serial
        ))
        if result and result.returncode == 0:
            return True, f"Opened URL: {url}"
        return False, f"Failed to open URL: {url}"

    def list_apps(self, third_party_only=True):
        """List installed packages."""
        args = ["shell", "pm", "list", "packages"]
        if third_party_only:
            args.append("-3")
        result = run_command(build_adb_command(args, serial=self.serial))
        if result and result.returncode == 0:
            packages = [
                line.replace("package:", "").strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            return packages
        return []

    def get_app_state(self, package):
        """Check if an app is running."""
        result = run_command(build_adb_command(
            ["shell", "pidof", package], serial=self.serial
        ))
        if result and result.returncode == 0 and result.stdout.strip():
            return {"state": "running", "pid": result.stdout.strip()}
        return {"state": "stopped", "pid": None}

    def get_current_activity(self):
        """Get the current foreground activity."""
        result = run_command(build_adb_command(
            ["shell", "dumpsys", "activity", "activities"],
            serial=self.serial
        ))
        if result and result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "mResumedActivity" in line or "mFocusedActivity" in line:
                    return line.strip()
        return None

    def clear_data(self, package):
        """Clear app data."""
        result = run_command(build_adb_command(
            ["shell", "pm", "clear", package], serial=self.serial
        ))
        if result and result.returncode == 0:
            return True, f"Cleared data for {package}"
        return False, f"Failed to clear data for {package}"


def main():
    parser = argparse.ArgumentParser(description="Android app lifecycle management")
    parser.add_argument("--launch", metavar="PACKAGE", help="Launch app by package name")
    parser.add_argument("--activity", help="Activity to launch (optional)")
    parser.add_argument("--terminate", metavar="PACKAGE", help="Force stop app")
    parser.add_argument("--restart", metavar="PACKAGE", help="Restart app")
    parser.add_argument("--install", metavar="APK", help="Install APK file")
    parser.add_argument("--uninstall", metavar="PACKAGE", help="Uninstall app")
    parser.add_argument("--open-url", metavar="URL", help="Open URL / deep link")
    parser.add_argument("--list", action="store_true", help="List installed apps")
    parser.add_argument("--list-all", action="store_true", help="List all installed apps (including system)")
    parser.add_argument("--state", metavar="PACKAGE", help="Check if app is running")
    parser.add_argument("--current", action="store_true", help="Show current foreground activity")
    parser.add_argument("--clear", metavar="PACKAGE", help="Clear app data")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    launcher = AppLauncher(serial=serial)

    if args.launch:
        success, msg = launcher.launch(args.launch, activity=args.activity)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)
    elif args.terminate:
        success, msg = launcher.terminate(args.terminate)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)
    elif args.restart:
        success, msg = launcher.restart(args.restart, activity=args.activity)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)
    elif args.install:
        success, msg = launcher.install(args.install)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)
    elif args.uninstall:
        success, msg = launcher.uninstall(args.uninstall)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)
    elif args.open_url:
        success, msg = launcher.open_url(args.open_url)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)
    elif args.list or args.list_all:
        packages = launcher.list_apps(third_party_only=not args.list_all)
        if args.json:
            print(json.dumps({"packages": packages}))
        else:
            for p in packages:
                print(p)
    elif args.state:
        state = launcher.get_app_state(args.state)
        if args.json:
            print(json.dumps(state))
        else:
            print(f"{args.state}: {state['state']}" + (f" (PID: {state['pid']})" if state['pid'] else ""))
    elif args.current:
        activity = launcher.get_current_activity()
        print(activity or "No foreground activity detected")
    elif args.clear:
        success, msg = launcher.clear_data(args.clear)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
