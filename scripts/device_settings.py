#!/usr/bin/env python3
"""Change Android device settings — locale, dark mode, font size, display density."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.device_utils import resolve_serial, build_adb_command, run_command


COMMON_LOCALES = {
    "tr": "tr-TR", "en": "en-US", "de": "de-DE", "fr": "fr-FR",
    "es": "es-ES", "it": "it-IT", "pt": "pt-BR", "ar": "ar-SA",
    "ja": "ja-JP", "ko": "ko-KR", "zh": "zh-CN", "ru": "ru-RU",
    "nl": "nl-NL", "pl": "pl-PL", "sv": "sv-SE",
}


def set_locale(serial, locale):
    """Change device locale."""
    # Resolve short code
    if locale.lower() in COMMON_LOCALES:
        locale = COMMON_LOCALES[locale.lower()]

    # Set via persist prop and settings
    run_command(build_adb_command(
        ["shell", "setprop", "persist.sys.locale", locale], serial=serial
    ))
    run_command(build_adb_command(
        ["shell", "setprop", "persist.sys.language", locale.split("-")[0]], serial=serial
    ))
    run_command(build_adb_command(
        ["shell", "setprop", "persist.sys.country", locale.split("-")[-1] if "-" in locale else ""],
        serial=serial
    ))

    # Apply with settings command (Android 7+)
    result = run_command(build_adb_command(
        ["shell", "settings", "put", "system", "system_locales", locale], serial=serial
    ))

    return True, f"Locale set to {locale} (restart app to take effect)"


def set_dark_mode(serial, enabled):
    """Toggle dark mode (Android 10+)."""
    mode = "yes" if enabled else "no"
    result = run_command(build_adb_command(
        ["shell", "cmd", "uimode", "night", mode], serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"Dark mode {'enabled' if enabled else 'disabled'}"
    return False, "Failed to change dark mode (requires Android 10+)"


def set_font_scale(serial, scale):
    """Set font scale (1.0 = normal, 1.5 = large, 2.0 = extra large)."""
    result = run_command(build_adb_command(
        ["shell", "settings", "put", "system", "font_scale", str(scale)], serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"Font scale set to {scale}x"
    return False, "Failed to set font scale"


def set_display_density(serial, density):
    """Change display density (DPI)."""
    result = run_command(build_adb_command(
        ["shell", "wm", "density", str(density)], serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"Display density set to {density}dpi"
    return False, "Failed to set density"


def set_screen_rotation(serial, rotation):
    """Set screen rotation. 0=portrait, 1=landscape, 2=reverse portrait, 3=reverse landscape."""
    # Disable auto-rotation first
    run_command(build_adb_command(
        ["shell", "settings", "put", "system", "accelerometer_rotation", "0"], serial=serial
    ))
    result = run_command(build_adb_command(
        ["shell", "settings", "put", "system", "user_rotation", str(rotation)], serial=serial
    ))
    if result and result.returncode == 0:
        names = {0: "portrait", 1: "landscape", 2: "reverse portrait", 3: "reverse landscape"}
        return True, f"Rotation set to {names.get(rotation, rotation)}"
    return False, "Failed to set rotation"


def set_auto_rotation(serial, enabled):
    """Toggle auto-rotation."""
    value = "1" if enabled else "0"
    result = run_command(build_adb_command(
        ["shell", "settings", "put", "system", "accelerometer_rotation", value], serial=serial
    ))
    if result and result.returncode == 0:
        return True, f"Auto-rotation {'enabled' if enabled else 'disabled'}"
    return False, "Failed to change auto-rotation"


def set_animations(serial, enabled):
    """Enable/disable all animations (useful for faster testing)."""
    scale = "1.0" if enabled else "0.0"
    for setting in ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]:
        run_command(build_adb_command(
            ["shell", "settings", "put", "global", setting, scale], serial=serial
        ))
    return True, f"Animations {'enabled' if enabled else 'disabled'}"


def reset_all(serial):
    """Reset all settings to defaults."""
    results = []
    results.append(set_font_scale(serial, 1.0))
    results.append(set_dark_mode(serial, False))
    results.append(set_auto_rotation(serial, True))
    results.append(set_animations(serial, True))

    # Reset density
    run_command(build_adb_command(["shell", "wm", "density", "reset"], serial=serial))
    results.append((True, "Display density reset"))

    return True, "All settings reset to defaults"


def get_current_settings(serial):
    """Get current device settings."""
    info = {}

    result = run_command(build_adb_command(
        ["shell", "settings", "get", "system", "font_scale"], serial=serial
    ))
    info["font_scale"] = result.stdout.strip() if result else "unknown"

    result = run_command(build_adb_command(
        ["shell", "cmd", "uimode", "night"], serial=serial
    ))
    info["dark_mode"] = result.stdout.strip() if result else "unknown"

    result = run_command(build_adb_command(
        ["shell", "wm", "density"], serial=serial
    ))
    info["density"] = result.stdout.strip() if result else "unknown"

    result = run_command(build_adb_command(
        ["shell", "settings", "get", "system", "accelerometer_rotation"], serial=serial
    ))
    info["auto_rotation"] = "on" if result and result.stdout.strip() == "1" else "off"

    result = run_command(build_adb_command(
        ["shell", "getprop", "persist.sys.locale"], serial=serial
    ))
    info["locale"] = result.stdout.strip() if result else "unknown"

    result = run_command(build_adb_command(
        ["shell", "settings", "get", "global", "animator_duration_scale"], serial=serial
    ))
    info["animations"] = "on" if result and result.stdout.strip() != "0.0" else "off"

    return info


def main():
    parser = argparse.ArgumentParser(description="Change Android device settings")
    parser.add_argument("--locale", help="Set locale (e.g., 'tr', 'en', 'tr-TR', 'en-US')")
    parser.add_argument("--dark-mode", choices=["on", "off"], help="Toggle dark mode")
    parser.add_argument("--font-scale", type=float, help="Font scale (0.85, 1.0, 1.15, 1.3, 1.5, 2.0)")
    parser.add_argument("--density", type=int, help="Display density in DPI (e.g., 320, 420, 560)")
    parser.add_argument("--rotation", type=int, choices=[0, 1, 2, 3],
                        help="Screen rotation (0=portrait, 1=landscape)")
    parser.add_argument("--auto-rotation", choices=["on", "off"], help="Toggle auto-rotation")
    parser.add_argument("--animations", choices=["on", "off"], help="Toggle animations")
    parser.add_argument("--reset", action="store_true", help="Reset all to defaults")
    parser.add_argument("--status", action="store_true", help="Show current settings")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serial", help="Device serial number")
    parser.add_argument("--name", help="AVD name")
    args = parser.parse_args()

    try:
        serial = resolve_serial(serial=args.serial, name=args.name)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.status:
        settings = get_current_settings(serial)
        if args.json:
            print(json.dumps(settings, indent=2))
        else:
            for k, v in settings.items():
                print(f"  {k}: {v}")
        sys.exit(0)

    if args.reset:
        success, msg = reset_all(serial)
        print(json.dumps({"success": success, "message": msg}) if args.json else msg)
        sys.exit(0)

    results = []

    if args.locale:
        results.append(set_locale(serial, args.locale))
    if args.dark_mode:
        results.append(set_dark_mode(serial, args.dark_mode == "on"))
    if args.font_scale:
        results.append(set_font_scale(serial, args.font_scale))
    if args.density:
        results.append(set_display_density(serial, args.density))
    if args.rotation is not None:
        results.append(set_screen_rotation(serial, args.rotation))
    if args.auto_rotation:
        results.append(set_auto_rotation(serial, args.auto_rotation == "on"))
    if args.animations:
        results.append(set_animations(serial, args.animations == "on"))

    if not results:
        parser.print_help()
        sys.exit(1)

    for success, msg in results:
        if args.json:
            print(json.dumps({"success": success, "message": msg}))
        else:
            print(msg)


if __name__ == "__main__":
    main()
