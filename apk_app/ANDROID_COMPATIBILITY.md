# Android Compatibility Plan (BarcodOmatic Mobile)

This document defines what is needed to run efficiently across Android devices, including current Android OS releases.

## Current Build Settings Applied

- Target API: 35 (`android.api = 35`)
- Minimum API: 24 (`android.minapi = 24`)
- NDK: `25b`
- Architectures: `arm64-v8a`, `armeabi-v7a`
- Release artifact: `aab`
- Debug artifact: `apk`
- Permissions: `INTERNET` only

These settings support modern Play requirements while keeping broad device reach.

## Why These Settings

- API 35 target is required for current Play submissions (new apps/updates).
- Min API 24 avoids install failures on newer Android policy floors while still covering many active devices.
- arm64 + armeabi-v7a covers modern 64-bit phones and many older 32-bit devices.
- AAB is preferred for Play distribution and device-specific splits.
- Removing legacy storage permissions improves privacy compliance and avoids unnecessary prompts.

## Performance and Stability Changes Applied

- Online lookup moved to a background thread to prevent UI freezes.
- UI updates from background work are marshaled to the main thread (`@mainthread`).
- App stores data under app-private storage (`user_data_dir`) to avoid scoped-storage issues.

## Device Test Matrix (Must Pass)

Test each of these before release:

1. Android 8/9 class device (API 26-28)
2. Android 10/11 class device (API 29-30)
3. Android 12/13 class device (API 31-33)
4. Android 14 device (API 34)
5. Android 15 device (API 35)
6. One low-RAM device (3 GB or less)
7. One tablet / large-screen device

## Functional Test Checklist

1. App launch time under 3 seconds on mid-range hardware
2. Load CSV, edit record, save, relaunch, verify persistence
3. Barcode not-found flow + online lookup success path
4. Offline mode: app remains stable and shows useful status
5. Generate barcode image repeatedly (10+ times) without crash
6. Rapid screen rotations (if orientation later changed)
7. Background/foreground app switch during lookup
8. Force-stop then relaunch (state recovers cleanly)

## New Android OS Considerations

- Android 14/15 enforce stricter background behavior; do network only while app is active.
- Android 15 increases minimum installable target SDK floor for sideloading older-target apps; API 35 target avoids this.
- If native extensions are added later, verify 16 KB page-size compatibility for Android 15+ devices.

## Release Build Commands (Linux/WSL)

```bash
cd apk_app
buildozer android debug
buildozer android release
```

For Play upload, use generated AAB from the `bin/` folder.

## Future Upgrades Recommended

1. Add camera barcode scanning (ZXing/MLKit bridge)
2. Add network timeout retry + exponential backoff
3. Add crash reporting (Sentry/Firebase Crashlytics via bridge)
4. Add CI build pipeline for reproducible APK/AAB outputs
5. Add automated UI smoke tests on emulators (API 28/33/35)
