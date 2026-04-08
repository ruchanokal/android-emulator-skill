#!/usr/bin/env python3
"""Control network settings on Android emulator — WiFi, airplane mode, throttling."""

import argparse
import json
import sys
import os
import socket
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


# Network speed presets for emulator console
NETWORK_PRESETS = {
    "full": {"speed": "full", "delay": "none", "description": "No throttling"},
    "5g": {"speed": "full", "delay": "none", "description": "5G (no throttling)"},
    "4g": {"speed": "lte", "delay": "200", "description": "4G LTE (~100Mbps, 200ms delay)"},
    "3g": {"speed": "umts", "delay": "300", "description": "3G UMTS (~2Mbps, 300ms delay)"},
    "edge": {"speed": "edge", "delay": "500", "description": "EDGE (~200Kbps, 500ms delay)"},
    "gprs": {"speed": "gprs", "delay": "800", "description": "GPRS (~40Kbps, 800ms delay)"},
    "none": {"speed": "gsm", "delay": "9999", "description": "Effectively no connection"},
}


def _get_emulator_port(serial):
    """Extract emulator console port from serial (e.g., emulator-5554 -> 5554)."""
    match = re.match(r"emulator-(\d+)", serial)
    if match:
        return int(match.group(1))
    return None


def _get_auth_token():
    """Read emulator console auth token."""
    token_path = os.path.expanduser("~/.emulator_console_auth_token")
    if os.path.exists(token_path):
        with open(token_path) as f:
            return f.read().strip()
    return ""


def _send_console_command(serial, command):
    """Send a command to the emulator console via socket."""
    port = _get_emulator_port(serial)
    if not port:
        return False, "Cannot determine emulator console port"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("localhost", port))

        # Read welcome message
        _recv_until(sock, b"OK")

        # Authenticate
        token = _get_auth_token()
        if token:
            sock.sendall(f"auth {token}\n".encode())
            _recv_until(sock, b"OK")

        # Send command
        sock.sendall(f"{command}\n".encode())
        response = _recv_until(sock, b"OK")

        sock.sendall(b"quit\n")
        sock.close()
        return True, response.strip()
    except Exception as e:
        return False, str(e)


def _recv_until(sock, marker, bufsize=4096):
    """Read from socket until marker is found."""
    data = b""
    while marker not in data:
        try:
            chunk = sock.recv(bufsize)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
    return data.decode(errors="replace")


def set_wifi(serial, enabled):
    """Toggle WiFi on/off."""
    state = "enable" if enabled else "disable"
    result = run_command(build_adb_command(
        ["shell", "svc", "wifi", state], serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"WiFi {'enabled' if enabled else 'disabled'}"
    return False, "Failed to change WiFi state"


def set_airplane_mode(serial, enabled):
    """Toggle airplane mode."""
    value = "1" if enabled else "0"
    # Set the setting
    run_command(build_adb_command(
        ["shell", "settings", "put", "global", "airplane_mode_on", value],
        serial=serial
    ))
    # Broadcast the change
    run_command(build_adb_command(
        ["shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE",
         "--ez", "state", "true" if enabled else "false"],
        serial=serial
    ))
    return True, f"Airplane mode {'enabled' if enabled else 'disabled'}"


def set_mobile_data(serial, enabled):
    """Toggle mobile data on/off."""
    state = "enable" if enabled else "disable"
    result = run_command(build_adb_command(
        ["shell", "svc", "data", state], serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"Mobile data {'enabled' if enabled else 'disabled'}"
    return False, "Failed to change mobile data state"


def set_network_speed(serial, preset):
    """Set network speed/delay via emulator console."""
    if preset not in NETWORK_PRESETS:
        return False, f"Unknown preset: {preset}. Available: {', '.join(NETWORK_PRESETS.keys())}"

    config = NETWORK_PRESETS[preset]

    # Try emulator console first
    success1, msg1 = _send_console_command(serial, f"network speed {config['speed']}")
    success2, msg2 = _send_console_command(serial, f"network delay {config['delay']}")

    if success1 and success2:
        return True, f"Network set to {preset}: {config['description']}"

    # Fallback info
    return False, f"Console command failed. Make sure emulator is running. Error: {msg1}"


def get_network_status(serial):
    """Get current network status."""
    info = {}

    # WiFi state
    result = run_command(build_adb_command(
        ["shell", "settings", "get", "global", "wifi_on"], serial=serial
    ))
    if result:
        info["wifi"] = "on" if result.stdout.strip() == "1" else "off"

    # Airplane mode
    result = run_command(build_adb_command(
        ["shell", "settings", "get", "global", "airplane_mode_on"], serial=serial
    ))
    if result:
        info["airplane_mode"] = "on" if result.stdout.strip() == "1" else "off"

    # Mobile data
    result = run_command(build_adb_command(
        ["shell", "settings", "get", "global", "mobile_data"], serial=serial
    ))
    if result:
        info["mobile_data"] = "on" if result.stdout.strip() == "1" else "off"

    # Connection check
    result = run_command(build_adb_command(
        ["shell", "ping", "-c", "1", "-W", "2", "8.8.8.8"], serial=serial
    ), timeout=5)
    info["internet"] = "connected" if result and result.returncode == 0 else "disconnected"

    return info


def main():
    parser = argparse.ArgumentParser(description="Control Android network settings")
    parser.add_argument("--wifi", choices=["on", "off"], help="Toggle WiFi")
    parser.add_argument("--airplane", choices=["on", "off"], help="Toggle airplane mode")
    parser.add_argument("--data", choices=["on", "off"], help="Toggle mobile data")
    parser.add_argument("--throttle", choices=list(NETWORK_PRESETS.keys()),
                        help="Set network speed preset")
    parser.add_argument("--status", action="store_true", help="Show network status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    results = []

    if args.status:
        status = get_network_status(serial)
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            for k, v in status.items():
                print(f"  {k}: {v}")
        sys.exit(0)

    if args.wifi:
        success, msg = set_wifi(serial, args.wifi == "on")
        results.append({"action": "wifi", "success": success, "message": msg})

    if args.airplane:
        success, msg = set_airplane_mode(serial, args.airplane == "on")
        results.append({"action": "airplane", "success": success, "message": msg})

    if args.data:
        success, msg = set_mobile_data(serial, args.data == "on")
        results.append({"action": "data", "success": success, "message": msg})

    if args.throttle:
        success, msg = set_network_speed(serial, args.throttle)
        results.append({"action": "throttle", "success": success, "message": msg})

    if not results:
        parser.print_help()
        sys.exit(1)

    all_success = all(r["success"] for r in results)
    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        for r in results:
            print(r["message"])

    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
