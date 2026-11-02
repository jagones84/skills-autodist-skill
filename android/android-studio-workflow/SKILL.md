---
name: android-studio-workflow
description: Workflow completo per creare, editare, ricompilare e installare app Android da PC Windows al telefono (OnePlus 15R + altri). Usa Gradle 8.13.1, JDK 17, AGP 8.13.1, Kotlin 2.2.21. Installazione via ADB Tailscale 5G (senza USB).
---

# Android Studio Workflow — Windows PC → OnePlus 15R

Guida operativa per creare app Android da zero, modificarle, compilarle e installarle sul telefono **via 5G Tailscale** (zero USB).

---

## 0. Prerequisiti (verificati nel sistema corrente)

| Componente | Path |
|---|---|
| Android Studio | `C:\Program Files\Android\Android Studio1\` (JDK 21 bundled) |
| JDK 17 (build) | `C:\Tools\jdk17\jdk-17.0.12+7\` ← **QUESTO per Gradle** |
| Android SDK | `%LOCALAPPDATA%\Android\Sdk` (= `C:\Users\giova\AppData\Local\Android\Sdk`) |
| adb | `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe` |
| gradle wrapper jar | in ogni progetto: `<proj>\gradle\wrapper\gradle-wrapper.jar` |
| Tailscale IP telefono | `100.67.181.54:5555` (auto-magico-dns `oneplus-15r:5555`) |

**Regola aurea**: prima di OGNI build, settare `JAVA_HOME` al JDK 17 (NON quello di Android Studio, è JDK 21 e Gradle 8.13.1 vuole 17).

```powershell
$env:JAVA_HOME = "C:\Tools\jdk17\jdk-17.0.12+7"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
```

---

## 1. Percorsi chiave sul PC

| Tipo | Path |
|---|---|
| Progetti Android Studio | `C:\Users\giova\AndroidStudioProjects\<nome>\` |
| Progetti esistenti noti | `AI_Callable\` (325 MB, AI), `DaySurp\` (template ricco), `FinancialAwareness\` (v1.0.1), `MoneyCatcher\`, `SelfBuilder\`, `TRD\`, `Telemetry\`, `Test_app_maps\` |
| APK debug appena compilato | `<proj>\app\build\outputs\apk\debug\app-debug.apk` |
| Build log | `<proj>\build.log` (scriverlo sempre) |
| Skill in Trae | `C:\Users\giova\.trae\skills\<nome>\SKILL.md` |
| BACKUP progetti | `C:\Users\giova\AndroidStudioProjects\BACKUPS\` (tar/7z di vecchie versioni) |

---

## 2. Creare progetto Android da zero (minimo)

### 2.1 Struttura minima (solo file essenziali)

```
<ProjectRoot>/
├── build.gradle.kts                        # root, plugins apply false
├── settings.gradle.kts                     # rootProject.name + include(":app")
├── gradle.properties
├── gradlew  +  gradlew.bat                 # copia da DaySurp/
├── gradle/
│   ├── libs.versions.toml                  # AGP, Kotlin, deps versions
│   └── wrapper/
│       ├── gradle-wrapper.jar              # copia da DaySurp
│       └── gradle-wrapper.properties
├── local.properties                        # sdk.dir=...
└── app/
    ├── build.gradle.kts                    # namespace, deps
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/<package-path>/MainActivity.kt
        └── res/
            ├── layout/activity_main.xml
            ├── values/strings.xml
            ├── values/themes.xml
            ├── values-it/strings.xml       # italiano (opzionale)
            ├── drawable/ic_launcher_foreground.xml
            ├── drawable/ic_launcher_background.xml
            ├── mipmap-anydpi-v26/ic_launcher.xml + ic_launcher_round.xml
            ├── mipmap-mdpi/ic_launcher.png + ic_launcher_round.png
            └── xml/backup_rules.xml + data_extraction_rules.xml
```

### 2.2 Template `build.gradle.kts` (root)

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
}
```

### 2.3 Template `gradle/libs.versions.toml`

```toml
[versions]
agp = "8.13.1"
kotlin = "2.2.21"
coreKtx = "1.10.1"
appcompat = "1.6.1"
material = "1.10.0"

[libraries]
androidx-core-ktx = { group = "androidx.core", name = "core-ktx", version.ref = "coreKtx" }
androidx-appcompat = { group = "androidx.appcompat", name = "appcompat", version.ref = "appcompat" }
material = { group = "com.google.android.material", name = "material", version.ref = "material" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
```

