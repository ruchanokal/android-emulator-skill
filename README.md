# Android Emulator Skill for Claude Code

> 29 production-ready Python scripts to automate Android emulator testing, navigation, and debugging — designed for AI agents with minimal token output.

Built as a [Claude Code custom skill](https://docs.anthropic.com/en/docs/claude-code), this toolkit gives Claude Code (or any AI agent) the ability to **boot emulators, navigate UIs semantically, run tests, mock locations, throttle networks, fuzz test, and more** — all through structured CLI commands.

## Why?

AI agents struggle with mobile app testing because:
- **Screenshots are expensive** (1,600–6,300 tokens each) and fragile (pixel coordinates break on different devices)
- **adb commands are scattered** across dozens of tools with inconsistent interfaces
- **There's no structured output** — just raw logs and text dumps

This skill solves all three:
1. **Accessibility-first navigation** — uses UIAutomator's accessibility tree (10–50 tokens) instead of screenshots
2. **Unified CLI interface** — every script follows the same patterns (`--json`, `--serial`, `--help`)
3. **Structured output** — concise human-readable defaults, JSON when you need it

## Quick Start

### 1. Install as Claude Code Skill

```bash
# Clone into Claude Code skills directory
git clone https://github.com/ruchanokal/android-emulator-skill.git \
  ~/.claude/skills/android-emulator-skill
```

Claude Code will automatically detect the skill from `SKILL.md`.

### 2. Manual Usage (without Claude Code)

```bash
# Clone anywhere
git clone https://github.com/ruchanokal/android-emulator-skill.git
cd android-emulator-skill

# Check your environment
bash scripts/health_check.sh

# Boot an emulator
python3 scripts/emulator_boot.py --avd Pixel_6_API_34

# Launch an app
python3 scripts/app_launcher.py --launch com.example.app

# See what's on screen
python3 scripts/screen_mapper.py

# Tap a button by its text
python3 scripts/navigator.py --find-text "Login" --tap

# Type into a text field
python3 scripts/navigator.py --find-type EditText --enter-text "hello@example.com"
```

## Requirements

| Requirement | Minimum | Check |
|-------------|---------|-------|
| Python | 3.8+ | `python3 --version` |
| Android SDK Platform-Tools (adb) | Any | `adb version` |
| Android SDK Emulator | Any | `emulator -version` |
| Java | 17+ | `java -version` |
| Pillow (optional) | Any | `pip3 install Pillow` |

Run `bash scripts/health_check.sh` to verify everything at once.

## All 29 Scripts

### Navigation & Interaction

| Script | Description | Example |
|--------|-------------|---------|
| `screen_mapper.py` | Analyze screen elements | `python3 scripts/screen_mapper.py --verbose` |
| `navigator.py` | Find & interact with elements | `python3 scripts/navigator.py --find-text "OK" --tap` |
| `gesture.py` | Swipes, scrolls, long press | `python3 scripts/gesture.py --swipe up` |
| `keyboard.py` | Type text, press keys/buttons | `python3 scripts/keyboard.py --type "hello"` |
| `app_launcher.py` | Launch, stop, install apps | `python3 scripts/app_launcher.py --launch com.example.app` |

### Build & Development

| Script | Description | Example |
|--------|-------------|---------|
| `build_and_test.py` | Gradle build, test, lint | `python3 scripts/build_and_test.py --build --module androidApp` |
| `log_monitor.py` | Filtered logcat monitoring | `python3 scripts/log_monitor.py --app com.example.app --severity error` |

### Testing & Analysis

| Script | Description | Example |
|--------|-------------|---------|
| `accessibility_audit.py` | WCAG compliance check | `python3 scripts/accessibility_audit.py --verbose` |
| `visual_diff.py` | Compare two screenshots | `python3 scripts/visual_diff.py before.png after.png` |
| `test_recorder.py` | Document test steps | `python3 scripts/test_recorder.py --step "Login screen"` |
| `app_state_capture.py` | Full debug snapshot | `python3 scripts/app_state_capture.py --app-bundle-id com.example.app` |
| `health_check.sh` | Verify environment | `bash scripts/health_check.sh` |
| `monkey_test.py` | Fuzz/stress testing | `python3 scripts/monkey_test.py --package com.example.app --events 500` |

### Android-Exclusive Features

| Script | Description | Example |
|--------|-------------|---------|
| `network_control.py` | WiFi, airplane mode, throttle | `python3 scripts/network_control.py --throttle 3g` |
| `location_mock.py` | Mock GPS coordinates | `python3 scripts/location_mock.py --preset istanbul-kadikoy` |
| `screen_record.py` | Record screen video | `python3 scripts/screen_record.py --duration 10 -o demo.mp4` |
| `device_settings.py` | Locale, dark mode, font, DPI | `python3 scripts/device_settings.py --dark-mode on` |
| `intent_sender.py` | Send intents & deep links | `python3 scripts/intent_sender.py --deep-link "myapp://order/123"` |
| `file_manager.py` | Push/pull files & databases | `python3 scripts/file_manager.py --pull-prefs com.example.app` |
| `port_forward.py` | ADB port forwarding | `python3 scripts/port_forward.py --firebase` |

### Permissions & Notifications

| Script | Description | Example |
|--------|-------------|---------|
| `permission_manager.py` | Grant/revoke permissions | `python3 scripts/permission_manager.py --bundle-id com.example.app --grant camera,location` |
| `push_notification.py` | Send test notifications | `python3 scripts/push_notification.py --bundle-id com.example.app --title "New order"` |
| `clipboard.py` | Clipboard management | `python3 scripts/clipboard.py --copy "test text"` |

### Emulator Lifecycle

| Script | Description | Example |
|--------|-------------|---------|
| `emulator_boot.py` | Boot with readiness check | `python3 scripts/emulator_boot.py --avd Pixel_6_API_34` |
| `emulator_shutdown.py` | Graceful shutdown | `python3 scripts/emulator_shutdown.py --all` |
| `emulator_create.py` | Create AVDs | `python3 scripts/emulator_create.py --name MyDevice --device pixel_6` |
| `emulator_delete.py` | Delete AVDs | `python3 scripts/emulator_delete.py --name MyDevice --yes` |
| `emulator_wipe.py` | Factory reset (keep AVD) | `python3 scripts/emulator_wipe.py --name MyDevice --yes` |

## How It Works

### Navigation Strategy

The skill prioritizes **structured data over visual analysis**:

```
Priority 1: screen_mapper.py → UI hierarchy (10-50 tokens)
Priority 2: navigator.py     → semantic find & interact
Priority 3: Screenshots       → only for visual verification
```

**screen_mapper.py** uses `adb shell uiautomator dump` to get the full accessibility tree, then outputs a concise summary:

```
Screen: Login (42 elements, 8 interactive)
Buttons: "Sign In", "Register", "Forgot Password"
TextFields: 2 (0 filled)
Focusable: 5 elements
```

**navigator.py** finds elements by meaning, not coordinates:

```bash
# Find by visible text (fuzzy match)
python3 scripts/navigator.py --find-text "Sign In" --tap
# → Tapped: Button "Sign In" at (540, 1200)

# Find by element type
python3 scripts/navigator.py --find-type EditText --enter-text "user@example.com"
# → Entered "user@example.com" in EditText "Email"

# Find by resource ID
python3 scripts/navigator.py --find-id "btn_submit" --tap
# → Tapped: Button "Submit" at (540, 1400)
```

### Network Throttling

Simulate real-world network conditions via the emulator console:

```bash
python3 scripts/network_control.py --throttle 3g    # 3G (~2Mbps, 300ms delay)
python3 scripts/network_control.py --throttle edge   # EDGE (~200Kbps, 500ms delay)
python3 scripts/network_control.py --throttle gprs   # GPRS (~40Kbps, 800ms delay)
python3 scripts/network_control.py --wifi off         # No WiFi
python3 scripts/network_control.py --status           # Check current state
```

### GPS Location Mocking

Test location-based features with presets or exact coordinates:

```bash
# Use a preset
python3 scripts/location_mock.py --preset istanbul-kadikoy
python3 scripts/location_mock.py --preset tokyo

# Use exact coordinates
python3 scripts/location_mock.py --lat 41.0082 --lng 28.9784

# List all presets
python3 scripts/location_mock.py --list-presets
```

Built-in presets: Istanbul (5 districts), Ankara, Izmir, Antalya, Bursa, London, Paris, New York, Tokyo, Berlin.

### Fuzz Testing

Find crashes by throwing random events at your app:

```bash
# Quick smoke test (100 events)
python3 scripts/monkey_test.py --package com.example.app --events 100

# Heavy stress test with custom distribution
python3 scripts/monkey_test.py --package com.example.app \
  --events 5000 --touch 70 --nav 20 --sys 10

# Reproduce a crash (use the seed from a previous run)
python3 scripts/monkey_test.py --package com.example.app \
  --events 5000 --seed 1234567890
```

Output:
```
Monkey test: FAILED
  Events: 3247/5000
  Seed: 1234567890 (use --seed 1234567890 to reproduce)
  Crashes: 1
    - com.example.app (PID: 12345)
```

### Port Forwarding for Local Dev

Connect your emulator to local development servers:

```bash
# Set up all Firebase emulator ports at once
python3 scripts/port_forward.py --firebase

# Custom port forwarding
python3 scripts/port_forward.py --reverse 3000       # React dev server
python3 scripts/port_forward.py --reverse 8080 9090   # Custom mapping

# See what's active
python3 scripts/port_forward.py --list

# Clean up
python3 scripts/port_forward.py --clear
```

### Device Settings for Testing

Test your app under different conditions without manual setup:

```bash
# Accessibility testing
python3 scripts/device_settings.py --font-scale 2.0   # Extra large text
python3 scripts/device_settings.py --dark-mode on      # Dark theme

# Internationalization
python3 scripts/device_settings.py --locale tr         # Turkish
python3 scripts/device_settings.py --locale ja         # Japanese
python3 scripts/device_settings.py --locale ar         # Arabic (RTL)

# Performance testing (disable animations)
python3 scripts/device_settings.py --animations off

# Reset everything
python3 scripts/device_settings.py --reset
```

## Common Patterns

### Auto-Detection
Most scripts automatically detect the running emulator. No need to pass `--serial` unless you have multiple devices:

```bash
# These all auto-detect the device
python3 scripts/screen_mapper.py
python3 scripts/navigator.py --find-text "OK" --tap
python3 scripts/keyboard.py --type "hello"
```

### JSON Output
Every script supports `--json` for machine-readable output:

```bash
python3 scripts/screen_mapper.py --json | jq '.buttons'
python3 scripts/emulator_boot.py --list --json
```

### Typical Test Workflow

```bash
# 1. Environment
bash scripts/health_check.sh

# 2. Boot & setup
python3 scripts/emulator_boot.py --avd Pixel_6_API_34
python3 scripts/port_forward.py --firebase
python3 scripts/device_settings.py --animations off

# 3. Install & launch
python3 scripts/app_launcher.py --install app-debug.apk
python3 scripts/app_launcher.py --launch com.example.app

# 4. Navigate & test
python3 scripts/screen_mapper.py
python3 scripts/navigator.py --find-text "Login" --tap
python3 scripts/navigator.py --find-type EditText --enter-text "test@example.com"
python3 scripts/keyboard.py --key enter

# 5. Test edge cases
python3 scripts/network_control.py --throttle 3g
python3 scripts/location_mock.py --preset istanbul-kadikoy
python3 scripts/device_settings.py --font-scale 1.5

# 6. Verify & report
python3 scripts/accessibility_audit.py
python3 scripts/monkey_test.py --package com.example.app --events 200
python3 scripts/app_state_capture.py --app-bundle-id com.example.app

# 7. Clean up
python3 scripts/device_settings.py --reset
python3 scripts/port_forward.py --clear
python3 scripts/emulator_shutdown.py --all
```

## Project Structure

```
android-emulator-skill/
├── SKILL.md                          # Claude Code skill definition
├── README.md                         # This file
└── scripts/
    ├── common/                       # Shared utilities
    │   ├── __init__.py
    │   ├── device_utils.py           # ADB command builders, device detection
    │   ├── uiautomator_utils.py      # UI hierarchy parsing (XML → structured data)
    │   └── screenshot_utils.py       # Screenshot capture & resize
    ├── screen_mapper.py              # Screen element analysis
    ├── navigator.py                  # Semantic UI navigation
    ├── gesture.py                    # Swipes, scrolls, gestures
    ├── keyboard.py                   # Text input & hardware buttons
    ├── app_launcher.py               # App lifecycle management
    ├── build_and_test.py             # Gradle build & test
    ├── log_monitor.py                # Logcat monitoring
    ├── accessibility_audit.py        # Accessibility compliance
    ├── visual_diff.py                # Screenshot comparison
    ├── test_recorder.py              # Test documentation
    ├── app_state_capture.py          # Debug snapshots
    ├── health_check.sh               # Environment verification
    ├── network_control.py            # Network settings & throttling
    ├── location_mock.py              # GPS mocking
    ├── screen_record.py              # Video recording
    ├── device_settings.py            # Device configuration
    ├── intent_sender.py              # Intent & deep link testing
    ├── monkey_test.py                # Fuzz testing
    ├── file_manager.py               # File push/pull/inspect
    ├── port_forward.py               # Port forwarding
    ├── permission_manager.py         # App permissions
    ├── push_notification.py          # Notification testing
    ├── clipboard.py                  # Clipboard management
    ├── emulator_boot.py              # Boot emulators
    ├── emulator_shutdown.py          # Shutdown emulators
    ├── emulator_create.py            # Create AVDs
    ├── emulator_delete.py            # Delete AVDs
    └── emulator_wipe.py              # Factory reset AVDs
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow existing code patterns (argparse, `--json` output, `--serial` support)
4. Test with a real emulator
5. Submit a pull request
