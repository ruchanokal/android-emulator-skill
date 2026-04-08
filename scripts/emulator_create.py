#!/usr/bin/env python3
"""Create Android Virtual Devices (AVDs) dynamically."""

import argparse
import json
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import list_avds, run_command


def list_system_images():
    """List available system images."""
    result = run_command(["sdkmanager", "--list"], timeout=30)
    if not result or result.returncode != 0:
        return []

    images = []
    for line in result.stdout.split("\n"):
        if "system-images" in line and "installed" in line.lower():
            parts = line.strip().split("|")
            if parts:
                images.append(parts[0].strip())
    return images


def list_device_types():
    """List available device types."""
    result = run_command(["avdmanager", "list", "device", "-c"], timeout=15)
    if not result or result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def create_avd(name, device="pixel_6", package=None, force=False):
    """Create a new AVD."""
    if not package:
        # Try to find a suitable system image
        result = run_command(["sdkmanager", "--list", "--short"], timeout=30)
        if result and result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "system-images" in line and "google_apis" in line and "x86_64" in line:
                    package = line.strip().split("|")[0].strip()
                    break

    if not package:
        return False, "No system image found. Install one with: sdkmanager 'system-images;android-34;google_apis;x86_64'"

    cmd = ["avdmanager", "create", "avd", "-n", name, "-d", device, "-k", package]
    if force:
        cmd.append("--force")

    result = subprocess.run(
        cmd, input="no\n", capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        return True, f"Created AVD: {name} (device={device})"
    return False, f"Failed to create AVD: {result.stderr}"


def main():
    parser = argparse.ArgumentParser(description="Create Android Virtual Devices")
    parser.add_argument("--name", help="AVD name")
    parser.add_argument("--device", default="pixel_6", help="Device type (default: pixel_6)")
    parser.add_argument("--package", help="System image package")
    parser.add_argument("--force", action="store_true", help="Overwrite existing AVD")
    parser.add_argument("--list-devices", action="store_true", help="List available device types")
    parser.add_argument("--list-images", action="store_true", help="List available system images")
    parser.add_argument("--list-avds", action="store_true", help="List existing AVDs")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.list_devices:
        devices = list_device_types()
        if args.json:
            print(json.dumps({"devices": devices}))
        else:
            print("Available device types:")
            for d in devices[:20]:
                print(f"  - {d}")
    elif args.list_images:
        images = list_system_images()
        if args.json:
            print(json.dumps({"images": images}))
        else:
            print("Available system images:")
            for img in images:
                print(f"  - {img}")
    elif args.list_avds:
        avds = list_avds()
        if args.json:
            print(json.dumps({"avds": avds}))
        else:
            for avd in avds:
                print(f"  - {avd}")
    elif args.name:
        success, msg = create_avd(args.name, device=args.device, package=args.package, force=args.force)
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
