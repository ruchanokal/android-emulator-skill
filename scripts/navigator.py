#!/usr/bin/env python3
"""Find and interact with Android UI elements semantically."""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command
from common.uiautomator_utils import get_ui_hierarchy, flatten_tree, get_short_class


class Navigator:
    def __init__(self, serial=None):
        self.serial = serial
        self._tree_cache = None

    def _get_elements(self):
        if self._tree_cache is None:
            root = get_ui_hierarchy(serial=self.serial)
            self._tree_cache = flatten_tree(root)
        return self._tree_cache

    def _invalidate_cache(self):
        self._tree_cache = None

    def _find_clickable_parent(self, elem):
        """Find the nearest clickable parent for a text element (Compose pattern)."""
        elements = self._get_elements()
        for other in elements:
            if (other["clickable"] and
                other["bounds"]["x1"] <= elem["bounds"]["x1"] and
                other["bounds"]["y1"] <= elem["bounds"]["y1"] and
                other["bounds"]["x2"] >= elem["bounds"]["x2"] and
                other["bounds"]["y2"] >= elem["bounds"]["y2"] and
                other is not elem):
                return other
        return None

    def find_by_text(self, text, exact=False, index=0):
        """Find elements by text content (text or content-desc).

        For Compose UIs: if a text match is found on a non-clickable element,
        looks for a clickable parent and returns that instead (for tapping).
        """
        elements = self._get_elements()
        matches = []
        text_lower = text.lower()

        for elem in elements:
            elem_text = (elem["text"] or "").lower()
            elem_desc = (elem["content_desc"] or "").lower()

            matched = False
            if exact:
                matched = (elem_text == text_lower or elem_desc == text_lower)
            else:
                matched = (text_lower in elem_text or text_lower in elem_desc)

            if matched:
                # If elem itself is clickable, use it directly
                if elem["clickable"] or elem["focusable"]:
                    matches.append(elem)
                else:
                    # Compose pattern: text is in child, clickable is on parent
                    parent = self._find_clickable_parent(elem)
                    if parent and parent not in matches:
                        # Copy text info to parent for display purposes
                        if not parent["text"] and not parent["content_desc"]:
                            parent = dict(parent)
                            parent["text"] = elem["text"]
                            parent["content_desc"] = elem["content_desc"]
                        matches.append(parent)
                    else:
                        # No clickable parent, return the text element itself
                        matches.append(elem)

        if not matches:
            return None
        if index < len(matches):
            return matches[index]
        return matches[0]

    def find_by_type(self, class_name, index=0):
        """Find elements by class type."""
        elements = self._get_elements()
        matches = []
        class_lower = class_name.lower()

        for elem in elements:
            short = get_short_class(elem["class"]).lower()
            full = elem["class"].lower()
            if class_lower in short or class_lower in full:
                matches.append(elem)

        if not matches:
            return None
        if index < len(matches):
            return matches[index]
        return matches[0]

    def find_by_id(self, resource_id, index=0):
        """Find elements by resource ID."""
        elements = self._get_elements()
        matches = []

        for elem in elements:
            rid = elem.get("resource_id", "")
            if resource_id in rid:
                matches.append(elem)

        if not matches:
            return None
        if index < len(matches):
            return matches[index]
        return matches[0]

    def tap(self, elem):
        """Tap on an element."""
        cx, cy = elem["center"]
        cmd = build_adb_command(["shell", "input", "tap", str(cx), str(cy)], serial=self.serial)
        result = run_command(cmd)
        self._invalidate_cache()
        return result and result.returncode == 0

    def enter_text(self, elem, text):
        """Tap element and enter text."""
        # First tap to focus
        self.tap(elem)
        time.sleep(0.5)

        # Clear existing text
        cmd = build_adb_command(
            ["shell", "input", "keyevent", "--longpress", "123"],  # KEYCODE_MOVE_END
            serial=self.serial
        )
        run_command(cmd)
        # Select all and delete
        run_command(build_adb_command(["shell", "input", "keyevent", "29", "--longpress"], serial=self.serial))

        # Type text - escape special characters for shell
        escaped = text.replace("'", "'\\''").replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>").replace("|", "\\|")
        cmd = build_adb_command(["shell", "input", "text", escaped], serial=self.serial)
        result = run_command(cmd)
        self._invalidate_cache()
        return result and result.returncode == 0

    def find_and_tap(self, text=None, class_name=None, resource_id=None, index=0):
        """Find an element and tap it."""
        elem = None
        search_desc = ""

        if text:
            elem = self.find_by_text(text, index=index)
            search_desc = f'text "{text}"'
        elif class_name:
            elem = self.find_by_type(class_name, index=index)
            search_desc = f'type "{class_name}"'
        elif resource_id:
            elem = self.find_by_id(resource_id, index=index)
            search_desc = f'id "{resource_id}"'

        if not elem:
            return False, f"Not found: {search_desc}"

        short_class = get_short_class(elem["class"])
        label = elem["text"] or elem["content_desc"] or "(unnamed)"
        cx, cy = elem["center"]

        success = self.tap(elem)
        if success:
            return True, f'Tapped: {short_class} "{label}" at ({cx}, {cy})'
        return False, f"Failed to tap: {short_class} \"{label}\""

    def find_and_enter_text(self, text, find_text=None, find_type=None, find_id=None, index=0):
        """Find an element and enter text."""
        elem = None
        if find_text:
            elem = self.find_by_text(find_text, index=index)
        elif find_type:
            elem = self.find_by_type(find_type, index=index)
        elif find_id:
            elem = self.find_by_id(find_id, index=index)

        if not elem:
            return False, "Element not found for text entry"

        short_class = get_short_class(elem["class"])
        label = elem["text"] or elem["content_desc"] or "(unnamed)"

        success = self.enter_text(elem, text)
        if success:
            return True, f'Entered "{text}" in {short_class} "{label}"'
        return False, f"Failed to enter text in {short_class} \"{label}\""


def main():
    parser = argparse.ArgumentParser(description="Navigate and interact with Android UI elements")
    parser.add_argument("--find-text", help="Find element by text content")
    parser.add_argument("--find-type", help="Find element by class type")
    parser.add_argument("--find-id", help="Find element by resource ID")
    parser.add_argument("--tap", action="store_true", help="Tap the found element")
    parser.add_argument("--enter-text", help="Enter text into the found element")
    parser.add_argument("--index", type=int, default=0, help="Index if multiple matches (default: 0)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    nav = Navigator(serial=serial)

    if args.enter_text:
        success, msg = nav.find_and_enter_text(
            args.enter_text,
            find_text=args.find_text,
            find_type=args.find_type,
            find_id=args.find_id,
            index=args.index,
        )
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
        sys.exit(0 if success else 1)

    elif args.tap:
        success, msg = nav.find_and_tap(
            text=args.find_text,
            class_name=args.find_type,
            resource_id=args.find_id,
            index=args.index,
        )
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)
        sys.exit(0 if success else 1)

    else:
        # Just find and show element info
        elem = None
        if args.find_text:
            elem = nav.find_by_text(args.find_text, index=args.index)
        elif args.find_type:
            elem = nav.find_by_type(args.find_type, index=args.index)
        elif args.find_id:
            elem = nav.find_by_id(args.find_id, index=args.index)

        if elem:
            if args.json:
                print(json.dumps(elem, ensure_ascii=False, indent=2))
            else:
                short = get_short_class(elem["class"])
                label = elem["text"] or elem["content_desc"] or "(unnamed)"
                cx, cy = elem["center"]
                print(f'Found: {short} "{label}" at ({cx}, {cy})')
        else:
            print("Element not found", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
