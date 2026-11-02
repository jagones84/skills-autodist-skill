---
name: android-install-launch-debug
description: Use when an Android app won't open after install.
---

# Android install → launch → verify

The workflow for taking an Android app from source to a *confirmed running*
on a real device over ADB. The failure mode this guards against: the build
succeeds and the APK installs, but the app crashes the instant you open it
or the screen shows nothing useful.

## Procedure

### Connecting to phone over WiFi (ADB TCP)

1. **Confirm phone is on same LAN**: `ping -c 2 <hostname>` or check `/etc/hosts`.
2. **Verify wireless debugging is active on phone**: Settings → Developer options → Wireless debugging → ensure toggle is ON. The phone's own UI shows the IP:port (or you can start it from Android Studio).
3. **Discover the ADB port** (NOT fixed at 5555):
   - Scan typical ranges: `nmap -p 5555-5559 192.168.1.X` for the phone's IP
   - Also try 34998-34999 and 44999 (Android's dynamic port range)
   - If phone is USB-connected to Windows PC, resolve port from there: `ssh win "adb devices -l"` shows `oneplus-15r:<port>` (note: Windows PATH may not include adb — use full path like `"C:\Program Files\Android\sdk\platform-tools\adb.exe" devices -l`)
4. **Connect**: `adb connect <IP>:<port>`
5. **Verify**: `adb devices -l` should show the device

### Standard workflow

1. **Build** from the project dir: `./gradlew assembleDebug` (check the real
exit code — don't pipe through `tail`, which swallows it).
2. **Confirm the launcher Activity class actually exists in source.** A
manifest pointing at `.MainActivity` that resolves to a class which does not
exist compiles and installs fine but crashes immediately at start. This is the
#1 silent cause of "installs, won't open".
3. **Install**: `adb -s $DEV install -r app/build/outputs/apk/debug/app-debug.apk`.
4. **Launch**: `adb -s $DEV shell am start -W -n <pkg>/.MainActivity` and
check it returns `Status: ok` / `Complete`.
5. **Verify it truly runs, not just reports ok**: `am start -W` can say
`Status: ok / Complete` even when the Activity crashed during instantiation.
Check three things together:
   - process alive: `adb shell "ps -A | grep <pkg>"` (not `pidof`, which may
     be absent)
   - no fatal crash: `adb logcat -d -b crash` — look for `FATAL EXCEPTION`
   - real focus: `adb shell dumpsys window | grep mCurrentFocus`

## Pitfalls

- **`@Composable fun App()` is NOT an entry-point Activity.** The manifest's
launcher `<activity android:name=".MainActivity">` requires a real class
`class MainActivity : ComponentActivity() { setContent { App() } }`.
A bare top-level Composable produces a successful build + install, then
`ClassNotFoundException: Didn't find class "<pkg>.MainActivity"` at
instantiation, because the class was never compiled into any dex.
- **Verify the class made it into the APK** by scanning the dex, not by
trusting the build. On aarch64 hosts (DGX Spark) the x86 SDK tools
(`aapt2`, `dexdump`) fail with "Exec format error" — instead open the APK
with Python's `zipfile` and regex the raw dex bytes for the full type
string `L<pkg>/<Class>;` (e.g. `Lcom/example/app/MainActivity;`). The
short name `MainActivity` appearing 100+ times is NOT proof the class is
defined; only the full `L...;` string is.
- **`@OptIn(ExperimentalMaterial3Api::class)` applies per-call-site.** Putting
it on the Activity class alone does NOT cover a separate `@Composable fun
App()` that calls experimental APIs (`TopAppBar` is one). Attach the
OptIn to every function that calls an experimental composable, or the
build fails with "This material API is experimental".
- **A local adb daemon restart silently drops all TCP-connected devices.**
After `adb kill-server`/daemon restart, devices go "not found" — re-run
`adb connect <host>:<port>`. The adb TCP port is NOT fixed (5555 is only a
default): the authoritative source for the live port is the device's own
persistent adb server. When the phone is meshed to another host that owns
that server (e.g. a Windows PC running its own adb), read the port from
there first — `ssh win "... adb devices -l"` shows `oneplus-15r:<port>`
as the transport. Never assume 5555; resolve the port, then connect.
- **A physically locked phone (keyguard/PIN) can't be unlocked by input.**
When `dumpsys display` shows `mScreenState=DOZE/DOZE_SUSPEND` and
`isKeyguardShowing=true`, the app may be `ResumedActivity` with the
process alive and no crash — but the screen stays on a black/lock/`
NotificationShade` window and screenshots come back cached/black. Input
events and swipes cannot clear a PIN/fingerprint gate. Stop looping and
ask the user to unlock the phone physically.
- `svc power stayon true` + `input keyevent 224` (WAKEUP) are cheap and
harmless; do them before launching so the screen stays awake.
- **Phone pingable ≠ ADB responding.** A device may be on LAN and pass ICMP
but refuse TCP on port 5555 if wireless debugging is off, or if the adb
server on the phone crashed. Always scan ports, don't just try 5555.
- **Windows adb PATH may not include platform-tools.** If `ssh win "adb
devices -l"` fails with '"adb" non è riconosciuto...', use the full path:
`"C:\Program Files\Android\sdk\platform-tools\adb.exe" devices -l`.
