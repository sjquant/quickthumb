# Android Drawable reference fixture

Used by `scripts/check_lottie_android.py` with the existing web reference manifest.
The official Lottie Android 6.7.1 AAR runs on Robolectric 4.17, API 35 native
graphics, mdpi and software Drawable rendering. Tests assert the native runtime
actually loads. This is Linux/JVM execution, not a device, emulator or GPU test.

The fixture pins the minimal Drawable dependencies. AppCompat UI dependencies
are excluded because no `LottieAnimationView`, activity or Android resource/UI
integration is exercised. Maven copies only the resolved AAR closure; the helper
exposes those classes to the test JVM. Lottie calls use reflection because ordinary
Java compilation cannot consume AAR `classes.jar` directly. Positive payloads
are read verbatim; only the explicit blank control replaces its layers.

The Python gate, not JUnit status alone, establishes image acceptance. Errors,
clock mismatches and missed negative controls fail the run. Dependencies are
resolved only when this optional developer check or its CI step is invoked.
No Android artifacts are bundled into the product.
