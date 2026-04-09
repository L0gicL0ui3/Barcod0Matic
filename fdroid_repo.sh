#!/usr/bin/env bash
# BarcodOmatic Mobile — Local F-Droid repository setup
#
# This creates a self-hosted F-Droid repo so users can install the app
# directly from F-Droid client (or download APK for ADB sideloading)
# without submitting to the official F-Droid index.
#
# Run from WSL Ubuntu AFTER building with: bash build.sh debug
#
# Requirements:
#   sudo apt install -y fdroidserver
#
# Usage:
#   bash fdroid_repo.sh           # initialize and add latest APK
#   bash fdroid_repo.sh update    # rebuild repo index after adding a new APK

set -euo pipefail

REPO_DIR="$(pwd)/fdroid_repo"
APK_SRC="../apk_app/bin"

# ── Install fdroidserver if missing ──────────────────────────────────────────
if ! command -v fdroid &>/dev/null; then
    echo "[INFO] fdroidserver not found — installing..."
    sudo apt install -y fdroidserver
fi

# ── Initialize repo (first run only) ─────────────────────────────────────────
if [[ ! -d "$REPO_DIR/repo" ]]; then
    echo "[INFO] Initializing F-Droid repo at $REPO_DIR ..."
    mkdir -p "$REPO_DIR"
    cd "$REPO_DIR"
    fdroid init
    # Patch config.yml with app details
    cat > config.yml <<'CONFIG'
repo_url: "https://your-server.example.com/fdroid/repo"
repo_name: "BarcodOmatic Releases"
repo_description: "Unofficial F-Droid repo for BarcodOmatic Mobile"
repo_icon: "icon.png"
# Change to your keystore path after running 'fdroid init'
# keystore: /path/to/my.keystore
CONFIG
    echo ""
    echo "[INFO] Repo initialized. Before publishing:"
    echo "       1. Edit $REPO_DIR/config.yml and set your actual server URL"
    echo "       2. Keep the generated keystore safe — losing it means users cannot update"
    cd ..
fi

# ── Copy latest APK into repo ─────────────────────────────────────────────────
APK=$(ls -t "${APK_SRC}"/*.apk 2>/dev/null | head -n1 || true)
if [[ -z "$APK" ]]; then
    echo "[ERROR] No APK found in $APK_SRC"
    echo "        Run 'bash apk_app/build.sh debug' first."
    exit 1
fi

APK_NAME=$(basename "$APK")
if [[ ! -f "$REPO_DIR/repo/$APK_NAME" ]]; then
    echo "[INFO] Adding $APK_NAME to repo..."
    cp "$APK" "$REPO_DIR/repo/"
fi

# Copy icon
if [[ -f "apk_app/icon.png" && ! -f "$REPO_DIR/repo/icon.png" ]]; then
    cp apk_app/icon.png "$REPO_DIR/repo/icon.png"
fi

# ── Rebuild index ─────────────────────────────────────────────────────────────
echo "[INFO] Building F-Droid repo index..."
cd "$REPO_DIR"
fdroid update --create-key --delete-unknown
fdroid deploy 2>/dev/null || true   # optional: deploy to server if configured
echo ""
echo "[DONE] F-Droid repo is ready at: $REPO_DIR/repo/"
echo ""
echo "  To share with others:"
echo "    1. Copy the 'repo/' folder to a web server"
echo "    2. Users open F-Droid app > Settings > Repositories > + Add"
echo "       and enter: https://your-server.example.com/fdroid/repo"
echo ""
echo "  To install via ADB (no web server needed):"
echo "    Copy the APK from $REPO_DIR/repo/ to your machine, then:"
echo "    adb install -r $APK_NAME"
echo ""
echo "  To share locally over HTTP (LAN only, for testing):"
echo "    python3 -m http.server 8080 --directory $REPO_DIR/repo &"
echo "    # Then in F-Droid: http://<your-WSL-or-PC-IP>:8080"
