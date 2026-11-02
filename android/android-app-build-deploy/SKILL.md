---
name: "android-app-build-deploy"
description: "App/giochi Android da DGX al OnePlus: scaffold, build (Windows o nativo ARM64), install/reinstall con ADB (USB o Tailscale), cambio applicationId senza perdere dati. Trigger: 'fammi un'app', 'fammi un gioco', 'installala', 'reinstallala', 'rendila pubblicabile'."
---

# Android App Build & Deploy (DGX → Windows → OnePlus)

Crea, compila e installa un'app o un gioco Android sul telefono OnePlus 15R partendo dal DGX Spark. Usa questa skill quando l'utente chiede "fammi un'app", "fammi un gioco", "crea/installa un'app android", "installala sul telefono", o vuole una nuova app diversa da quelle già installate.

## Percorsi e prerequisiti (verificati 2026-09-04)

- Cartella progetti: `C:\Users\giova\AndroidStudioProjects\<NomeApp>` — raggiungibile via `ssh win-ts`. I mount SSHFS `win_disks` sono **stantii**: un path può risultare montato e restituire 0 voci, e `/home/jagones/win_disks/win_home` è **scrivibile ma è una cartella LOCALE del DGX**, non il PC — copiarci un file riesce e non arriva da nessuna parte (verificato 2026-09-18). Per i file di progetto non usare SSHFS: `scp <file> win-ts:C:/Users/giova/...` e **verifica l'hash sull'altro lato** (`Get-FileHash <path> -Algorithm MD5`).
- **Il vincolo sulla build è la chiave di firma, non la macchina.** Il DGX **sa** compilare nativamente (verificato 2026-09-18: `./gradlew clean assembleDebug` → `BUILD SUCCESSFUL` in 27 s, APK valido, poi installato e verificato sul telefono) — toolchain e caveat in `references/build-on-arm64.md`. Ma un APK compilato su un host **non può aggiornare in place** un'app installata da un altro host (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`): le app già sul telefono sono firmate dalla chiave del PC, quindi quelle vanno compilate su Windows; un'app **nuova** (o da affiancare/migrare) puoi compilarla sul DGX.
- Toolchain pronta: `~/Repositories/android-arm64-devkit-skill` (pubblico) — `scripts/setup-aapt2-arm64.sh` (architetture + override), `adb-connect.sh` (porta mai data per scontata), `adb-install-verify.sh` (install + focus + pid + logcat + screenshot, avvisa se lo screenshot è il framebuffer nero), `adb-disconnect.sh`.
- Progetto template provato e funzionante: **TapCounter** — da cui copiare wrapper Gradle, catalogo versioni e icone
- Build su Windows via SSH: `ssh win-ts` (si connette al PC Windows)
- JDK 17 Windows: `C:\Tools\jdk17\jdk-17.0.12+7`
- SDK Android: `C:\Users\giova\AppData\Local\Android\Sdk` → `local.properties`: `sdk.dir=C\:\\Users\\giova\\AppData\\Local\\Android\\Sdk`
- ADB da DGX: `/usr/bin/adb`, device `oneplus-15r:<porta>` via Tailscale

## Procedura

1. **Verifica e APRI il dispositivo (pre-flight OBBLIGATORIO, prima di ogni install)**. Un `adb devices` vuoto **non** significa "il telefono non c'è": sul DGX non esiste cavo USB, il trasporto Tailscale va **aperto**. Connetti DIRETTAMENTE, senza passare dal PC:
   ```bash
   adb devices -l
   # se vuoto, PRIMA cosa: connetti via Tailscale (MagicDNS) — la porta 5555 è esposta su tun0
   adb connect oneplus-15r:5555
   adb devices -l          # atteso: oneplus-15r:5555   device
   ```
   La `:5555` è la porta verificata attiva (2026-10-08). Il debug wireless di OnePlus può però cambiarla: se `:5555` non diventa `device`, scopri la porta LIVE dal lato Windows e riconnetti:
   ```bash
   ssh win-ts 'powershell -NoProfile -Command "& C:\Users\giova\AppData\Local\Android\Sdk\platform-tools\adb.exe devices -l"'
   adb connect oneplus-15r:<porta>
   ```
   Se ancora nessun `device`: `adb kill-server && adb start-server && adb connect oneplus-15r:5555` e **sveglia l'app Tailscale sul telefono** (deep sleep OxygenOS). ⛔ Mai concludere "collega il telefono via USB" né proseguire con il device disconnesso: sul DGX si usa **solo** Tailscale.

2. **Scaffold del progetto** (dentro `AndroidStudioProjects/<NomeApp>` con package `com.jagones.<nome>`):
   - crea `app/src/main/java/com/jagones/<nome>`, `app/src/main/res/{layout,values,drawable,mipmap-anydpi-v26}`, `gradle/wrapper`
   - copia da TapCounter: `gradlew`, `gradlew.bat`, `gradle/wrapper/*` (jar+properties), `gradle/libs.versions.toml`, `res/drawable/ic_launcher_foreground.xml`, `res/mipmap-anydpi-v26/ic_launcher.xml`
   - `settings.gradle.kts`: pluginManagement (google/mavenCentral/gradlePluginPortal), `rootProject.name = "<NomeApp>"`, `include(":app")`
   - `gradle.properties`: `org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8`, `android.useAndroidX=true`, `android.nonTransitiveRClass=true`

