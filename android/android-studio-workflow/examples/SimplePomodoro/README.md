# Esempio: SimplePomodoro

Progetto Android minimal dimostrativo (timer Pomodoro 25/5 min con vibrazione).
Mirror funzionante del progetto reale in `C:\Users\giova\AndroidStudioProjects\SimplePomodoro`.

## Caratteristiche didattiche

- **1 sola Activity** (no Fragment, no Navigation graph)
- **View classico** (no Compose) → build 10x più veloce
- **Niente dipendenze pesanti** (solo core-ktx, appcompat, material)
- **APK risultante: ~5 MB** (vs 325 MB di un progetto con modelli AI)
- **Nessuna icona raster** (solo adaptive vector)

## Cosa fa l'app

- Timer countdown 25 min (lavoro) → 5 min (pausa) → loop
- Vibrazione lunga al termine di ogni fase (3 pattern)
- Bottoni Start/Pausa + Reset
- Sfondo scuro, display monospace gigante

## Come compilare e installare

Vedi SKILL.md §10 (Workflow TL;DR) e §3 (Build).

```powershell
$env:JAVA_HOME = "C:\Tools\jdk17\jdk-17.0.12+7"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

cd "C:\Users\giova\AndroidStudioProjects\SimplePomodoro"
.\gradlew.bat --no-daemon assembleDebug
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" -s oneplus-15r:5555 install -r -d -t -g app\build\outputs\apk\debug\app-debug.apk
```

## Mappa file

| File | Scopo | Righe |
|---|---|---|
| `app/src/main/AndroidManifest.xml` | Entry point + permission VIBRATE | 22 |
| `app/src/main/java/.../MainActivity.kt` | Logica timer + vibrazione | 91 |
| `app/src/main/res/layout/activity_main.xml` | UI lineare con TextView + 2 Button | 47 |
| `app/src/main/res/values/themes.xml` | Tema Material dark | 7 |
| `app/src/main/res/values/strings.xml` | App name | 3 |
| `app/src/main/res/values-it/strings.xml` | Localization italiano | 3 |
| `app/build.gradle.kts` | AGP 8.13.1, Kotlin 2.2.21, Java 17 | 24 |
| `gradle/libs.versions.toml` | Versioni centralizzate | 12 |

## Lezione appresa (per clonare correggendo)

1. `buildTypes` in Kotlin DSL: serve `getByName("debug")` NON `debug { }`
2. `jvmToolchain(11)` blocca il build se JDK 11 non esiste → usa `JavaVersion.VERSION_17`
3. AGP 8+ marca debug come `testOnly` → `adb install` vuole `-t`
4. Backup rules files (`backup_rules.xml` + `data_extraction_rules.xml`) sono obbligatori se l'app referenzia `android:fullBackupContent` o `android:dataExtractionRules`
