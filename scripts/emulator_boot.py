#!/usr/bin/env python3
"""Boot Android emulators with readiness verification."""

import argparse
import json
import sys
import os
import time
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import (
    list_avds, get_running_emulators, get_connected_devices,
    build_adb_command, run_command
)


class EmulatorBooter:
    def __init__(self):
        pass

    def boot(self, avd_name, cold_boot=False, no_window=False, wait_ready=True, timeout=120):
        """Boot an emulator by AVD name."""
        # Check if already running
        running = get_running_emulators()
        for emu in running:
            if emu.get("avd_name", "").lower() == avd_name.lower():
                return True, f"Already running: {avd_name} ({emu['serial']})"

        # Check AVD exists
        avds = list_avds()
        matched = None
        for avd in avds:
            if avd.lower() == avd_name.lower():
                matched = avd
                break
        if not matched:
            # Try partial match
            for avd in avds:
                if avd_name.lower() in avd.lower():
                    matched = avd
                    break
        if not matched:
            return False, f"AVD not found: {avd_name}. Available: {', '.join(avds)}"

        # Launch emulator in background
        cmd = ["emulator", "-avd", matched]
        if cold_boot:
            cmd.append("-no-snapshot-load")
        if no_window:
            cmd.append("-no-window")

        start = time.time()
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not wait_ready:
            return True, f"Booting {matched} (PID: {proc.pid})"

        # Wait for device to appear
        serial = self._wait_for_device(matched, timeout)
        if not serial:
            return False, f"Timeout waiting for {matched} to appear"

        # Wait for boot completion
        if not self._wait_for_boot(serial, timeout - (time.time() - start)):
            return False, f"Timeout waiting for {matched} to finish booting"

        elapsed = time.time() - start
        return True, f"Device booted and ready: {serial} [{elapsed:.1f}s total]"

    def _wait_for_device(self, avd_name, timeout):
        """Wait for emulator to appear in device list."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            emulators = get_running_emulators()
            for emu in emulators:
                if emu.get("avd_name", "").lower() == avd_name.lower():
                    return emu["serial"]
            # Also check by serial appearing
            devices = get_connected_devices()
            if devices:
                for d in devices:
                    if d["is_emulator"]:
                        name = self._get_avd_name_safe(d["serial"])
                        if name and name.lower() == avd_name.lower():
                            return d["serial"]
            time.sleep(1)
        return None

    def _get_avd_name_safe(self, serial):
        """Get AVD name, handling errors gracefully."""
        try:
            result = run_command(build_adb_command(["emu", "avd", "name"], serial=serial), timeout=5)
            if result and result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines:
                    return lines[0].strip()
        except Exception:
            pass
        return None

    def _wait_for_boot(self, serial, timeout):
        """Wait for device to finish booting."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = run_command(
                build_adb_command(["shell", "getprop", "sys.boot_completed"], serial=serial),
                timeout=5
            )
            if result and result.returncode == 0 and result.stdout.strip() == "1":
                return True
            time.sleep(1)
        return False

    def boot_all(self):
        """Boot all available AVDs."""
        avds = list_avds()
        results = []
        for avd in avds:
            success, msg = self.boot(avd, wait_ready=False)
            results.append({"avd": avd, "success": success, "message": msg})
        return results


def main():
    parser = argparse.ArgumentParser(description="Boot Android emulators")
    parser.add_argument("--avd", help="AVD name to boot")
    parser.add_argument("--cold-boot", action="store_true", help="Cold boot (no snapshot)")
    parser.add_argument("--no-window", action="store_true", help="Run headless (no window)")
    parser.add_argument("--wait-ready", action="store_true", default=True, help="Wait for boot completion")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for boot")
    parser.add_argument("--timeout", type=int, default=120, help="Boot timeout in seconds")
    parser.add_argument("--list", action="store_true", help="List available AVDs")
    parser.add_argument("--running", action="store_true", help="List running emulators")
    parser.add_argument("--all", action="store_true", help="Boot all AVDs")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    booter = EmulatorBooter()

    if args.list:
        avds = list_avds()
        if args.json:
            print(json.dumps({"avds": avds}))
        else:
            if avds:
                print("Available AVDs:")
                for avd in avds:
                    print(f"  - {avd}")
            else:
                print("No AVDs found. Create one with: avdmanager create avd ...")
        sys.exit(0)

    elif args.running:
        emulators = get_running_emulators()
        if args.json:
            print(json.dumps({"emulators": emulators}))
        else:
            if emulators:
                print("Running emulators:")
                for emu in emulators:
                    print(f"  - {emu.get('avd_name', 'unknown')} ({emu['serial']})")
            else:
                print("No running emulators")
        sys.exit(0)

    elif args.all:
        results = booter.boot_all()
        if args.json:
            print(json.dumps({"results": results}))
        else:
            for r in results:
                status = "OK" if r["success"] else "FAIL"
                print(f"[{status}] {r['avd']}: {r['message']}")
        sys.exit(0)

    elif args.avd:
        wait = not args.no_wait
        success, msg = booter.boot(
            args.avd,
            cold_boot=args.cold_boot,
            no_window=args.no_window,
            wait_ready=wait,
            timeout=args.timeout,
        )
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
        sys.exit(0 if success else 1)

    else:
        parser.error("Specify --avd <name>, --list, --running, or --all")


if __name__ == "__main__":
    main()