### 2.4 Template `app/build.gradle.kts` (senza Compose)

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.example.<appname>"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.<appname>"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release { isMinifyEnabled = false }
        getByName("debug") { isDebuggable = true }   // <-- "getByName" NON "debug { }"!
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
}
```

### 2.5 Template `app/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.VIBRATE" />  <!-- se serve -->
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.<AppName>">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:label="@string/app_name"
            android:theme="@style/Theme.<AppName>">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

### 2.6 Esempio `app/src/main/java/com/example/<appname>/MainActivity.kt`

```kotlin
package com.example.<appname>

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        // ... logica app ...
    }
}
```

### 2.7 Esempio `app/src/main/res/layout/activity_main.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:gravity="center">

    <TextView
        android:id="@+id/myText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Hello"
        android:textSize="32sp" />

    <Button
        android:id="@+id/myButton"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Click" />
</LinearLayout>
```

### 2.8 `res/values/strings.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name"><AppName></string>
</resources>
```

### 2.9 `res/values/themes.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.<AppName>" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">#FF6B6B</item>
        <item name="colorOnPrimary">#FFFFFF</item>
    </style>
</resources>
```

### 2.10 Icone launcher (minimal)

- `res/drawable/ic_launcher_foreground.xml` (vector drawable, 108dp viewport)
- `res/drawable/ic_launcher_background.xml` (shape con `<solid>` di un colore)
- `res/mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
```

- `res/mipmap-mdpi/ic_launcher.png` + `ic_launcher_round.png` (placeholder 1x1 PNG per pre-26)

### 2.11 `res/xml/backup_rules.xml` + `data_extraction_rules.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<full-backup-content/>
```

### 2.12 `local.properties`

```properties
sdk.dir=C\:\Users\giova\AppData\Local\Android\Sdk
```

### 2.13 Copia file da template esistente (veloce)

```powershell
$src = "C:\Users\giova\AndroidStudioProjects\DaySurp"
$dst = "C:\Users\giova\AndroidStudioProjects\<AppName>"

# struttura vuota
$d = $dst
New-Item -ItemType Directory -Force -Path "$d\app\src\main\java\com\example\<pkg>"
New-Item -ItemType Directory -Force -Path "$d\app\src\main\res\layout"
New-Item -ItemType Directory -Force -Path "$d\app\src\main\res\values"
New-Item -ItemType Directory -Force -Path "$d\app\src\main\res\values-it"
New-Item -ItemType Directory -Force -Path "$d\app\src\main\res\drawable"
New-Item -ItemType Directory -Force -Path "$d\app\src\main\res\mipmap-anydpi-v26"
New-Item -ItemType Directory -Force -Path "$d\app\src\main\res\mipmap-mdpi"
New-Item -ItemType Directory -Force -Path "$d\app\src\main\res\xml"
New-Item -ItemType Directory -Force -Path "$d\gradle\wrapper"

# file da copiare (wrapper + gradlew)
Copy-Item "$src\gradlew" $d
Copy-Item "$src\gradlew.bat" $d
Copy-Item "$src\gradle\wrapper\gradle-wrapper.jar" "$d\gradle\wrapper\"
Copy-Item "$src\gradle\wrapper\gradle-wrapper.properties" "$d\gradle\wrapper\"
Copy-Item "$src\gradle.properties" $d
```

---

## 3. Build (Gradle)

```powershell
cd "C:\Users\giova\AndroidStudioProjects\<AppName>"
$env:JAVA_HOME = "C:\Tools\jdk17\jdk-17.0.12+7"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

.\gradlew.bat --no-daemon assembleDebug 2>&1 | Tee-Object -FilePath "$PWD\build.log"
```

**Tempi tipici**:
- Primo build (download deps): 2-5 minuti
- Build successivi: 20-60 secondi
- Output APK: `<proj>\app\build\outputs\apk\debug\app-debug.apk`

### 3.1 Errori comuni Gradle

| Errore | Causa | Fix |
|---|---|---|
| `JAVA_HOME is set to an invalid directory` | JDK 21 di Android Studio | usa JDK 17 (`C:\Tools\jdk17\jdk-17.0.12+7`) |
| `Cannot find Java matching languageVersion=11` | `jvmToolchain(11)` ma no JDK 11 | rimuovere, mettere `JavaVersion.VERSION_17` + `kotlinOptions { jvmTarget = "17" }` |
| `Unresolved reference: debug` in buildTypes | `debug { }` invece di `getByName("debug") { }` | correggere sintassi |
| `AndroidManifest.xml already specifies` dataExtractionRules mancante | `dataExtractionRules` referenziato ma file assente | creare `res/xml/data_extraction_rules.xml` |

---

## 4. Connessione ADB Tailscale (zero USB)

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

# Connessione (una volta per sessione; auto-reconnect in background dopo)
& $adb connect oneplus-15r:5555
# expected: connected to oneplus-15r:5555

# Verifica
& $adb devices
# deve mostrare: oneplus-15r:5555  device
```

