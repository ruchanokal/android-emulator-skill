#!/usr/bin/env python3
"""Real-time log monitoring with intelligent filtering for Android."""

import argparse
import json
import sys
import os
import subprocess
import signal
import time
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command


class LogMonitor:
    SEVERITY_MAP = {
        "V": "verbose",
        "D": "debug",
        "I": "info",
        "W": "warning",
        "E": "error",
        "F": "fatal",
    }

    SEVERITY_PRIORITY = {"verbose": 0, "debug": 1, "info": 2, "warning": 3, "error": 4, "fatal": 5}

    def __init__(self, serial=None, app=None, severity="info"):
        self.serial = serial
        self.app = app
        self.min_severity = severity.lower()
        self.stats = {"verbose": 0, "debug": 0, "info": 0, "warning": 0, "error": 0, "fatal": 0}
        self.logs = []
        self._seen = set()
        self._running = True

    def _parse_duration(self, duration_str):
        """Parse duration string (e.g., '30s', '5m', '1h')."""
        match = re.match(r"(\d+)([smh])", duration_str)
        if not match:
            return 30
        val, unit = int(match.group(1)), match.group(2)
        return val * {"s": 1, "m": 60, "h": 3600}[unit]

    def _classify_line(self, line):
        """Extract severity from logcat line."""
        # Logcat format: DATE TIME PID TID SEVERITY TAG: MESSAGE
        match = re.match(r"\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+\s+\d+\s+\d+\s+([VDIWEF])\s+", line)
        if match:
            return self.SEVERITY_MAP.get(match.group(1), "info")
        return "info"

    def _should_include(self, severity):
        """Check if severity meets minimum threshold."""
        return self.SEVERITY_PRIORITY.get(severity, 0) >= self.SEVERITY_PRIORITY.get(self.min_severity, 0)

    def _dedup_key(self, line):
        """Create dedup key by stripping timestamps and PIDs."""
        return re.sub(r"\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+\s+\d+\s+\d+", "", line).strip()

    def capture(self, duration="30s", follow=False, last=None, dedup=True):
        """Capture logs."""
        cmd = build_adb_command(["logcat"], serial=self.serial)

        if last:
            # Clear and capture recent
            cmd_clear = build_adb_command(["logcat", "-c"], serial=self.serial)
            subprocess.run(cmd_clear, capture_output=True, timeout=5)
            time.sleep(0.5)

        if self.app:
            # Get PID for app filtering
            pid_result = subprocess.run(
                build_adb_command(["shell", "pidof", self.app], serial=self.serial),
                capture_output=True, text=True, timeout=5
            )
            if pid_result.returncode == 0 and pid_result.stdout.strip():
                pid = pid_result.stdout.strip().split()[0]
                cmd = build_adb_command(["logcat", "--pid", pid], serial=self.serial)

        # Set severity filter
        severity_flag = {"verbose": "V", "debug": "D", "info": "I", "warning": "W", "error": "E", "fatal": "F"}
        flag = severity_flag.get(self.min_severity, "I")
        cmd.extend(["*:" + flag])

        if not follow:
            cmd.append("-d")  # Dump and exit

        timeout_sec = self._parse_duration(duration) if not follow else None

        def signal_handler(sig, frame):
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            start = time.time()

            for line in proc.stdout:
                if not self._running:
                    break
                if timeout_sec and (time.time() - start) > timeout_sec:
                    break

                line = line.rstrip()
                severity = self._classify_line(line)

                if not self._should_include(severity):
                    continue

                if dedup:
                    key = self._dedup_key(line)
                    if key in self._seen:
                        continue
                    self._seen.add(key)

                self.stats[severity] += 1
                self.logs.append({"line": line, "severity": severity})

            proc.terminate()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    def format_output(self, verbose=False, as_json=False):
        """Format captured logs."""
        if as_json:
            return json.dumps({
                "stats": self.stats,
                "total": len(self.logs),
                "logs": self.logs if verbose else self.logs[-50:],
            }, indent=2)

        lines = []
        total = sum(self.stats.values())
        lines.append(f"Captured {total} log entries")
        lines.append(f"  Errors: {self.stats['error']} | Warnings: {self.stats['warning']} | Info: {self.stats['info']}")

        if verbose:
            lines.append("")
            for entry in self.logs[-100:]:
                lines.append(entry["line"])
        else:
            # Show errors and warnings
            important = [e for e in self.logs if e["severity"] in ("error", "fatal", "warning")]
            if important:
                lines.append("")
                lines.append("Important entries:")
                for entry in important[-20:]:
                    lines.append(f"  [{entry['severity'].upper()}] {entry['line'][:200]}")

        return "\n".join(lines)

    def save_logs(self, output_path):
        """Save logs to file."""
        with open(output_path, "w") as f:
            for entry in self.logs:
                f.write(entry["line"] + "\n")

        summary_path = output_path.replace(".log", "-summary.json")
        with open(summary_path, "w") as f:
            json.dump({"stats": self.stats, "total": len(self.logs)}, f, indent=2)

        return output_path, summary_path


def main():
    parser = argparse.ArgumentParser(description="Monitor Android device logs")
    parser.add_argument("--app", help="Filter by app package name")
    parser.add_argument("--severity", default="info", choices=["verbose", "debug", "info", "warning", "error", "fatal"])
    parser.add_argument("--follow", action="store_true", help="Follow mode (stream)")
    parser.add_argument("--duration", default="30s", help="Capture duration (e.g., 30s, 5m)")
    parser.add_argument("--last", action="store_true", help="Clear and capture fresh logs")
    parser.add_argument("--output", help="Save logs to file")
    parser.add_argument("--verbose", action="store_true", help="Show all log lines")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    monitor = LogMonitor(serial=serial, app=args.app, severity=args.severity)
    monitor.capture(duration=args.duration, follow=args.follow, last=args.last)

    if args.output:
        log_path, summary_path = monitor.save_logs(args.output)
        print(f"Logs saved to: {log_path}")
        print(f"Summary saved to: {summary_path}")
    else:
        print(monitor.format_output(verbose=args.verbose, as_json=args.json))


if __name__ == "__main__":
    main()
