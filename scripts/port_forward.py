#!/usr/bin/env python3
"""ADB port forwarding for local development server access."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


# Common presets for development
PORT_PRESETS = {
    "firebase-auth": {"port": 9099, "description": "Firebase Auth Emulator"},
    "firebase-firestore": {"port": 8080, "description": "Firebase Firestore Emulator"},
    "firebase-storage": {"port": 9199, "description": "Firebase Storage Emulator"},
    "firebase-functions": {"port": 5001, "description": "Firebase Functions Emulator"},
    "firebase-hosting": {"port": 5000, "description": "Firebase Hosting Emulator"},
    "firebase-ui": {"port": 4000, "description": "Firebase Emulator UI"},
    "react-dev": {"port": 3000, "description": "React Dev Server"},
    "metro-bundler": {"port": 8081, "description": "React Native Metro Bundler"},
    "webpack": {"port": 8080, "description": "Webpack Dev Server"},
    "api-server": {"port": 8000, "description": "API Server"},
}


def forward_port(serial, local_port, remote_port=None):
    """Forward device port to host (device -> host access)."""
    remote_port = remote_port or local_port
    result = run_command(build_adb_command(
        ["forward", f"tcp:{local_port}", f"tcp:{remote_port}"],
        serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"Forward: host:{local_port} → device:{remote_port}"
    return False, f"Failed to forward port {local_port}"


def reverse_port(serial, device_port, host_port=None):
    """Reverse port: device can reach host's port (host -> device access)."""
    host_port = host_port or device_port
    result = run_command(build_adb_command(
        ["reverse", f"tcp:{device_port}", f"tcp:{host_port}"],
        serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"Reverse: device:{device_port} → host:{host_port}"
    return False, f"Failed to reverse port {device_port}"


def list_forwards(serial):
    """List all port forwards."""
    result = run_command(build_adb_command(["forward", "--list"], serial=serial))
    forwards = []
    if result and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                forwards.append({
                    "serial": parts[0],
                    "local": parts[1],
                    "remote": parts[2],
                    "type": "forward",
                })

    result = run_command(build_adb_command(["reverse", "--list"], serial=serial))
    if result and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                forwards.append({
                    "serial": parts[0],
                    "device": parts[1],
                    "host": parts[2],
                    "type": "reverse",
                })

    return forwards


def remove_forward(serial, local_port):
    """Remove a specific port forward."""
    result = run_command(build_adb_command(
        ["forward", "--remove", f"tcp:{local_port}"], serial=serial
    ))
    return result and result.returncode == 0


def remove_reverse(serial, device_port):
    """Remove a specific reverse port."""
    result = run_command(build_adb_command(
        ["reverse", "--remove", f"tcp:{device_port}"], serial=serial
    ))
    return result and result.returncode == 0


def clear_all(serial):
    """Remove all port forwards and reverses."""
    run_command(build_adb_command(["forward", "--remove-all"], serial=serial))
    run_command(build_adb_command(["reverse", "--remove-all"], serial=serial))
    return True, "All port forwards and reverses cleared"


def apply_preset(serial, preset_name, direction="reverse"):
    """Apply a port forwarding preset."""
    if preset_name not in PORT_PRESETS:
        return False, f"Unknown preset: {preset_name}. Available: {', '.join(PORT_PRESETS.keys())}"

    preset = PORT_PRESETS[preset_name]
    port = preset["port"]

    if direction == "reverse":
        success, msg = reverse_port(serial, port, port)
    else:
        success, msg = forward_port(serial, port, port)

    if success:
        return True, f"{preset['description']}: {msg}"
    return success, msg


def main():
    parser = argparse.ArgumentParser(description="ADB port forwarding management")
    parser.add_argument("--forward", nargs="+", metavar="PORT",
                        help="Forward ports: LOCAL [REMOTE] (host:LOCAL → device:REMOTE)")
    parser.add_argument("--reverse", nargs="+", metavar="PORT",
                        help="Reverse ports: DEVICE [HOST] (device:DEVICE → host:HOST)")
    parser.add_argument("--preset", help="Apply a port preset (e.g., firebase-auth, firebase-firestore)")
    parser.add_argument("--preset-direction", choices=["forward", "reverse"], default="reverse",
                        help="Direction for preset (default: reverse)")
    parser.add_argument("--firebase", action="store_true",
                        help="Shortcut: reverse all Firebase emulator ports")
    parser.add_argument("--list", action="store_true", help="List all port forwards")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")
    parser.add_argument("--remove-forward", type=int, metavar="PORT", help="Remove a forward")
    parser.add_argument("--remove-reverse", type=int, metavar="PORT", help="Remove a reverse")
    parser.add_argument("--clear", action="store_true", help="Clear all forwards and reverses")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    if args.list_presets:
        if args.json:
            print(json.dumps(PORT_PRESETS, indent=2))
        else:
            print("Available port presets:")
            for key, val in PORT_PRESETS.items():
                print(f"  {key:25s} → port {val['port']} ({val['description']})")
        sys.exit(0)

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.list:
        forwards = list_forwards(serial)
        if args.json:
            print(json.dumps({"forwards": forwards}, indent=2))
        else:
            if forwards:
                for f in forwards:
                    if f["type"] == "forward":
                        print(f"  [forward] {f['local']} → {f['remote']}")
                    else:
                        print(f"  [reverse] {f['device']} → {f['host']}")
            else:
                print("No active port forwards")
        sys.exit(0)

    if args.clear:
        success, msg = clear_all(serial)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0)

    if args.firebase:
        firebase_presets = [k for k in PORT_PRESETS if k.startswith("firebase-")]
        results = []
        for preset in firebase_presets:
            success, msg = apply_preset(serial, preset, "reverse")
            results.append({"preset": preset, "success": success, "message": msg})
        if args.json:
            print(json.dumps({"results": results}, indent=2))
        else:
            for r in results:
                status = "OK" if r["success"] else "FAIL"
                print(f"[{status}] {r['message']}")
        sys.exit(0)

    if args.preset:
        success, msg = apply_preset(serial, args.preset, args.preset_direction)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)

    if args.forward:
        ports = [int(p) for p in args.forward]
        local_port = ports[0]
        remote_port = ports[1] if len(ports) > 1 else local_port
        success, msg = forward_port(serial, local_port, remote_port)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)

    if args.reverse:
        ports = [int(p) for p in args.reverse]
        device_port = ports[0]
        host_port = ports[1] if len(ports) > 1 else device_port
        success, msg = reverse_port(serial, device_port, host_port)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)

    if args.remove_forward:
        success = remove_forward(serial, args.remove_forward)
        msg = f"Removed forward: {args.remove_forward}" if success else "Failed to remove"
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)

    if args.remove_reverse:
        success = remove_reverse(serial, args.remove_reverse)
        msg = f"Removed reverse: {args.remove_reverse}" if success else "Failed to remove"
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0 if success else 1)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
