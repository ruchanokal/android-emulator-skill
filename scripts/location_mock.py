#!/usr/bin/env python3
"""Mock GPS location on Android emulator."""

import argparse
import json
import sys
import os
import re
import telnetlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


# Common location presets
LOCATION_PRESETS = {
    "istanbul-kadikoy": {"lat": 40.9903, "lng": 29.0291, "name": "Kadıköy, İstanbul"},
    "istanbul-besiktas": {"lat": 41.0422, "lng": 29.0067, "name": "Beşiktaş, İstanbul"},
    "istanbul-uskudar": {"lat": 41.0234, "lng": 29.0153, "name": "Üsküdar, İstanbul"},
    "istanbul-fatih": {"lat": 41.0186, "lng": 28.9397, "name": "Fatih, İstanbul"},
    "istanbul-sisli": {"lat": 41.0602, "lng": 28.9877, "name": "Şişli, İstanbul"},
    "ankara": {"lat": 39.9334, "lng": 32.8597, "name": "Ankara"},
    "izmir": {"lat": 38.4237, "lng": 27.1428, "name": "İzmir"},
    "antalya": {"lat": 36.8969, "lng": 30.7133, "name": "Antalya"},
    "bursa": {"lat": 40.1885, "lng": 29.0610, "name": "Bursa"},
    "london": {"lat": 51.5074, "lng": -0.1278, "name": "London"},
    "paris": {"lat": 48.8566, "lng": 2.3522, "name": "Paris"},
    "new-york": {"lat": 40.7128, "lng": -74.0060, "name": "New York"},
    "tokyo": {"lat": 35.6762, "lng": 139.6503, "name": "Tokyo"},
    "berlin": {"lat": 52.5200, "lng": 13.4050, "name": "Berlin"},
}


def _get_emulator_port(serial):
    """Extract emulator console port from serial."""
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


def set_location(serial, lat, lng, altitude=0):
    """Set GPS location via emulator console."""
    port = _get_emulator_port(serial)
    if not port:
        return False, "Cannot determine emulator console port (is this an emulator?)"

    try:
        tn = telnetlib.Telnet("localhost", port, timeout=5)
        tn.read_until(b"OK", timeout=3)

        token = _get_auth_token()
        if token:
            tn.write(f"auth {token}\n".encode())
            tn.read_until(b"OK", timeout=3)

        cmd = f"geo fix {lng} {lat} {altitude}"
        tn.write(f"{cmd}\n".encode())
        response = tn.read_until(b"OK", timeout=5).decode()

        tn.write(b"quit\n")
        tn.close()

        return True, f"Location set to ({lat}, {lng})"
    except Exception as e:
        # Fallback: try adb emu command
        result = run_command(build_adb_command(
            ["emu", "geo", "fix", str(lng), str(lat), str(altitude)],
            serial=serial
        ))
        if result and result.returncode == 0:
            return True, f"Location set to ({lat}, {lng})"
        return False, f"Failed to set location: {e}"


def set_location_preset(serial, preset_name):
    """Set location from a preset."""
    if preset_name not in LOCATION_PRESETS:
        return False, f"Unknown preset: {preset_name}. Available: {', '.join(LOCATION_PRESETS.keys())}"

    preset = LOCATION_PRESETS[preset_name]
    success, msg = set_location(serial, preset["lat"], preset["lng"])
    if success:
        return True, f"Location set to {preset['name']} ({preset['lat']}, {preset['lng']})"
    return success, msg


def enable_mock_location(serial, package=None):
    """Enable mock location provider in developer settings."""
    run_command(build_adb_command(
        ["shell", "settings", "put", "secure", "mock_location", "1"],
        serial=serial
    ))
    if package:
        run_command(build_adb_command(
            ["shell", "appops", "set", package, "android:mock_location", "allow"],
            serial=serial
        ))
    return True, "Mock location enabled"


def main():
    parser = argparse.ArgumentParser(description="Mock GPS location on Android emulator")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lng", type=float, help="Longitude")
    parser.add_argument("--altitude", type=float, default=0, help="Altitude in meters")
    parser.add_argument("--preset", choices=list(LOCATION_PRESETS.keys()),
                        help="Use a location preset")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")
    parser.add_argument("--enable-mock", action="store_true", help="Enable mock location")
    parser.add_argument("--package", help="Package name for mock location permission")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    if args.list_presets:
        if args.json:
            print(json.dumps(LOCATION_PRESETS, indent=2, ensure_ascii=False))
        else:
            print("Available location presets:")
            for key, val in LOCATION_PRESETS.items():
                print(f"  {key:25s} → {val['name']} ({val['lat']}, {val['lng']})")
        sys.exit(0)

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.enable_mock:
        success, msg = enable_mock_location(serial, package=args.package)
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)

    if args.preset:
        success, msg = set_location_preset(serial, args.preset)
    elif args.lat is not None and args.lng is not None:
        success, msg = set_location(serial, args.lat, args.lng, args.altitude)
    elif not args.enable_mock and not args.list_presets:
        parser.print_help()
        sys.exit(1)
    else:
        sys.exit(0)

    if args.json:
        print(json.dumps({"success": success, "message": msg}))
    else:
        print(msg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
