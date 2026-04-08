#!/usr/bin/env python3
"""UI Automator utilities for parsing Android accessibility tree."""

import subprocess
import sys
import xml.etree.ElementTree as ET
from .device_utils import build_adb_command, run_command


def get_ui_hierarchy(serial=None):
    """Dump and parse the UI hierarchy via uiautomator."""
    dump_cmd = build_adb_command(["shell", "uiautomator", "dump", "/dev/tty"], serial=serial)
    result = run_command(dump_cmd, timeout=15)

    if not result or result.returncode != 0:
        # Fallback: dump to file and pull
        run_command(build_adb_command(
            ["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], serial=serial
        ))
        result = run_command(build_adb_command(
            ["shell", "cat", "/sdcard/window_dump.xml"], serial=serial
        ))
        if not result or result.returncode != 0:
            print("Failed to dump UI hierarchy", file=sys.stderr)
            sys.exit(1)

    xml_content = result.stdout.strip()
    # Remove any non-XML prefix (uiautomator sometimes outputs extra text)
    xml_start = xml_content.find("<?xml")
    if xml_start == -1:
        xml_start = xml_content.find("<hierarchy")
    if xml_start > 0:
        xml_content = xml_content[xml_start:]

    try:
        root = ET.fromstring(xml_content)
        return root
    except ET.ParseError as e:
        print(f"Failed to parse UI hierarchy: {e}", file=sys.stderr)
        sys.exit(1)


def flatten_tree(element, depth=0):
    """Flatten XML tree into list of element dicts."""
    elements = []
    elem_dict = parse_element(element, depth)
    if elem_dict:
        elements.append(elem_dict)
    for child in element:
        elements.extend(flatten_tree(child, depth + 1))
    return elements


def parse_element(element, depth=0):
    """Parse an XML element into a dict."""
    attribs = element.attrib
    if not attribs:
        return None

    bounds = attribs.get("bounds", "")
    x1, y1, x2, y2 = 0, 0, 0, 0
    if bounds:
        import re
        match = re.findall(r"\d+", bounds)
        if len(match) == 4:
            x1, y1, x2, y2 = int(match[0]), int(match[1]), int(match[2]), int(match[3])

    return {
        "class": attribs.get("class", ""),
        "text": attribs.get("text", ""),
        "content_desc": attribs.get("content-desc", ""),
        "resource_id": attribs.get("resource-id", ""),
        "package": attribs.get("package", ""),
        "checkable": attribs.get("checkable", "false") == "true",
        "checked": attribs.get("checked", "false") == "true",
        "clickable": attribs.get("clickable", "false") == "true",
        "enabled": attribs.get("enabled", "true") == "true",
        "focusable": attribs.get("focusable", "false") == "true",
        "focused": attribs.get("focused", "false") == "true",
        "scrollable": attribs.get("scrollable", "false") == "true",
        "long_clickable": attribs.get("long-clickable", "false") == "true",
        "selected": attribs.get("selected", "false") == "true",
        "bounds": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "center": ((x1 + x2) // 2, (y1 + y2) // 2),
        "depth": depth,
    }


def get_short_class(class_name):
    """Get short class name from full Android class path."""
    if "." in class_name:
        return class_name.split(".")[-1]
    return class_name


def count_elements(element):
    """Count total elements in hierarchy."""
    count = 1
    for child in element:
        count += count_elements(child)
    return count
