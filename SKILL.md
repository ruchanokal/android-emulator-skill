# Android Emulator Skill

Build, test, and automate Android applications using accessibility-driven navigation and structured data instead of pixel coordinates. Includes Android-exclusive capabilities like network throttling, GPS mocking, screen recording, intent testing, and fuzz testing.

## Quick Start

```bash
# 1. Check environment
bash scripts/health_check.sh

# 2. Boot emulator
python3 scripts/emulator_boot.py --avd Pixel_6_API_34

# 3. Launch app
python3 scripts/app_launcher.py --launch com.example.app

# 4. Map screen to see elements
python3 scripts/screen_mapper.py

# 5. Tap button
python3 scripts/navigator.py --find-text "Login" --tap

# 6. Enter text
python3 scripts/navigator.py --find-type EditText --enter-text "user@example.com"
```

All scripts support `--help` for detailed options and `--json` for machine-readable output.

## Navigation Strategy

**Always prefer the UI hierarchy over screenshots for navigation.** The UI hierarchy (via uiautomator) gives you element types, labels, bounds, and tap targets — structured data that's cheaper and more reliable than image analysis.

Use this priority:
1. `screen_mapper.py` → structured element list (5-7 lines, ~10 tokens)
2. `navigator.py --find-text/--find-type/--find-id` → semantic interaction
3. Screenshots → only for visual verification, bug reports, or visual diff

Screenshots cost 1,600–6,300 tokens depending on size. The UI hierarchy costs 10–50 tokens in default mode.

## 29 Production Scripts

### Build & Development (2 scripts)

1. **build_and_test.py** - Build Gradle projects, run tests, parse results
   - Build with variant selection (debug/release)
   - Run unit tests and instrumented tests
   - Install on device, lint checks
   - Options: `--project`, `--module`, `--build`, `--test`, `--connected-test`, `--install`, `--lint`, `--variant`, `--clean`, `--verbose`, `--json`

2. **log_monitor.py** - Real-time log monitoring with intelligent filtering
   - Stream logs via logcat or capture by duration
   - Filter by severity (verbose/debug/info/warning/error/fatal) and app
   - Deduplicate repeated messages
   - Options: `--app`, `--severity`, `--follow`, `--duration`, `--last`, `--output`, `--verbose`, `--json`, `--serial`

### Navigation & Interaction (5 scripts)

3. **screen_mapper.py** - Analyze current screen and list interactive elements
   - Element type breakdown (Button, EditText, ImageView, etc.)
   - Interactive button list with labels
   - Text field status (filled/empty/focused)
   - Options: `--verbose`, `--hints`, `--json`, `--serial`, `--name`

4. **navigator.py** - Find and interact with elements semantically
   - Find by text (fuzzy matching on text + content-desc)
   - Find by element type (EditText, Button, etc.)
   - Find by resource ID
   - Enter text or tap elements
   - Options: `--find-text`, `--find-type`, `--find-id`, `--tap`, `--enter-text`, `--index`, `--json`, `--serial`

5. **gesture.py** - Perform swipes, scrolls, pinches, and complex gestures
   - Directional swipes (up/down/left/right)
   - Multi-step scrolling
   - Long press, double tap
   - Pull to refresh
   - Options: `--swipe`, `--swipe-from`, `--swipe-to`, `--scroll`, `--long-press`, `--refresh`, `--tap`, `--double-tap`, `--duration`, `--json`, `--serial`

6. **keyboard.py** - Text input and hardware button control
   - Type text (fast or slow mode)
   - Special keys (enter, delete, tab, space, arrows, escape)
   - Hardware buttons (home, back, power, volume, recent-apps, screenshot)
   - Clear text, dismiss keyboard
   - Options: `--type`, `--key`, `--button`, `--clear`, `--dismiss`, `--back`, `--count`, `--slow`, `--json`, `--serial`

7. **app_launcher.py** - App lifecycle management
   - Launch apps by package name (with optional activity)
   - Terminate (force stop), restart apps
   - Install/uninstall APKs
   - Deep link navigation, list installed apps
   - Check app state, clear app data
   - Options: `--launch`, `--terminate`, `--restart`, `--install`, `--uninstall`, `--open-url`, `--list`, `--state`, `--current`, `--clear`, `--json`, `--serial`

### Testing & Analysis (5 scripts)

8. **accessibility_audit.py** - Check accessibility compliance on current screen
   - Critical issues (missing labels, images without descriptions)
   - Warnings (small touch targets, EditText without hints)
   - Info (missing resource IDs, deep nesting)
   - Options: `--verbose`, `--output`, `--json`, `--serial`

