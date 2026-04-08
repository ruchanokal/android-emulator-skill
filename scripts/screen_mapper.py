#!/usr/bin/env python3
"""Analyze current screen and list interactive elements on Android."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial
from common.uiautomator_utils import get_ui_hierarchy, flatten_tree, get_short_class, count_elements


INTERACTIVE_TYPES = {
    "Button", "ImageButton", "FloatingActionButton",
    "EditText", "AutoCompleteTextView", "MultiAutoCompleteTextView",
    "CheckBox", "RadioButton", "Switch", "ToggleButton",
    "Spinner", "SeekBar", "RatingBar",
    "ImageView",  # Often clickable
    "TextView",   # Often clickable
    "ComposeView",
    "MaterialButton",
}


class ScreenMapper:
    def __init__(self, serial=None):
        self.serial = serial
        self.root = get_ui_hierarchy(serial=serial)
        self.elements = flatten_tree(self.root)
        self.total_count = count_elements(self.root)

    def get_interactive_elements(self):
        """Get all interactive (clickable/focusable) elements."""
        interactive = []
        for elem in self.elements:
            if elem["clickable"] or elem["checkable"] or elem["focusable"]:
                short_class = get_short_class(elem["class"])
                has_label = elem["text"] or elem["content_desc"]
                # For Compose UIs: clickable Views with child text are buttons
                # Skip only truly empty containers (no text, no desc, no clickable children)
                if short_class in ("FrameLayout", "LinearLayout", "RelativeLayout", "ConstraintLayout"):
                    if not has_label:
                        continue
                # For View (common in Compose), include if clickable — even without direct text
                # because Compose wraps text in child nodes
                if short_class == "View" and not has_label and not elem["clickable"]:
                    continue
                interactive.append(elem)
        return interactive

    def _find_child_text(self, elem):
        """Find text in child elements (for Compose clickable Views)."""
        for other in self.elements:
            if (other["depth"] > elem["depth"] and
                other["bounds"]["x1"] >= elem["bounds"]["x1"] and
                other["bounds"]["y1"] >= elem["bounds"]["y1"] and
                other["bounds"]["x2"] <= elem["bounds"]["x2"] and
                other["bounds"]["y2"] <= elem["bounds"]["y2"]):
                if other["text"]:
                    return other["text"]
                if other["content_desc"]:
                    return other["content_desc"]
        return None

    def get_buttons(self):
        """Get button elements."""
        buttons = []
        for elem in self.elements:
            short_class = get_short_class(elem["class"])
            has_direct_label = elem["text"] or elem["content_desc"]

            is_button = False
            label = None

            if "Button" in short_class:
                is_button = True
                label = elem["text"] or elem["content_desc"]
            elif elem["clickable"] and has_direct_label:
                is_button = True
                label = elem["text"] or elem["content_desc"]
            elif elem["clickable"] and short_class == "View":
                # Compose pattern: clickable View with child TextView
                child_text = self._find_child_text(elem)
                if child_text:
                    is_button = True
                    label = child_text

            if is_button and label and label != "(unnamed)":
                if label not in buttons:  # Avoid duplicates
                    buttons.append(label)
        return buttons

    def get_text_fields(self):
        """Get text input fields."""
        fields = []
        for elem in self.elements:
            short_class = get_short_class(elem["class"])
            if "EditText" in short_class or "AutoComplete" in short_class:
                fields.append({
                    "hint": elem["content_desc"] or elem["text"] or "(empty)",
                    "text": elem["text"],
                    "focused": elem["focused"],
                    "resource_id": elem["resource_id"],
                })
        return fields

    def get_screen_name(self):
        """Try to determine the current screen/activity."""
        for elem in self.elements:
            rid = elem.get("resource_id", "")
            if "toolbar" in rid.lower() or "action_bar" in rid.lower():
                if elem["text"]:
                    return elem["text"]
                # Check children for title
                for child in self.elements:
                    if child["depth"] > elem["depth"] and child["text"]:
                        return child["text"]
        # Fallback: check for any large text at top of screen
        for elem in self.elements:
            if elem["text"] and elem["bounds"]["y1"] < 200:
                short_class = get_short_class(elem["class"])
                if "TextView" in short_class:
                    return elem["text"]
        return "Unknown Screen"

    def format_output(self, verbose=False, as_json=False):
        interactive = self.get_interactive_elements()
        buttons = self.get_buttons()
        text_fields = self.get_text_fields()
        screen_name = self.get_screen_name()

        if as_json:
            return json.dumps({
                "screen": screen_name,
                "total_elements": self.total_count,
                "interactive_count": len(interactive),
                "buttons": buttons,
                "text_fields": text_fields,
                "elements": self.elements if verbose else [],
            }, indent=2, ensure_ascii=False)

        lines = []
        btn_preview = ", ".join(f'"{b}"' for b in buttons[:5])
        if len(buttons) > 5:
            btn_preview += f" +{len(buttons) - 5} more"

        lines.append(f"Screen: {screen_name} ({self.total_count} elements, {len(interactive)} interactive)")
        if buttons:
            lines.append(f"Buttons: {btn_preview}")
        filled = sum(1 for f in text_fields if f["text"])
        if text_fields:
            lines.append(f"TextFields: {len(text_fields)} ({filled} filled)")
        lines.append(f"Focusable: {len([e for e in interactive if e['focusable']])} elements")

        if verbose:
            lines.append("")
            lines.append("Elements by type:")
            type_groups = {}
            for elem in interactive:
                short = get_short_class(elem["class"])
                if short not in type_groups:
                    type_groups[short] = []
                label = elem["text"] or elem["content_desc"] or "(unnamed)"
                type_groups[short].append(label)

            for etype, labels in type_groups.items():
                lines.append(f"  {etype}: {len(labels)}")
                for label in labels[:3]:
                    lines.append(f"    - {label}")
                if len(labels) > 3:
                    lines.append(f"    ... +{len(labels) - 3} more")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze current Android screen elements")
    parser.add_argument("--verbose", action="store_true", help="Show detailed element breakdown")
    parser.add_argument("--hints", action="store_true", help="Show navigation hints")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    mapper = ScreenMapper(serial=serial)
    print(mapper.format_output(verbose=args.verbose or args.hints, as_json=args.json))


if __name__ == "__main__":
    main()