**IMPORTANTE**: la porta 5555 è fissa (impostata una volta con `setprop service.adb.tcp.port 5555`). Non usare porte random 37xxx che cambiano ad ogni riattivazione di "Debug wireless" sul telefono.

Se la connessione cade (deep sleep OnePlus): aprire l'app Tailscale sul telefono, attendere 5s, rifare `adb connect`.

---

## 5. Installazione APK

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$apk = "C:\Users\giova\AndroidStudioProjects\<AppName>\app\build\outputs\apk\debug\app-debug.apk"

# Flag -r (reinstall) -d (downgrade) -t (allow test-only) -g (grant permissions)
& $adb -s oneplus-15r:5555 install -r -d -t -g $apk
# expected: Performing Streamed Install
#           Success
```

**Tempi tipici via 5G Tailscale**:
- APK 5 MB: 4 secondi
- APK 13 MB: 8 secondi
- APK 325 MB (AI_Callable): 18 secondi

### 5.1 Verifica installazione

```powershell
& $adb -s oneplus-15r:5555 shell "pm list packages | grep <pkg-name>"
& $adb -s oneplus-15r:5555 shell "dumpsys package <pkg-name> | grep -E 'versionName|firstInstallTime|lastUpdateTime'"
```

### 5.2 Trovare il package name reale

`aapt` legge l'APK:
```powershell
$aapt = "$env:LOCALAPPDATA\Android\Sdk\build-tools\34.0.0\aapt.exe"
& $aapt dump badging $apk | Select-String "package:|launchable" | Select-Object -First 5
```

Oppure guarda in `app/build.gradle.kts` → `defaultConfig.applicationId` (= `namespace`).

---

## 6. Lancio app + verifica runtime

```powershell
# Lancio
& $adb -s oneplus-15r:5555 shell "am start -n <pkg>/.MainActivity"

# Verifica che sia in foreground
& $adb -s oneplus-15r:5555 shell "dumpsys activity activities | grep -E 'topResumedActivity' | head -1"

# Screenshot
& $adb -s oneplus-15r:5555 exec-out screencap -p > "$env:USERPROFILE\Desktop\<appname>.png"

# Logcat (debug crash)
& $adb -s oneplus-15r:5555 logcat -d | Select-String "<pkg>|AndroidRuntime"

# Disinstalla
& $adb -s oneplus-15r:5555 uninstall <pkg>
```

---

## 7. Editare un progetto esistente

### 7.1 Modifica rapida a 1 file

1. Apri il file (IDE o python-local MCP)
2. `gradlew assembleDebug` (ricompila in 20-60s se non cambi gradle deps)
3. `adb install -r -d -t -g <apk>` (sovrascrive)
4. `adb shell am start -n <pkg>/.MainActivity`

### 7.2 Modifica profonda (cambio namespace, deps, manifest)

1. Modifica `app/build.gradle.kts` (namespace, deps)
2. Modifica `AndroidManifest.xml` se cambi activity/permessi
3. Rebuild → reinstall → test

### 7.3 Ricompilare progetto esistente che ha già APK

Se `<proj>\app\build\outputs\apk\debug\app-debug.apk` esiste, NON serve ricompilare. Vai direttamente a §5.

Se NON esiste o vuoi rebuildare:
```powershell
cd "<proj>"
# stesso blocco env di §3
.\gradlew.bat --no-daemon assembleDebug
```

---

## 8. Diagnosi problemi comuni

### 8.1 `adb devices` non mostra il telefono

```powershell
# 1. Verifica Tailscale attivo su PC
tailscale status

# 2. Riconnetti
& $adb disconnect
& $adb kill-server
& $adb connect oneplus-15r:5555

