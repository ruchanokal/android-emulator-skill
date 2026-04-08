#!/usr/bin/env python3
"""Text input and hardware button control for Android."""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


# Android KeyEvent codes
SPECIAL_KEYS = {
    "enter": 66, "return": 66,
    "delete": 67, "backspace": 67,
    "del": 112,  # Forward delete
    "tab": 61,
    "space": 62,
    "escape": 111, "esc": 111,
    "up": 19, "down": 20, "left": 21, "right": 22,
    "home-key": 3,
    "back": 4,
    "menu": 82,
    "search": 84,
    "page-up": 92, "page-down": 93,
    "move-home": 122, "move-end": 123,
    "select-all": 29,  # Used with META_CTRL
}

HARDWARE_BUTTONS = {
    "home": 3,
    "back": 4,
    "power": 26,
    "volume-up": 24,
    "volume-down": 25,
    "volume-mute": 164,
    "camera": 27,
    "recent-apps": 187,
    "screenshot": 120,
}


class KeyboardController:
    def __init__(self, serial=None):
        self.serial = serial

    def type_text(self, text, slow=False):
        """Type text into the focused field."""
        if slow:
            for char in text:
                escaped = char.replace(" ", "%s").replace("'", "'\\''")
                escaped = escaped.replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
                cmd = build_adb_command(["shell", "input", "text", escaped], serial=self.serial)
                run_command(cmd)
                time.sleep(0.1)
        else:
            escaped = text.replace(" ", "%s").replace("'", "'\\''")
            escaped = escaped.replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
            escaped = escaped.replace("(", "\\(").replace(")", "\\)")
            cmd = build_adb_command(["shell", "input", "text", escaped], serial=self.serial)
            run_command(cmd)
        return True, f'Typed: "{text}"'

    def press_key(self, key_name, count=1):
        """Press a special key by name."""
        key_lower = key_name.lower()

        if key_lower in SPECIAL_KEYS:
            code = SPECIAL_KEYS[key_lower]
        elif key_lower in HARDWARE_BUTTONS:
            code = HARDWARE_BUTTONS[key_lower]
        else:
            try:
                code = int(key_name)
            except ValueError:
                return False, f"Unknown key: {key_name}"

        for _ in range(count):
            cmd = build_adb_command(
                ["shell", "input", "keyevent", str(code)],
                serial=self.serial
            )
            result = run_command(cmd)
            if not result or result.returncode != 0:
                return False, f"Failed to press key: {key_name}"
            if count > 1:
                time.sleep(0.05)

        return True, f"Pressed: {key_name}" + (f" x{count}" if count > 1 else "")

    def press_button(self, button_name):
        """Press a hardware button."""
        button_lower = button_name.lower()
        if button_lower not in HARDWARE_BUTTONS:
            return False, f"Unknown button: {button_name}. Available: {', '.join(HARDWARE_BUTTONS.keys())}"

        code = HARDWARE_BUTTONS[button_lower]
        cmd = build_adb_command(
            ["shell", "input", "keyevent", str(code)],
            serial=self.serial
        )
        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, f"Pressed button: {button_name}"
        return False, f"Failed to press button: {button_name}"

    def clear_text(self):
        """Clear text in focused field (Ctrl+A then Delete)."""
        # Move to end
        run_command(build_adb_command(
            ["shell", "input", "keyevent", "123"],  # MOVE_END
            serial=self.serial
        ))
        # Select all: Ctrl+A
        run_command(build_adb_command(
            ["shell", "input", "keyevent", "--meta", "28672", "29"],  # META_CTRL_ON + A
            serial=self.serial
        ))
        time.sleep(0.1)
        # Delete
        run_command(build_adb_command(
            ["shell", "input", "keyevent", "67"],  # DEL
            serial=self.serial
        ))
        return True, "Cleared text"

    def dismiss_keyboard(self):
        """Dismiss the on-screen keyboard."""
        cmd = build_adb_command(
            ["shell", "input", "keyevent", "111"],  # ESCAPE
            serial=self.serial
        )
        result = run_command(cmd)
        if result and result.returncode == 0:
            return True, "Dismissed keyboard"
        return False, "Failed to dismiss keyboard"

    def press_back(self):
        """Press the Back button."""
        return self.press_key("back")


def main():
    parser = argparse.ArgumentParser(description="Android keyboard and button control")
    parser.add_argument("--type", dest="text", help="Text to type")
    parser.add_argument("--key", help="Special key to press (enter, delete, tab, etc.)")
    parser.add_argument("--button", help="Hardware button (home, back, power, volume-up, etc.)")
    parser.add_argument("--clear", action="store_true", help="Clear text in focused field")
    parser.add_argument("--dismiss", action="store_true", help="Dismiss keyboard")
    parser.add_argument("--back", action="store_true", help="Press Back button")
    parser.add_argument("--count", type=int, default=1, help="Number of key presses")
    parser.add_argument("--slow", action="store_true", help="Type slowly (character by character)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    kb = KeyboardController(serial=serial)

    if args.text:
        success, msg = kb.type_text(args.text, slow=args.slow)
    elif args.key:
        success, msg = kb.press_key(args.key, count=args.count)
    elif args.button:
        success, msg = kb.press_button(args.button)
    elif args.clear:
        success, msg = kb.clear_text()
    elif args.dismiss:
        success, msg = kb.dismiss_keyboard()
    elif args.back:
        success, msg = kb.press_back()
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
