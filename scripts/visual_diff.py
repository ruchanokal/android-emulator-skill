#!/usr/bin/env python3
"""Compare two screenshots for visual changes on Android."""

import argparse
import json
import sys
import os

try:
    from PIL import Image, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def compare_images(path1, path2, threshold=0.02):
    """Compare two images and return similarity info."""
    if not HAS_PIL:
        return {"error": "PIL/Pillow required. Install with: pip3 install Pillow"}

    img1 = Image.open(path1).convert("RGB")
    img2 = Image.open(path2).convert("RGB")

    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    diff = ImageChops.difference(img1, img2)
    pixels = list(diff.getdata())
    total = len(pixels) * 3  # R, G, B channels
    changed = sum(1 for p in pixels for c in p if c > 10)
    ratio = changed / total if total > 0 else 0

    passed = ratio <= threshold
    return {
        "passed": passed,
        "diff_ratio": round(ratio, 4),
        "threshold": threshold,
        "changed_pixels_pct": round(ratio * 100, 2),
        "image1_size": img1.size,
        "image2_size": img2.size,
    }


def generate_diff_image(path1, path2, output_path):
    """Generate a visual diff image."""
    if not HAS_PIL:
        return None

    img1 = Image.open(path1).convert("RGB")
    img2 = Image.open(path2).convert("RGB")

    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    diff = ImageChops.difference(img1, img2)
    # Amplify differences
    diff = diff.point(lambda x: min(255, x * 5))
    diff.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Compare screenshots for visual changes")
    parser.add_argument("image1", help="First screenshot path")
    parser.add_argument("image2", help="Second screenshot path")
    parser.add_argument("--threshold", type=float, default=0.02, help="Max diff ratio to pass (default: 0.02)")
    parser.add_argument("--output", help="Save diff image to path")
    parser.add_argument("--details", action="store_true", help="Show detailed comparison")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    result = compare_images(args.image1, args.image2, threshold=args.threshold)

    if "error" in result:
        print(result["error"], file=sys.stderr)
        sys.exit(1)

    if args.output:
        diff_path = generate_diff_image(args.image1, args.image2, args.output)
        if diff_path:
            result["diff_image"] = diff_path

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"Visual diff: {status} ({result['changed_pixels_pct']}% changed, threshold: {result['threshold'] * 100}%)")
        if args.output and result.get("diff_image"):
            print(f"Diff image saved: {result['diff_image']}")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
