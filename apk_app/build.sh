#!/usr/bin/env bash
# BarcodOmatic Mobile — one-command WSL build script
# Run from WSL Ubuntu: bash build.sh [debug|release]
# Default: debug  (produces APK for direct ADB sideloading)
#          release (produces AAB for Google Play upload)

set -euo pipefail

MODE="${1:-debug}"

# ── Dependency check ────────────────────────────────────────────────────────
check_deps() {
    local missing=()
    for cmd in python3 pip java; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "[ERROR] Missing system tools: ${missing[*]}"
        echo "Install with:"
        echo "  sudo apt install -y python3-pip openjdk-17-jdk autoconf automake libtool pkg-config zlib1g-dev libffi-dev libssl-dev"
        exit 1
    fi

    if ! command -v buildozer &>/dev/null; then
        echo "[INFO] Buildozer not found — installing..."
        pip install --user --upgrade buildozer cython
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# ── Build ────────────────────────────────────────────────────────────────────
build() {
    echo "[INFO] Starting $MODE build..."
    if [[ "$MODE" == "release" ]]; then
        buildozer -v android release
        echo ""
        echo "[DONE] Release AAB is in: bin/*.aab"
        echo "       Upload to Google Play Console for distribution."
        echo "       To test on a device, use install.sh with bundletool (see INSTALL_DEVICE.md)."
    else
        buildozer -v android debug
        APK=$(ls bin/*.apk 2>/dev/null | head -n1 || true)
        echo ""
        echo "[DONE] Debug APK is in: $APK"
        echo "       To install on a connected device, run: bash install.sh"
    fi
}

check_deps
build
