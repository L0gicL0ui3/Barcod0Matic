#!/usr/bin/env bash
# BarcodOmatic Mobile — ADB device installer
# Installs the debug APK built by build.sh onto a connected Android device.
#
# Requirements:
#   - ADB installed and on PATH (comes with Android SDK Platform Tools)
#   - USB debugging enabled on the device (Settings > Developer Options)
#   - Device connected via USB (or ADB over Wi-Fi — see below)
#
# Usage:
#   bash install.sh              # auto-detect latest APK in bin/
#   bash install.sh path/to.apk  # install a specific APK file

set -euo pipefail

# ── Find APK ─────────────────────────────────────────────────────────────────
if [[ -n "${1:-}" ]]; then
    APK="$1"
else
    APK=$(ls -t bin/*.apk 2>/dev/null | head -n1 || true)
fi

if [[ -z "$APK" || ! -f "$APK" ]]; then
    echo "[ERROR] No APK found."
    echo "        Run 'bash build.sh debug' first, or pass the APK path as an argument."
    exit 1
fi

echo "[INFO] APK: $APK"

# ── Check ADB ────────────────────────────────────────────────────────────────
if ! command -v adb &>/dev/null; then
    echo "[ERROR] ADB not found on PATH."
    echo ""
    echo "Install Android SDK Platform Tools:"
    echo "  Windows: https://developer.android.com/tools/releases/platform-tools"
    echo "  WSL:     sudo apt install adb"
    exit 1
fi

# ── Check device connection ───────────────────────────────────────────────────
DEVICES=$(adb devices | grep -E "^[^\s].*device$" | wc -l)
if [[ "$DEVICES" -eq 0 ]]; then
    echo "[ERROR] No Android device detected."
    echo ""
    echo "Checklist:"
    echo "  1. Connect device via USB"
    echo "  2. Enable Developer Options: Settings > About Phone > tap Build Number 7 times"
    echo "  3. Enable USB Debugging: Settings > Developer Options > USB Debugging"
    echo "  4. On the device, tap 'Allow' on the USB debugging authorisation prompt"
    echo "  5. Run: adb devices   — your device should show as 'device' (not 'unauthorized')"
    echo ""
    echo "  ADB over Wi-Fi (Android 11+):"
    echo "    adb connect <device-ip>:5555"
    exit 1
fi

if [[ "$DEVICES" -gt 1 ]]; then
    echo "[WARN] Multiple devices connected. ADB will use the first one listed."
    echo "       To target a specific device: adb -s <serial> install ..."
    adb devices
fi

# ── Install ───────────────────────────────────────────────────────────────────
echo "[INFO] Installing to device..."
adb install -r "$APK"

PACKAGE="com.edm4v.barcodomaticmobile"
echo ""
echo "[DONE] Installation complete."
echo "       The app should appear in your launcher as 'BarcodOmatic Mobile'."
echo ""
echo "       To launch from command line:"
echo "         adb shell am start -n ${PACKAGE}/org.kivy.android.PythonActivity"
echo ""
echo "       To view live logs:"
echo "         adb logcat -s python"
echo ""
echo "       To uninstall:"
echo "         adb uninstall ${PACKAGE}"
