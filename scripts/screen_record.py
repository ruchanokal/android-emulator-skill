#!/usr/bin/env python3
"""Record screen video from Android device."""

import argparse
import json
import sys
import os
import time
import subprocess
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


class ScreenRecorder:
    def __init__(self, serial=None):
        self.serial = serial
        self._process = None
        self._device_path = "/sdcard/screenrecord.mp4"

    def record(self, duration=10, output=None, size=None, bitrate=None):
        """Record screen for specified duration."""
        output = output or f"/tmp/android_record_{int(time.time())}.mp4"

        cmd = build_adb_command(["shell", "screenrecord"], serial=self.serial)

        if duration:
            cmd.extend(["--time-limit", str(min(duration, 180))])  # Max 3 minutes
        if size:
            cmd.extend(["--size", size])  # e.g., "720x1280"
        if bitrate:
            cmd.extend(["--bit-rate", str(bitrate)])

        cmd.append(self._device_path)

        start = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
        except subprocess.TimeoutExpired:
            pass

        elapsed = time.time() - start

        # Pull file from device
        pull_result = run_command(build_adb_command(
            ["pull", self._device_path, output], serial=self.serial
        ), timeout=30)

        # Clean up device file
        run_command(build_adb_command(
            ["shell", "rm", self._device_path], serial=self.serial
        ))

        if pull_result and pull_result.returncode == 0 and os.path.exists(output):
            file_size = os.path.getsize(output)
            return True, {
                "file": output,
                "duration": f"{elapsed:.1f}s",
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
            }
        return False, {"error": "Failed to pull recording from device"}

    def start_background(self, output=None, size=None, bitrate=None):
        """Start recording in background (use stop() to finish)."""
        cmd = build_adb_command(["shell", "screenrecord"], serial=self.serial)
        if size:
            cmd.extend(["--size", size])
        if bitrate:
            cmd.extend(["--bit-rate", str(bitrate)])
        cmd.append(self._device_path)

        self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._output = output or f"/tmp/android_record_{int(time.time())}.mp4"
        self._start_time = time.time()
        return True, f"Recording started (PID: {self._process.pid})"

    def stop_background(self):
        """Stop background recording and pull file."""
        if not self._process:
            # Try to kill any running screenrecord on device
            run_command(build_adb_command(
                ["shell", "pkill", "-INT", "screenrecord"], serial=self.serial
            ))
            time.sleep(2)
        else:
            self._process.send_signal(signal.SIGINT)
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            time.sleep(1)

        elapsed = time.time() - getattr(self, "_start_time", time.time())
        output = getattr(self, "_output", f"/tmp/android_record_{int(time.time())}.mp4")

        # Pull file
        pull_result = run_command(build_adb_command(
            ["pull", self._device_path, output], serial=self.serial
        ), timeout=30)

        # Clean up
        run_command(build_adb_command(
            ["shell", "rm", self._device_path], serial=self.serial
        ))

        if pull_result and pull_result.returncode == 0 and os.path.exists(output):
            file_size = os.path.getsize(output)
            return True, {
                "file": output,
                "duration": f"{elapsed:.1f}s",
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
            }
        return False, {"error": "Failed to pull recording"}


def main():
    parser = argparse.ArgumentParser(description="Record Android screen video")
    parser.add_argument("--duration", type=int, default=10, help="Recording duration in seconds (max 180)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--size", help="Video size (e.g., '720x1280')")
    parser.add_argument("--bitrate", type=int, help="Bit rate (e.g., 4000000 for 4Mbps)")
    parser.add_argument("--start", action="store_true", help="Start background recording")
    parser.add_argument("--stop", action="store_true", help="Stop background recording")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    recorder = ScreenRecorder(serial=serial)

    if args.start:
        success, msg = recorder.start_background(output=args.output, size=args.size, bitrate=args.bitrate)
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
    elif args.stop:
        success, result = recorder.stop_background()
        if args.json:
            print(json.dumps({"success": success, **result}, indent=2))
        else:
            if success:
                print(f"Recording saved: {result['file']} ({result['duration']}, {result['size_mb']}MB)")
            else:
                print(f"Error: {result.get('error', 'Unknown')}")
    else:
        print(f"Recording for {args.duration}s...")
        success, result = recorder.record(
            duration=args.duration, output=args.output,
            size=args.size, bitrate=args.bitrate
        )
        if args.json:
            print(json.dumps({"success": success, **result}, indent=2))
        else:
            if success:
                print(f"Recording saved: {result['file']} ({result['duration']}, {result['size_mb']}MB)")
            else:
                print(f"Error: {result.get('error', 'Unknown')}")

    sys.exit(0)


if __name__ == "__main__":
    main()
