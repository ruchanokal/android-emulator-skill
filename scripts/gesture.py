#!/usr/bin/env python3
"""Perform swipes, scrolls, and gestures on Android."""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command, get_screen_size


class GestureController:
    def __init__(self, serial=None):
        self.serial = serial
        self.screen_width, self.screen_height = get_screen_size(serial=serial)

    def swipe(self, direction, duration=300):
        """Perform a directional swipe."""
        cx = self.screen_width // 2
        cy = self.screen_height // 2
        dist_x = int(self.screen_width * 0.35)
        dist_y = int(self.screen_height * 0.35)

        coords = {
            "up": (cx, cy + dist_y, cx, cy - dist_y),
            "down": (cx, cy - dist_y, cx, cy + dist_y),
            "left": (cx + dist_x, cy, cx - dist_x, cy),
            "right": (cx - dist_x, cy, cx + dist_x, cy),
        }

        if direction not in coords:
            return False, f"Invalid direction: {direction}"

        x1, y1, x2, y2 = coords[direction]
        return self.swipe_between(x1, y1, x2, y2, duration)

    def swipe_between(self, x1, y1, x2, y2, duration=300):
        """Swipe between two points."""
        cmd = build_adb_command(
            ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)],
            serial=self.serial
        )
        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, f"Swiped from ({x1},{y1}) to ({x2},{y2})"
        return False, "Swipe failed"

    def scroll(self, direction="down", amount=3):
        """Scroll by performing multiple small swipes."""
        cx = self.screen_width // 2
        dist = int(self.screen_height * 0.15)

        for i in range(amount):
            if direction == "down":
                self.swipe_between(cx, cy := self.screen_height // 2 + dist, cx, cy - dist * 2, 200)
            else:
                self.swipe_between(cx, cy := self.screen_height // 2 - dist, cx, cy + dist * 2, 200)
            time.sleep(0.2)

        return True, f"Scrolled {direction} {amount} times"

    def long_press(self, x, y, duration=1000):
        """Long press at coordinates."""
        cmd = build_adb_command(
            ["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)],
            serial=self.serial
        )
        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, f"Long pressed at ({x}, {y}) for {duration}ms"
        return False, "Long press failed"

    def pinch(self, direction="in"):
        """Simulate pinch gesture (limited on Android without input inject)."""
        # Android's input command doesn't natively support multi-touch
        # This is a best-effort simulation
        cx = self.screen_width // 2
        cy = self.screen_height // 2
        offset = 200

        if direction == "out":
            # Pinch out (zoom in) - two fingers moving apart
            self.swipe_between(cx, cy, cx - offset, cy - offset, 500)
            return True, "Pinch out gesture simulated"
        else:
            # Pinch in (zoom out)
            self.swipe_between(cx - offset, cy - offset, cx, cy, 500)
            return True, "Pinch in gesture simulated"

    def pull_to_refresh(self):
        """Pull to refresh gesture."""
        cx = self.screen_width // 2
        start_y = int(self.screen_height * 0.2)
        end_y = int(self.screen_height * 0.7)
        return self.swipe_between(cx, start_y, cx, end_y, 500)

    def tap(self, x, y):
        """Tap at coordinates."""
        cmd = build_adb_command(
            ["shell", "input", "tap", str(x), str(y)],
            serial=self.serial
        )
        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, f"Tapped at ({x}, {y})"
        return False, "Tap failed"

    def double_tap(self, x, y):
        """Double tap at coordinates."""
        self.tap(x, y)
        time.sleep(0.1)
        return self.tap(x, y)


def main():
    parser = argparse.ArgumentParser(description="Perform gestures on Android device")
    parser.add_argument("--swipe", choices=["up", "down", "left", "right"], help="Directional swipe")
    parser.add_argument("--swipe-from", help="Swipe start x,y (e.g. '100,200')")
    parser.add_argument("--swipe-to", help="Swipe end x,y (e.g. '100,500')")
    parser.add_argument("--scroll", choices=["up", "down"], help="Scroll direction")
    parser.add_argument("--scroll-amount", type=int, default=3, help="Number of scroll steps")
    parser.add_argument("--long-press", help="Long press at x,y (e.g. '100,200')")
    parser.add_argument("--duration", type=int, default=300, help="Duration in ms")
    parser.add_argument("--pinch", choices=["in", "out"], help="Pinch gesture")
    parser.add_argument("--refresh", action="store_true", help="Pull to refresh")
    parser.add_argument("--tap", help="Tap at x,y (e.g. '100,200')")
    parser.add_argument("--double-tap", help="Double tap at x,y")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    gc = GestureController(serial=serial)

    if args.swipe:
        success, msg = gc.swipe(args.swipe, duration=args.duration)
    elif args.swipe_from and args.swipe_to:
        x1, y1 = map(int, args.swipe_from.split(","))
        x2, y2 = map(int, args.swipe_to.split(","))
        success, msg = gc.swipe_between(x1, y1, x2, y2, args.duration)
    elif args.scroll:
        success, msg = gc.scroll(args.scroll, args.scroll_amount)
    elif args.long_press:
        x, y = map(int, args.long_press.split(","))
        success, msg = gc.long_press(x, y, args.duration)
    elif args.pinch:
        success, msg = gc.pinch(args.pinch)
    elif args.refresh:
        success, msg = gc.pull_to_refresh()
    elif args.tap:
        x, y = map(int, args.tap.split(","))
        success, msg = gc.tap(x, y)
    elif args.double_tap:
        x, y = map(int, args.double_tap.split(","))
        success, msg = gc.double_tap(x, y)
    else:
        parser.print_help()
        sys.exit(1)

    if args.json:
        print(json.dumps({"success": success, "message": msg}))
    else:
        print(msg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
