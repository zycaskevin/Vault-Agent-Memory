# Flutter and Android Collectors

## Flutter (`flutter-log`)

Capture the narrow failing run:

```bash
umask 077
if ! mkdir -p <DEP>/private/raw; then exit 1; fi
if ! chmod 700 <DEP>/private/raw; then exit 1; fi
flutter run --verbose > <DEP>/private/raw/flutter-failure.log 2>&1
# Reproduce once, Press `q`, and wait until `flutter run` exits before continuing.
evidence collect <DEP> --collector flutter-log --input <DEP>/private/raw/flutter-failure.log
```

`flutter run` is interactive and unbounded until stopped. Do not background it or place collection on the same line: Press `q`, wait until `flutter run` exits, then run `evidence collect` so collection cannot race a live writer.

Prefer `flutter test <target> --machine` for deterministic test evidence. Record device/simulator, OS, Flutter/Dart version, build mode, locale, permissions, and network condition.

## Android Logcat (`android-logcat`)

Clear stale logs only in a disposable test context, reproduce once, and filter to the application process or relevant tags:

```bash
umask 077
if ! mkdir -p <DEP>/private/raw; then exit 1; fi
if ! chmod 700 <DEP>/private/raw; then exit 1; fi
adb logcat -v threadtime --pid=<test-app-pid> > <DEP>/private/raw/logcat-failure.log 2>&1
# Reproduce once, Press Ctrl-C, and wait until `adb logcat` exits before continuing.
evidence collect <DEP> --collector android-logcat --input <DEP>/private/raw/logcat-failure.log
```

`adb logcat` is a live stream. Press Ctrl-C, wait until `adb logcat` exits, and only then run `evidence collect`; do not background the writer or create the unredacted log in the working directory.

Likely secrets: account identifiers, push tokens, deep links, Intent extras, local file paths, OAuth callbacks, speech text, location, and device identifiers. Do not request a production user's full logcat.

For permission bugs, separately record microphone, speech, camera, location, notification, and settings-recovery state. A visible permission dialog proves only the UI state, not successful capability execution.
