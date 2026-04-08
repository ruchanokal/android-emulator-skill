#!/usr/bin/env python3
"""Android device/emulator utility functions."""

import subprocess
import sys
import re
import json
import os
import shutil


def _find_android_sdk():
    """Find Android SDK path and add tools to PATH if needed."""
    # Check if adb is already in PATH
    if shutil.which("adb"):
        return

    # Common SDK locations
    sdk_paths = [
        os.environ.get("ANDROID_HOME", ""),
        os.environ.get("ANDROID_SDK_ROOT", ""),
        os.path.expanduser("~/Library/Android/sdk"),  # macOS default
        os.path.expanduser("~/Android/Sdk"),  # Linux default
        "C:\\Users\\{}\\AppData\\Local\\Android\\Sdk".format(os.environ.get("USERNAME", "")),  # Windows
    ]

    for sdk in sdk_paths:
        if sdk and os.path.isdir(sdk):
            platform_tools = os.path.join(sdk, "platform-tools")
            emulator_dir = os.path.join(sdk, "emulator")
            cmdline_tools = os.path.join(sdk, "cmdline-tools", "latest", "bin")

            additions = []
            if os.path.isdir(platform_tools):
                additions.append(platform_tools)
            if os.path.isdir(emulator_dir):
                additions.append(emulator_dir)
            if os.path.isdir(cmdline_tools):
                additions.append(cmdline_tools)

            if additions:
                os.environ["PATH"] = os.pathsep.join(additions) + os.pathsep + os.environ.get("PATH", "")
                os.environ["ANDROID_HOME"] = sdk
                return


# Auto-detect SDK on import
_find_android_sdk()


def build_adb_command(args, serial=None):
    """Build an adb command list."""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    return cmd


def build_emulator_command(args):
    """Build an emulator command list."""
    return ["emulator"] + args


def run_command(cmd, timeout=30, capture=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {' '.join(cmd)}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}", file=sys.stderr)
        return None


def get_connected_devices():
    """Get list of connected devices/emulators."""
    result = run_command(["adb", "devices"])
    if not result or result.returncode != 0:
        return []

    devices = []
    for line in result.stdout.strip().split("\n")[1:]:
        line = line.strip()
        if not line or "offline" in line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1] == "device":
            serial = parts[0]
            is_emulator = serial.startswith("emulator-")
            devices.append({
                "serial": serial,
                "is_emulator": is_emulator,
                "type": "emulator" if is_emulator else "physical"
            })
    return devices


def get_running_emulators():
    """Get list of running emulators with their AVD names."""
    devices = get_connected_devices()
    emulators = []
    for d in devices:
        if d["is_emulator"]:
            avd_name = get_avd_name(d["serial"])
            d["avd_name"] = avd_name
            emulators.append(d)
    return emulators


def get_avd_name(serial):
    """Get the AVD name for an emulator."""
    result = run_command(build_adb_command(["emu", "avd", "name"], serial=serial))
    if result and result.returncode == 0:
        lines = result.stdout.strip().split("\n")
        if lines:
            return lines[0].strip()
    return "unknown"


def list_avds():
    """List available AVDs."""
    result = run_command(["emulator", "-list-avds"])
    if not result or result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def resolve_serial(serial=None, name=None):
    """Resolve device serial from args or auto-detect."""
    if serial:
        return serial

    if name:
        emulators = get_running_emulators()
        for emu in emulators:
            if emu.get("avd_name", "").lower() == name.lower():
                return emu["serial"]
        raise RuntimeError(f"No running emulator found with AVD name: {name}")

    devices = get_connected_devices()
    emulators = [d for d in devices if d["is_emulator"]]

    if len(emulators) == 1:
        return emulators[0]["serial"]
    elif len(emulators) > 1:
        return emulators[0]["serial"]
    elif len(devices) == 1:
        return devices[0]["serial"]
    elif len(devices) > 1:
        return devices[0]["serial"]
    else:
        raise RuntimeError("No connected devices or emulators found. Start one with: emulator -avd <name>")


def get_screen_size(serial=None):
    """Get device screen size."""
    result = run_command(build_adb_command(["shell", "wm", "size"], serial=serial))
    if result and result.returncode == 0:
        match = re.search(r"(\d+)x(\d+)", result.stdout)
        if match:
            return int(match.group(1)), int(match.group(2))
    return 1080, 1920  # Default


def get_device_info(serial=None):
    """Get device info."""
    info = {}
    commands = {
        "model": ["shell", "getprop", "ro.product.model"],
        "manufacturer": ["shell", "getprop", "ro.product.manufacturer"],
        "android_version": ["shell", "getprop", "ro.build.version.release"],
        "sdk_version": ["shell", "getprop", "ro.build.version.sdk"],
        "device": ["shell", "getprop", "ro.product.device"],
    }
    for key, args in commands.items():
        result = run_command(build_adb_command(args, serial=serial))
        if result and result.returncode == 0:
            info[key] = result.stdout.strip()
    return info
