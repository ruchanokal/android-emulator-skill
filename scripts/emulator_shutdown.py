#!/usr/bin/env python3
"""Shutdown Android emulators gracefully."""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import (
    resolve_serial, get_running_emulators, get_connected_devices,
    build_adb_command, run_command
)


class EmulatorShutdown:
    def __init__(self):
        pass

    def shutdown(self, serial=None, name=None, verify=False, timeout=30):
        """Shutdown an emulator."""
        if name:
            emulators = get_running_emulators()
            for emu in emulators:
                if emu.get("avd_name", "").lower() == name.lower():
                    serial = emu["serial"]
                    break
            if not serial:
                return True, f"No running emulator with name: {name}"

        if not serial:
            try:
                serial = resolve_serial()
            except RuntimeError as e:
                return True, "No running emulators to shutdown"

        # Send shutdown command
        result = run_command(build_adb_command(["emu", "kill"], serial=serial))
        if not result or result.returncode != 0:
            # Fallback: use adb reboot -p (power off)
            run_command(build_adb_command(["shell", "reboot", "-p"], serial=serial))

        if verify:
            if self._verify_shutdown(serial, timeout):
                return True, f"Shutdown verified: {serial}"
            return False, f"Shutdown may not have completed: {serial}"

        return True, f"Shutdown: {serial}"

    def _verify_shutdown(self, serial, timeout):
        """Verify device has shut down."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            devices = get_connected_devices()
            found = any(d["serial"] == serial for d in devices)
            if not found:
                return True
            time.sleep(1)
        return False

    def shutdown_all(self, verify=False):
        """Shutdown all running emulators."""
        emulators = get_running_emulators()
        if not emulators:
            return [{"message": "No running emulators"}]

        results = []
        for emu in emulators:
            success, msg = self.shutdown(serial=emu["serial"], verify=verify)
            results.append({
                "serial": emu["serial"],
                "avd_name": emu.get("avd_name", "unknown"),
                "success": success,
                "message": msg,
            })
        return results


def main():
    parser = argparse.ArgumentParser(description="Shutdown Android emulators")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    parser.add_argument("--verify", action="store_true", help="Verify shutdown completion")
    parser.add_argument("--timeout", type=int, default=30, help="Verification timeout")
    parser.add_argument("--all", action="store_true", help="Shutdown all emulators")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    sd = EmulatorShutdown()

    if args.all:
        results = sd.shutdown_all(verify=args.verify)
        if args.json:
            print(json.dumps({"results": results}))
        else:
            for r in results:
                status = "OK" if r.get("success", True) else "FAIL"
                print(f"[{status}] {r.get('avd_name', '')}: {r['message']}")
        sys.exit(0)
    else:
        success, msg = sd.shutdown(
            serial=args.serial, name=args.name,
            verify=args.verify, timeout=args.timeout
        )
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