3. **`app/build.gradle.kts` — blocchi obbligatori** (se mancano, la build fallisce):
   - plugins: `alias(libs.plugins.android.application)` + `alias(libs.plugins.kotlin.android)`
   - `namespace` e `applicationId` unici (`com.jagones.<nome>`)
   - `compileSdk` **dipende dall'HOST** (non è un valore fisso): su **Windows** `36`; su **DGX/ARM64** — dove serve l'override `android.aapt2FromMavenOverride=/usr/lib/android-sdk/build-tools/debian/aapt2`, che è un aapt2 aarch64 `2.19-debian` — usa `compileSdk = 34`, perché quella aapt2 **non** legge `android-35/36/android.jar` (fallisce con "Entry offset ... outside Type boundaries"). Dettagli e prove in `references/build-on-arm64.md`. Poi `minSdk = 24`, `targetSdk = 34` (o `36` su Windows).
   - `compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }` **e** `kotlinOptions { jvmTarget = "17" }` (assenti → errore "Inconsistent JVM Target")
   - `buildTypes { getByName("debug") { isDebuggable = true } }`
   - verifica che `gradle/libs.versions.toml` esista (assente → "Unresolved reference 'android'")

4. **Wrapper di build `.cmd`** per progetto (`build_<nome>.cmd`), perché `set JAVA_HOME` inline via ssh NON funziona:
   ```cmd
   @echo off
   set JAVA_HOME=C:\Tools\jdk17\jdk-17.0.12+7
   set PATH=C:\Tools\jdk17\jdk-17.0.12+7\bin;%PATH%
   cd /d C:\Users\giova\AndroidStudioProjects\<NomeApp>
   call gradlew.bat --no-daemon assembleDebug
   ```

5. **Compila**: `ssh -o ConnectTimeout=8 win-ts 'cmd /c C:\Users\giova\AndroidStudioProjects\<NomeApp>\build_<nome>.cmd'` → attendi `BUILD SUCCESSFUL` (20–40s con cache calda).

6. **Installa**: prima **riconferma il device** (`adb devices -l` deve mostrare `device`; se è vuoto torna al passo 1 e fai `adb connect oneplus-15r:5555` — senza device l'install non parte). Poi `adb install -r <proj>/app/build/outputs/apk/debug/app-debug.apk` → `Success`. Per **aggiornare o reinstallare un'app già installata**, per **cambiare `applicationId`** o per **migrare i dati** dell'app, leggi prima `references/install-and-data-safety.md`. Per APK scaricati da internet (es. app di terze parti): verifica prima l'ABI — `adb shell getprop ro.product.cpu.abilist` → deve contenere `arm64-v8a`. Se l'install fallisce con `INSTALL_FAILED_NO_MATCHING_ABIS`, l'APK è per un'altra architettura (es. la build F-Droid di VLC è x86_64): scarica la build `arm64-v8a` dal mirror ufficiale dell'app (VLC: `https://get.videolan.org/vlc-android/last/VLC-Android-<versione>-arm64-v8a.apk`) e verifica lo SHA-256 con il file `.sha256` accanto prima di installare.

7. **Avvia e verifica**:
   - `adb shell am start -n com.jagones.<nome>/.MainActivity`
   - `adb shell dumpsys window | grep mCurrentFocus` → deve mostrare il tuo package
   - overlay (notifiche, animazione ricarica) possono oscurare il focus: in tal caso forza-stop, ri-lancia e ricontrolla
   - `adb exec-out screencap -p > tmp/check.png` e ispeziona con view_image; per prova funzionale fai screenshot prima/dopo un `input tap`

8. **Rispondi con**: cosa è stato installato, tempo build, prova di funzionamento (focus + screenshot prima/dopo interazione).

## Lezioni incorporate (recovery, non fallimenti)

- `gradle/libs.versions.toml` mancante → "Unresolved reference 'android'": copiarlo dal template prima di buildare.
- Blocchi JVM non allineati → "Inconsistent JVM target compatibility": includere SEMPRE `compileOptions` VERSION_17 e `kotlinOptions jvmTarget "17"`.
- `set JAVA_HOME` via ssh non si propaga al cmd remoto: usare un file `.cmd` sul server Windows.
- ID risorse: un typo tra layout (`@+id/x`) e Kotlin (`R.id.y`) rompe la compilazione — verificare che gli id coincidano.
- Porta ADB dinamica: leggerla ogni volta da `adb devices -l`, mai hardcodarla. E sul DGX il device va **connesso**: `adb connect oneplus-15r:5555` (poi `<porta>` se cambiata) — un `adb devices` vuoto significa "trasporto non aperto", NON "telefono assente".
- Un progetto nuovo creato a metà (interruzione) va ricreato pulito, non riparato pezzo per pezzo.
- `gradle.properties` può contenere `org.gradle.java.home=C\:/Program Files/Android/Android Studio/jbr`: valido sul PC di Giovanni, **rompe la build su qualsiasi altra macchina**. Su un'altra macchina non cancellarlo, fai override con `-Dorg.gradle.java.home=<jdk17>`.
- `gradlew` nel repo può non avere il bit eseguibile (clone/checkout): su Linux/CI `chmod +x gradlew`; su Windows si usa `gradlew.bat` e non serve.
- **Un build tutto `UP-TO-DATE` non prova niente**: se nessun task esegue, `aapt2` non è girato e l'APK è di prima. Per validare un toolchain serve `./gradlew clean assembleDebug` e `N actionable tasks: M executed` con **M > 0**.
- **L'adb su Windows risponde con CRLF**: un confronto esatto come `[ "$state" = device ]` fallisce su `device\r` e il telefono viene riportato **offline mentre è connesso** (verificato 2026-09-18). Normalizza sempre l'output: `adb ... | tr -d '\r'`.