9. **visual_diff.py** - Compare two screenshots for visual changes
   - Pixel-by-pixel comparison with threshold
   - Generate amplified diff images
   - Options: `image1`, `image2`, `--threshold`, `--output`, `--details`, `--json`

10. **test_recorder.py** - Automatically document test execution
    - Capture screenshots and UI hierarchy per step
    - Generate markdown + JSON reports
    - Options: `--test-name`, `--output`, `--step`, `--report`, `--json`, `--serial`

11. **app_state_capture.py** - Create comprehensive debugging snapshots
    - Screenshot, UI hierarchy, app logs, device info
    - Markdown summary for bug reports
    - Options: `--app-bundle-id`, `--output`, `--log-lines`, `--json`, `--serial`

12. **health_check.sh** - Verify environment is properly configured
    - Check Java, adb, emulator, avdmanager, Python 3
    - List available AVDs and running emulators
    - Verify Python packages (Pillow)

### Advanced Testing & Permissions (4 scripts)

13. **clipboard.py** - Manage device clipboard for paste testing
    - Copy text to clipboard
    - Options: `--copy`, `--json`, `--serial`

14. **push_notification.py** - Send simulated push notifications
    - Simple mode (title + body)
    - Custom data payloads
    - Options: `--bundle-id`, `--title`, `--body`, `--badge`, `--data`, `--json`, `--serial`

15. **permission_manager.py** - Grant, revoke, and manage app permissions
    - 17 permission shortcuts (camera, microphone, location, contacts, etc.)
    - Batch operations (comma-separated)
    - List all granted/denied permissions
    - Options: `--bundle-id`, `--grant`, `--revoke`, `--list`, `--reset`, `--json`, `--serial`

16. **emulator_wipe.py** - Factory reset emulators without deletion
    - Preserve AVD configuration (faster than delete+create)
    - Wipe user data and snapshots
    - Options: `--name`, `--all`, `--yes`, `--json`

### Device Lifecycle Management (5 scripts)

17. **emulator_boot.py** - Boot emulators with readiness verification
    - Boot by AVD name with partial matching
    - Wait for boot completion (sys.boot_completed)
    - Cold boot option (no snapshot)
    - Headless mode (no window)
    - List AVDs and running emulators
    - Options: `--avd`, `--cold-boot`, `--no-window`, `--no-wait`, `--timeout`, `--list`, `--running`, `--all`, `--json`

18. **emulator_shutdown.py** - Gracefully shutdown emulators
    - Shutdown by serial or AVD name
    - Optional verification of shutdown completion
    - Batch shutdown operations
    - Options: `--serial`, `--name`, `--verify`, `--timeout`, `--all`, `--json`

19. **emulator_create.py** - Create AVDs dynamically
    - Create by device type and system image
    - List available device types and system images
    - Options: `--name`, `--device`, `--package`, `--force`, `--list-devices`, `--list-images`, `--list-avds`, `--json`

20. **emulator_delete.py** - Permanently delete AVDs
    - Safety confirmation by default (skip with --yes)
    - Batch delete operations
    - Options: `--name`, `--yes`, `--all`, `--json`

### Android-Exclusive Features (8 scripts)

21. **network_control.py** - Control network settings (WiFi, airplane mode, throttling)
    - Toggle WiFi on/off
    - Toggle airplane mode
    - Toggle mobile data
    - Network speed throttling via emulator console (full/5g/4g/3g/edge/gprs/none)
    - Check network status with connectivity test
    - Options: `--wifi on|off`, `--airplane on|off`, `--data on|off`, `--throttle <preset>`, `--status`, `--json`, `--serial`

22. **location_mock.py** - Mock GPS location on emulator
    - Set exact coordinates (lat/lng/altitude)
    - 14 built-in presets (Turkish cities + world capitals)
    - Enable mock location provider for apps
    - Options: `--lat`, `--lng`, `--altitude`, `--preset`, `--list-presets`, `--enable-mock`, `--package`, `--json`, `--serial`

23. **screen_record.py** - Record screen video
    - Timed recording (up to 180 seconds)
    - Background recording with start/stop control
    - Custom resolution and bitrate
    - Auto-pulls MP4 from device
    - Options: `--duration`, `--output`, `--size`, `--bitrate`, `--start`, `--stop`, `--json`, `--serial`

24. **device_settings.py** - Change device settings for testing
    - Locale/language switching (15 common locales with shortcuts)
    - Dark mode toggle (Android 10+)
    - Font scale (accessibility testing)
    - Display density (DPI)
    - Screen rotation (portrait/landscape)
    - Auto-rotation toggle
    - Enable/disable animations (faster test execution)
    - Reset all to defaults
    - Options: `--locale`, `--dark-mode`, `--font-scale`, `--density`, `--rotation`, `--auto-rotation`, `--animations`, `--reset`, `--status`, `--json`, `--serial`

