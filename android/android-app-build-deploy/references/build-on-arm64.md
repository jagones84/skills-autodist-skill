# Building Android on the ARM64 host (DGX Spark)

Read this when the build runs on the DGX itself — the app is not yet installed, it must be installed
alongside or migrated, or the Windows round trip is unavailable. Verified 2026-09-18 on the DGX Spark
(Ubuntu 24.04, aarch64) with AGP 8.5.2 / `compileSdk 34`.

## Why a plain build fails

Google ships `aapt2`, `aidl` and `zipalign` as **x86-64 only** — both the ones AGP downloads
(`aapt2-<version>-linux.jar` → `ELF 64-bit x86-64`) and the SDK build-tools (`34`/`35`/`36`). On
aarch64 they die with:

```
aapt2: cannot execute binary file: Exec format error
```

## The fix: point Gradle at Debian's native aarch64 binaries

Debian packages aarch64 builds of all of them (`android-libaapt`, `android-sdk-build-tools`,
`android-sdk-platform-tools`) in `/usr/lib/android-sdk/build-tools/debian/`:

```properties
# gradle.properties
android.aapt2FromMavenOverride=/usr/lib/android-sdk/build-tools/debian/aapt2
```

AGP flags the override as **experimental** (it prints a warning) but it works. `d8` and `apksigner`
are JVM wrappers, so they are architecture-independent already.

## Proving the build really used it — `clean`, or it proves nothing

A build where every task reports `UP-TO-DATE` never ran `aapt2`; the APK is left over from an earlier
run. Require the tasks to actually execute:

```bash
./gradlew clean assembleDebug
# require "N actionable tasks: M executed" with M > 0, and packageDebugResources / packageDebug listed
```

Without `clean`, `BUILD SUCCESSFUL` is not evidence of anything.

## Caveats (verified scope)

- Tested with **AGP 8.5.2**, `compileSdk 34`, no AIDL, no native code. Re-test after an AGP major bump.
- Debian's `aapt2` reports `2.19-debian` (2018) while AGP 8.x bundles a newer build: it passes the
  override here, but it is the first thing to suspect if a newer AGP misbehaves.
- **AIDL projects** additionally need `aidl` pointed at the Debian aarch64 binary (and explicit
  `zipalign` calls need `zipalign`) — both are x86-64 in Google's build-tools.

## Reusable toolkit

`~/Repositories/android-arm64-devkit` (public) — `scripts/setup-aapt2-arm64.sh` reports the
architecture of every `aapt2` it finds and installs what is missing; `--write-gradle-property <proj>`
adds the override to a project once. `scripts/adb-install-verify.sh` covers the install-and-prove
half on the device side.

When editing these scripts, keep the device argument as **separate argv entries** (`-s <serial> …`):
collapsed into a single string it still works over ssh — where the call is rebuilt into one command
line — and fails locally, so the bug hides until the transport changes (verified 2026-09-18, now
covered by `tests/run-tests.sh`).
