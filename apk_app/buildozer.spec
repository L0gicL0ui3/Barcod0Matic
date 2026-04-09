[app]
title = BarcodOmatic Mobile
package.name = barcodomaticmobile
package.domain = com.edm4v
source.dir = .
source.include_exts = py,png,jpg,kv,csv,ico,txt
version = 1.0.0
# android.numeric_version is the integer versionCode required by F-Droid and Google Play.
# Increment by 1 with every release.
android.numeric_version = 1
requirements = python3,kivy,python-barcode,pillow
icon.filename = icon.png
orientation = portrait
fullscreen = 0

# Android permissions
# INTERNET is required for Open Food Facts / UPCitemdb lookups.
# Storage permissions are intentionally omitted: app data is stored in user_data_dir.
android.permissions = INTERNET

# Keep this false for Play Store safety unless you rely on local HTTP endpoints
android.allow_cleartext = False

# Android compatibility and distribution settings
# Keep target API aligned with current Google Play requirements.
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.release_artifact = aab
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
