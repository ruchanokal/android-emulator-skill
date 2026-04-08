#!/usr/bin/env python3
"""Check accessibility compliance on current Android screen."""

import argparse
import json
import sys
import os
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial
from common.uiautomator_utils import get_ui_hierarchy, flatten_tree, get_short_class


@dataclass
class Issue:
    severity: str  # critical, warning, info
    rule: str
    element_type: str
    issue: str
    fix: str


CLICKABLE_TYPES = {"Button", "ImageButton", "FloatingActionButton", "ImageView", "TextView"}


class AccessibilityAuditor:
    def __init__(self, serial=None):
        self.serial = serial
        self.root = get_ui_hierarchy(serial=serial)
        self.elements = flatten_tree(self.root)
        self.issues = []

    def audit(self):
        """Run all audit rules."""
        for elem in self.elements:
            short_class = get_short_class(elem["class"])
            self._check_critical(elem, short_class)
            self._check_warnings(elem, short_class)
            self._check_info(elem, short_class)
        return self.issues

    def _check_critical(self, elem, short_class):
        # Missing content description on clickable elements
        if elem["clickable"] and not elem["text"] and not elem["content_desc"]:
            if short_class in CLICKABLE_TYPES or "Image" in short_class:
                self.issues.append(Issue(
                    severity="critical",
                    rule="missing_label",
                    element_type=short_class,
                    issue=f"Clickable {short_class} has no text or content description",
                    fix="Add android:contentDescription or text",
                ))

        # ImageView without content description
        if "ImageView" in short_class and not elem["content_desc"]:
            self.issues.append(Issue(
                severity="critical",
                rule="image_no_description",
                element_type=short_class,
                issue=f"ImageView without content description at {elem['center']}",
                fix='Add android:contentDescription or android:importantForAccessibility="no"',
            ))

    def _check_warnings(self, elem, short_class):
        # Small touch target (< 48dp ≈ 48*density pixels, using 96px as minimum)
        bounds = elem["bounds"]
        width = bounds["x2"] - bounds["x1"]
        height = bounds["y2"] - bounds["y1"]
        if elem["clickable"] and (width < 96 or height < 96) and width > 0:
            self.issues.append(Issue(
                severity="warning",
                rule="small_touch_target",
                element_type=short_class,
                issue=f"Touch target too small: {width}x{height}px (min 48dp)",
                fix="Increase size or add touchDelegate/padding",
            ))

        # EditText without hint
        if "EditText" in short_class and not elem["text"] and not elem["content_desc"]:
            self.issues.append(Issue(
                severity="warning",
                rule="edittext_no_hint",
                element_type=short_class,
                issue="EditText without hint or label",
                fix="Add android:hint or labelFor relationship",
            ))

    def _check_info(self, elem, short_class):
        # Missing resource ID
        if elem["clickable"] and not elem.get("resource_id"):
            self.issues.append(Issue(
                severity="info",
                rule="no_resource_id",
                element_type=short_class,
                issue=f"Clickable {short_class} has no resource-id",
                fix="Add android:id for testing and accessibility",
            ))

        # Deep nesting
        if elem["depth"] > 8:
            self.issues.append(Issue(
                severity="info",
                rule="deep_nesting",
                element_type=short_class,
                issue=f"Element nested {elem['depth']} levels deep",
                fix="Flatten view hierarchy for performance",
            ))

    def format_output(self, verbose=False, as_json=False):
        critical = [i for i in self.issues if i.severity == "critical"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        info = [i for i in self.issues if i.severity == "info"]

        if as_json:
            return json.dumps({
                "summary": {
                    "critical": len(critical),
                    "warnings": len(warnings),
                    "info": len(info),
                    "total": len(self.issues),
                },
                "issues": [asdict(i) for i in self.issues],
            }, indent=2, ensure_ascii=False)

        lines = []
        lines.append(f"Accessibility: {len(critical)} critical, {len(warnings)} warnings, {len(info)} info")

        if critical:
            # Group by rule
            rules = {}
            for issue in critical:
                if issue.rule not in rules:
                    rules[issue.rule] = 0
                rules[issue.rule] += 1
            top = sorted(rules.items(), key=lambda x: -x[1])[:3]
            lines.append(f"Top issues: {', '.join(f'{r} ({c})' for r, c in top)}")

        if verbose:
            lines.append("")
            for issue in self.issues[:30]:
                lines.append(f"  [{issue.severity.upper()}] {issue.issue}")
                lines.append(f"    Fix: {issue.fix}")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Android accessibility audit")
    parser.add_argument("--verbose", action="store_true", help="Show all issues")
    parser.add_argument("--output", help="Save JSON report to file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    auditor = AccessibilityAuditor(serial=serial)
    auditor.audit()

    if args.output:
        with open(args.output, "w") as f:
            f.write(auditor.format_output(as_json=True))
        print(f"Report saved to: {args.output}")
    else:
        print(auditor.format_output(verbose=args.verbose, as_json=args.json))

    # Exit with error if critical issues found
    critical_count = sum(1 for i in auditor.issues if i.severity == "critical")
    sys.exit(1 if critical_count > 0 else 0)


if __name__ == "__main__":
    main()
