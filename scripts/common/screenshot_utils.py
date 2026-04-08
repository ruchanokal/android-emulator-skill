#!/usr/bin/env python3
"""Screenshot capture utilities for Android."""

import subprocess
import sys
import os
import time
import base64
from .device_utils import build_adb_command, run_command

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

SIZE_PRESETS = {
    "full": 1.0,
    "half": 0.5,
    "quarter": 0.25,
    "thumb": 0.1,
}


def capture_screenshot(serial=None, output_path=None, size="half", inline=False):
    """Capture a screenshot from the device.

    Args:
        serial: Device serial number
        output_path: Path to save screenshot (file mode)
        size: Size preset (full, half, quarter, thumb)
        inline: If True, return base64 data instead of file path

    Returns:
        dict with screenshot info
    """
    tmp_path = "/tmp/android_screenshot.png"

    # Capture screenshot
    cmd = build_adb_command(["exec-out", "screencap", "-p"], serial=serial)
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode != 0:
            return {"error": "Failed to capture screenshot"}
        with open(tmp_path, "wb") as f:
            f.write(result.stdout)
    except Exception as e:
        return {"error": str(e)}

    # Resize if PIL available
    scale = SIZE_PRESETS.get(size, 0.5)
    if HAS_PIL and scale < 1.0:
        try:
            img = Image.open(tmp_path)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)
            img.save(tmp_path)
        except Exception:
            pass  # Use original if resize fails

    if inline:
        with open(tmp_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        file_size = os.path.getsize(tmp_path)
        return {
            "mode": "inline",
            "base64_data": data,
            "mime_type": "image/png",
            "size_bytes": file_size,
        }
    else:
        final_path = output_path or tmp_path
        if output_path and output_path != tmp_path:
            import shutil
            shutil.move(tmp_path, final_path)
        file_size = os.path.getsize(final_path)
        return {
            "mode": "file",
            "file_path": final_path,
            "size_bytes": file_size,
        }
