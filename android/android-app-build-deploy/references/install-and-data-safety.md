# Install, reinstall, applicationId and app data

Read this when the task is to **update/reinstall an app that is already on the phone**, to make an
app **publishable** (`applicationId`), or to **move the app's data** to a new package.
All facts below were verified on 2026-09-18 on the OnePlus 15R (Android 16) via `ssh win-ts` → `adb`.

## 1. What destroys data and what does not

| Command | Effect on installed app + its data |
|---|---|
| `adb install -r <apk>` (same package, same signing key) | **Update in place. Data preserved.** |
| `adb install -r <apk>` (same package, **different** key) | **Refused** (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`); installed app untouched |
| `adb install <apk>` (different package) | Installs **alongside**; the other app and its data untouched |
| `adb uninstall <package>` | **Destroyive** — this is the only one that erases app data |

Verified end-to-end: `adb install -r` → `Success`, and `md5sum` of `AppProfiles.xml` /
`ChatHistoryPrefs.xml` in `shared_prefs/` were **identical before and after**.

So: an install attempt can never damage the installed app. Say this when the user fears a reinstall,
and prove it with the md5 comparison rather than asserting it.

## 2. Signing keys are per machine

Each host has its own `~/.android/debug.keystore`. An APK built on host A **cannot** update an app
installed from host B — comparison:

```bash
keytool -list -v -keystore ~/.android/debug.keystore -storepass android -alias androiddebugkey | grep SHA256
apksigner verify --print-certs <apk>            # cert of the APK on the phone/disk
```

Consequence: build the APK on the machine whose debug key signed the installed app (here:
**Windows**). Do not try to "fix" a mismatch by uninstalling — that is the data-losing path.
The DGX *can* build natively for a **new** install (signed by the DGX key, so it installs alongside
instead of updating) — see `references/build-on-arm64.md`.

## 3. Back up app data before touching anything

Works on debuggable (debug) builds without root:

```bash
adb exec-out run-as <package> tar -cf - shared_prefs > backup.tar
```

On Windows redirect with `cmd /c "... > file"`. **Do not use PowerShell for this redirection** — it
mangles binary stream output.

## 4. Making the app publishable (`applicationId`)

Google Play **rejects** `com.example.*` as `applicationId`. Change it like this:

1. Change **only** `applicationId` in `app/build.gradle.kts`. Leave `namespace` alone — changing the
   namespace means moving every source file.
2. Grep the manifest for the placeholder form, e.g. `android:authorities="${applicationId}.provider"`:
   placeholders follow automatically. A **hardcoded** package string in the manifest would break, so
   check before building.
3. Update any instrumented test that asserts the old name
   (`assertEquals("com.example...", appContext.packageName)`).
4. Build and install: a different `applicationId` **installs alongside** — no conflict, no signature
   question. The old app stays installed and working, so the user can switch back.
5. Do this work in a **separate clone** so the user's working project is untouched.

## 5. Move the data to the new package

One phone-side pipe, no host-side binary handling and no temp files:

```bash
adb shell "run-as <OLD_PKG> tar -cf - shared_prefs | run-as <NEW_PKG> tar -xf -"
```

Then prove fidelity with `md5sum` on both sides — the hashes must be **equal per file**:

```bash
adb shell run-as <OLD_PKG> md5sum shared_prefs/AppProfiles.xml
adb shell run-as <NEW_PKG> md5sum shared_prefs/AppProfiles.xml
```

## 6. Launch and verify

The activity class keeps its namespace name, so the component differs from the package — launch by
package instead of naming the activity:

```bash
adb shell input keyevent 224                                     # wake display (OxygenOS)
adb shell monkey -p <applicationId> -c android.intent.category.LAUNCHER 1
adb shell dumpsys window | grep mCurrentFocus                    # expect <applicationId>/<namespace>.MainActivity
adb shell logcat -d -t 400 | grep -E "FATAL EXCEPTION|AndroidRuntime"
adb shell ps -A | grep <applicationId>                           # live process, no crash
```

Completion: **both** apps open (old and new), the new app shows no `FATAL EXCEPTION`, and the
migrated `md5sum`s match the originals.