# 3. Se ancora nulla, apri app Tailscale sul telefono (5s per risvegliare)
```

### 8.2 APK installa ma app crasha all'avvio

```powershell
& $adb -s oneplus-15r:5555 logcat -c    # clear
& $adb -s oneplus-15r:5555 shell "am start -n <pkg>/.MainActivity"
Start-Sleep 3
& $adb -s oneplus-15r:5555 logcat -d | Select-String "AndroidRuntime|<pkg>" | Select-Object -First 50
```

### 8.3 Build lento o bloccato

```powershell
# Pulisci cache gradle
cd "<proj>"
.\gradlew.bat --stop
Remove-Item .gradle -Recurse -Force
Remove-Item app\build -Recurse -Force
.\gradlew.bat --no-daemon assembleDebug
```

### 8.4 Permessi negati a `WRITE_SECURE_SETTINGS` (per plugin Tasker/ADB)

OnePlus OxygenOS 16 blocca TUTTI i `pm grant` di permessi signed-level. L'unica soluzione è root (sblocco bootloader + Magisk). Tasker puro NON può riavviare adbd wireless senza root.

---

## 9. Note di sicurezza

- **NO secrets nei repo**: API key, password, certificati vanno in `.env.template` (template) + variabili ambiente o file fuori repo
- `.gitignore` per progetto Android: `/build`, `/.gradle`, `/local.properties`, `*.iml`, `/.idea`
- `local.properties` contiene `sdk.dir` (path assoluto personale, MAI committare)
- `gradle.properties` può contenere credenziali Maven private (gitignore se sì)

---

## 10. Workflow rapido (TL;DR per un agente futuro)

```powershell
# SETUP
$env:JAVA_HOME = "C:\Tools\jdk17\jdk-17.0.12+7"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"

# CONNESSIONE (una volta)
& $adb connect oneplus-15r:5555

# BUILD
cd "C:\Users\giova\AndroidStudioProjects\<AppName>"
.\gradlew.bat --no-daemon assembleDebug 2>&1 | Tee-Object build.log

# INSTALL + LAUNCH
$apk = "app\build\outputs\apk\debug\app-debug.apk"
& $adb -s oneplus-15r:5555 install -r -d -t -g $apk
& $adb -s oneplus-15r:5555 shell "am start -n <pkg>/.MainActivity"
```

Tempo end-to-end tipico: 2-3 minuti per rebuild+install+launch via 5G.

---

## 11. Esempio reale (SimplePomodoro, fatto in sessione 2026-09-03)

- Progetto: `C:\Users\giova\AndroidStudioProjects\SimplePomodoro\`
- Package: `com.example.pomodoro`
- 1 Activity Kotlin (timer Pomodoro 25/5 min, vibrazione)
- 1 layout XML lineare (TextView + 2 Button)
- Tema dark Material Components
- Build: 56s (primo), 10-20s (successivi)
- APK: 5.3 MB
- Install via 5G: 4.2 secondi
- Lancio: ok, `topResumedActivity = com.example.pomodoro/.MainActivity`

---

## 12. Riferimenti incrociati

- `android-tailscale-adb` skill → connessione ADB dettagliata
- `connect-to-dgx-spark` skill → quando serve DGX per build
- Progetti template ricchi: `DaySurp\` (Compose, MVVM), `FinancialAwareness\` (minimal)


---

## 13. Esempio completo incluso

La skill contiene un **progetto Android funzionante e compilabile** come riferimento didattico:

```
android-studio-workflow/
├── SKILL.md
└── examples/SimplePomodoro/      ← mirror del progetto reale
    ├── README.md                 ← panoramica didattica
    ├── build.gradle.kts, settings.gradle.kts, ...
    ├── gradle/wrapper/...        ← gradle-wrapper.jar funzionante
    └── app/                      ← MainActivity + layout + manifest
```

**Come usarlo**:
1. Apri la cartella `examples/SimplePomodoro/`
2. Leggi `README.md` per capire cosa fa
3. Copia i file come template per un nuovo progetto
4. Modifica `namespace`, `applicationId`, package e nome app
5. `gradlew assembleDebug` → `adb install`

**Caratteristiche dell'esempio**:
- 1 Activity Kotlin (timer Pomodoro 25/5 min con vibrazione)
- ~90 righe di logica
- 0 dipendenze pesanti (solo core-ktx, appcompat, material)
- APK risultante ~5 MB
- Compila in ~20s (clean) / 5-10s (incrementale)
- Install via 5G Tailscale in ~4 secondi
- Funziona testato su OnePlus 15R con OxygenOS 16

Per studiare un'app più complessa (Compose, ViewModel, Room, Navigation), vedi il progetto reale `C:\Users\giova\AndroidStudioProjects\DaySurp\`.