25. **intent_sender.py** - Send arbitrary Android intents
    - Start activities, send broadcasts, start services
    - 15 action shortcuts (view, send, dial, settings, etc.)
    - Auto-detect extra types (string, int, float, boolean)
    - Deep link shortcut
    - App settings shortcut
    - Options: `--action`, `--data`, `--component`, `--package`, `--category`, `--type`, `--extra`, `--flag`, `--broadcast`, `--service`, `--deep-link`, `--app-settings`, `--list-actions`, `--json`, `--serial`

26. **monkey_test.py** - Fuzz/stress testing with Android monkey
    - Random UI events (tap, swipe, key) at configurable rate
    - Event type distribution control (touch/nav/system percentages)
    - Crash and ANR detection with detailed reports
    - Reproducible tests via seed
    - Options: `--package`, `--events`, `--throttle`, `--touch`, `--nav`, `--sys`, `--seed`, `--ignore-crashes`, `--ignore-timeouts`, `--verbose`, `--json`, `--serial`

27. **file_manager.py** - Push, pull, and manage files on device
    - Push/pull files and directories
    - List, remove, create directories on device
    - Read file contents (cat), file info (stat)
    - Pull app data directory (for debuggable apps)
    - Pull shared preferences XML
    - Pull database files
    - Options: `--push`, `--pull`, `--ls`, `--rm`, `--mkdir`, `--cat`, `--stat`, `--pull-app-data`, `--pull-prefs`, `--pull-db`, `--db-name`, `--output`, `--json`, `--serial`

28. **port_forward.py** - ADB port forwarding for local dev servers
    - Forward ports (host → device access)
    - Reverse ports (device → host access, for emulator reaching localhost)
    - 10 built-in presets (Firebase emulators, React dev, Metro bundler, etc.)
    - `--firebase` shortcut: reverse all Firebase emulator ports at once
    - List, remove, and clear all port mappings
    - Options: `--forward`, `--reverse`, `--preset`, `--firebase`, `--list`, `--list-presets`, `--remove-forward`, `--remove-reverse`, `--clear`, `--json`, `--serial`

## Common Patterns

**Auto-Serial Detection**: Most scripts auto-detect the running emulator if `--serial` is not provided.

**AVD Name Resolution**: Use `--name` with AVD names instead of serials — scripts resolve automatically.

**Batch Operations**: Many scripts support `--all` for all emulators/AVDs.

**Output Formats**: Default is concise human-readable output. Use `--json` for machine-readable output.

**Help**: All scripts support `--help` for detailed options.

**Emulator Console**: Network throttling and GPS mocking use the emulator telnet console (auto-authenticated).

## Typical Workflow

1. Verify environment: `bash scripts/health_check.sh`
2. Boot emulator: `python3 scripts/emulator_boot.py --avd Pixel_6_API_34`
3. Set up dev environment: `python3 scripts/port_forward.py --firebase`
4. Launch app: `python3 scripts/app_launcher.py --launch com.example.app`
5. Analyze screen: `python3 scripts/screen_mapper.py`
6. Interact: `python3 scripts/navigator.py --find-text "Button" --tap`
7. Test conditions: `python3 scripts/network_control.py --throttle 3g`
8. Test locations: `python3 scripts/location_mock.py --preset istanbul-kadikoy`
9. Verify accessibility: `python3 scripts/accessibility_audit.py`
10. Stress test: `python3 scripts/monkey_test.py --package com.example.app --events 500`
11. Debug if needed: `python3 scripts/app_state_capture.py --app-bundle-id com.example.app`

## Requirements

- macOS / Linux / Windows
- Android SDK Platform-Tools (adb)
- Android SDK Emulator
- Java 17+
- Python 3
- Pillow (optional, for screenshots/visual diff): `pip3 install Pillow`

## Key Design Principles

**Semantic Navigation**: Find elements by meaning (text, type, ID) not pixel coordinates. Survives UI changes.

**Token Efficiency**: Concise default output (3-5 lines) with optional verbose and JSON modes.

**Accessibility-First**: Built on UIAutomator accessibility tree for reliability.

**Zero Configuration**: Works immediately with Android SDK installed. No additional setup required.

**Structured Data**: Scripts output JSON or formatted text, not raw logs.

**Android-Native Power**: Leverages Android-exclusive capabilities (intents, monkey, emulator console) that have no iOS equivalent.

---

Use these scripts directly or let Claude Code invoke them automatically when your request matches the skill description.
