# Flutter and Android Collectors

## Flutter (`flutter-log`)

Capture the narrow failing run:

```bash
flutter run --verbose > flutter-failure.log 2>&1
evidence collect <DEP> --collector flutter-log --input flutter-failure.log
```

Prefer `flutter test <target> --machine` for deterministic test evidence. Record device/simulator, OS, Flutter/Dart version, build mode, locale, permissions, and network condition.

## Android Logcat (`android-logcat`)

Clear stale logs only in a disposable test context, reproduce once, and filter to the application process or relevant tags:

```bash
adb logcat -v threadtime --pid=<test-app-pid> > logcat-failure.log
evidence collect <DEP> --collector android-logcat --input logcat-failure.log
```

Likely secrets: account identifiers, push tokens, deep links, Intent extras, local file paths, OAuth callbacks, speech text, location, and device identifiers. Do not request a production user's full logcat.

For permission bugs, separately record microphone, speech, camera, location, notification, and settings-recovery state. A visible permission dialog proves only the UI state, not successful capability execution.
