#!/usr/bin/env python3
"""Factory reset Android emulators (wipe data) without deletion."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import list_avds, get_running_emulators, run_command, build_adb_command


def wipe_avd(name, serial=None):
    """Wipe AVD data. If running, shutdown first."""
    if serial:
        # Shutdown if running
        run_command(build_adb_command(["emu", "kill"], serial=serial))
        import time
        time.sleep(3)

    # Wipe by launching with -wipe-data and immediately killing
    # Or delete userdata files directly
    avd_dir = os.path.expanduser(f"~/.android/avd/{name}.avd")
    userdata = os.path.join(avd_dir, "userdata-qemu.img")
    userdata2 = os.path.join(avd_dir, "userdata.img")
    snapshots = os.path.join(avd_dir, "snapshots")

    wiped = []
    for path in [userdata, userdata2]:
        if os.path.exists(path):
            os.remove(path)
            wiped.append(os.path.basename(path))

    if os.path.exists(snapshots):
        import shutil
        shutil.rmtree(snapshots)
        wiped.append("snapshots/")

    if wiped:
        return True, f"Wiped {name}: removed {', '.join(wiped)}"
    return True, f"Wiped {name}: no user data found (already clean)"


def main():
    parser = argparse.ArgumentParser(description="Wipe Android emulator data")
    parser.add_argument("--name", help="AVD name to wipe")
    parser.add_argument("--all", action="store_true", help="Wipe all AVDs")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.all:
        avds = list_avds()
        if not args.yes:
            print(f"Wipe data for {len(avds)} AVDs? Use --yes to confirm")
            sys.exit(1)
        results = []
        for avd in avds:
            success, msg = wipe_avd(avd)
            results.append({"avd": avd, "success": success, "message": msg})
        if args.json:
            print(json.dumps({"results": results}))
        else:
            for r in results:
                print(r["message"])
    elif args.name:
        if not args.yes:
            print(f"Wipe data for '{args.name}'? Use --yes to confirm")
            sys.exit(1)
        # Check if running
        running = get_running_emulators()
        serial = None
        for emu in running:
            if emu.get("avd_name", "").lower() == args.name.lower():
                serial = emu["serial"]
                break
        success, msg = wipe_avd(args.name, serial=serial)
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
