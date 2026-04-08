#!/bin/bash
# Android Emulator Skill - Environment Health Check

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CHECKS_PASSED=0
CHECKS_FAILED=0

check_passed() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_failed() {
    echo -e "  ${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warning() {
    echo -e "  ${YELLOW}!${NC} $1"
}

echo -e "${BLUE}=== Android Emulator Skill - Health Check ===${NC}"
echo ""

# 1. Check macOS
echo "1. Operating System"
OS_VERSION=$(sw_vers -productVersion 2>/dev/null)
if [ -n "$OS_VERSION" ]; then
    check_passed "macOS $OS_VERSION"
else
    OS_VERSION=$(uname -sr)
    check_passed "$OS_VERSION"
fi

# 2. Check Java
echo ""
echo "2. Java"
if command -v java &>/dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -1)
    check_passed "$JAVA_VERSION"
else
    check_failed "Java not found. Install JDK 17+"
fi

# 3. Check Android SDK / adb
echo ""
echo "3. Android SDK (adb)"
if command -v adb &>/dev/null; then
    ADB_VERSION=$(adb version 2>&1 | head -1)
    check_passed "$ADB_VERSION"
else
    check_failed "adb not found. Install Android SDK Platform-Tools"
fi

# 4. Check emulator command
echo ""
echo "4. Android Emulator"
if command -v emulator &>/dev/null; then
    EMU_VERSION=$(emulator -version 2>&1 | head -1)
    check_passed "$EMU_VERSION"
else
    check_failed "emulator not found. Install Android SDK Emulator"
fi

# 5. Check avdmanager
echo ""
echo "5. AVD Manager"
if command -v avdmanager &>/dev/null; then
    check_passed "avdmanager available"
else
    check_warning "avdmanager not found (optional - needed for creating AVDs)"
fi

# 6. Check Python
echo ""
echo "6. Python 3"
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    check_passed "$PY_VERSION"
else
    check_failed "Python 3 not found"
fi

# 7. Check available AVDs
echo ""
echo "7. Available AVDs"
if command -v emulator &>/dev/null; then
    AVDS=$(emulator -list-avds 2>/dev/null)
    if [ -n "$AVDS" ]; then
        AVD_COUNT=$(echo "$AVDS" | wc -l | tr -d ' ')
        check_passed "$AVD_COUNT AVD(s) available:"
        echo "$AVDS" | head -5 | while read -r avd; do
            echo "      - $avd"
        done
        if [ "$AVD_COUNT" -gt 5 ]; then
            echo "      ... and $((AVD_COUNT - 5)) more"
        fi
    else
        check_warning "No AVDs found. Create one with Android Studio or avdmanager"
    fi
else
    check_failed "Cannot list AVDs (emulator not found)"
fi

# 8. Check running emulators
echo ""
echo "8. Running Emulators"
if command -v adb &>/dev/null; then
    RUNNING=$(adb devices 2>/dev/null | grep "emulator-" | grep "device")
    if [ -n "$RUNNING" ]; then
        RUNNING_COUNT=$(echo "$RUNNING" | wc -l | tr -d ' ')
        check_passed "$RUNNING_COUNT emulator(s) running:"
        echo "$RUNNING" | while read -r line; do
            echo "      - $line"
        done
    else
        check_warning "No running emulators"
    fi
else
    check_failed "Cannot check running emulators"
fi

# 9. Check Pillow (optional)
echo ""
echo "9. Python Packages"
if python3 -c "from PIL import Image" 2>/dev/null; then
    check_passed "Pillow (PIL) available"
else
    check_warning "Pillow not installed (optional - needed for screenshots/visual diff)"
    echo "      Install with: pip3 install Pillow"
fi

# Summary
echo ""
echo -e "${BLUE}=== Summary ===${NC}"
echo -e "  Passed: ${GREEN}${CHECKS_PASSED}${NC}"
echo -e "  Failed: ${RED}${CHECKS_FAILED}${NC}"

if [ "$CHECKS_FAILED" -eq 0 ]; then
    echo -e "  ${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "  ${RED}Some checks failed. Fix the issues above.${NC}"
    exit 1
fi
