---
name: android-game-dgx
description: "Crea giochi 2D per smartphone (Phaser 3 + Capacitor) e installali sul OnePlus 15R dal DGX Spark via Tailscale senza Windows. Use per sviluppo giochi Android dal DGX."
---

# ANDROID GAME DGX — Crea giochi 2D (Phaser + Capacitor) direttamente dal DGX Spark

Skill per creare **giochi per smartphone** (2D platformer, puzzle, arcade, **ALife/GA evolutivi**) usando **Phaser 3** come game engine e **Capacitor** come wrapper Android. Tutto compilato e installato sul OnePlus 15R via Tailscale, **senza Windows**.

**Differenza da `android-dgx-build`**: quella crea app native Kotlin/Java. Questa crea **giochi 2D in JavaScript/Phaser** dentro WebView Android.

**Stack**: Node 24 + Phaser 3.80 + Capacitor 6 + AGP (gradle wrapper 8.2.1) + aapt2 Debian (L12).

**Verificato funzionante**:
- 2026-09-04 — PixelDash Platformer: build 1m46s + install 5s + launch + screenshot con Score: 10.
- 2026-09-04 — Troglets ALife+GA: build 10s (incrementale) + install OK + screenshot Gen=24, Pop=80, AvgDNA visibile.

---

## TRIGGER (quando invocarmi)

- "crea un gioco", "fai un platformer", "fai snake/puzzle/arcade per android"
- "build game apk", "deploy gioco su oneplus", "lancia gioco sul cellulare"
- "fai un gioco con phaser", "usa capacitor per wrapping android"
- "rigenera PixelDash", "modifica il platformer"
- "crea un gioco con evoluzione", "fai un'alife", "crea Troglets", "crea creature che evolvono", "fai un tamagotchi evolutivo", "fai un ecosistema simulato", "crea un gioco genetico"
- Qualsiasi task dove serve un gioco 2D distribuito come APK

**NON usare** se:
- Serve un'app nativa Kotlin/Java (→ `android-dgx-build`)
- Serve grafica 3D avanzata (→ prendere in considerazione Godot 4 in futuro)
- Serve release firmata Play Store (→ solo debug APK qui)
- Serve un **LLM on-device** che gira nell'APK (ExecuTorch/llama.cpp) → troppo pesante per WebView, richiede nativo
- Serve un vero **Reinforcement Learning** con training → meglio Godot+RL su host, troppo complesso qui

---

## ANTI-PATTERN (cose che sembrano furbe ma ROMPONO tutto)

- ❌ Usare `adb` da `$ANDROID_HOME/platform-tools/adb` (= Google x86_64, NON gira su aarch64) → usare `/usr/bin/adb` (Debian ARM64, L16)
- ❌ Cambiare `compileSdk` a 35/36 in `android/variables.gradle` → aapt2 Debian 29.0.3 non legge platform 35/36 (L12b)
- ❌ Aggiungere dipendenze C++/NDK in `android/app/build.gradle` → servono toolchain NDK che non abbiamo
- ❌ Chiamare `node` da shell SSH senza `bash -lc` → nvm è caricato DOPO `case $-` (L13)
- ❌ Usare Phaser via CDN (`<script src="https://cdn.phaser.io">`) → offline non funziona, copia locale in `www/js/`
- ❌ Inventare package type `applicationId` con caratteri strani (solo `com.example.x` o `com.jagones.x` con lettere)
- ❌ Skippare `npx cap copy android` dopo aver modificato `www/` → APK contiene vecchia versione
- ❌ Settare `compileSdk = 36` in `app/build.gradle.kts` di HelloDGX pensando "più alto meglio è" → errore aapt2
- ❌ Lanciare build senza `bash -lc` se serve `node` → `node: command not found`
- ❌ Dimenticare `aapt2FromMavenOverride` dopo `cap add android` → build fallisce con `aapt2: Syntax error`
- ❌ "Ho finito, l'ho lanciata" senza screenshot di verifica → "l'ho fatto" non è verifica
- ❌ **In un ALife game, NON mettere `MAX_POP` illimitato** → centinaia di cerchi Phaser = WebView lagga (L20)
- ❌ **NON dimenticare il re-seed se la popolazione si estingue** → schermo nero statico, "non funziona nulla" (L20)
- ❌ **NON usare reti neurali o PyTorch in Phaser WebView** → bundle >50 MB, training non possibile (vedi §11)
- ❌ **NON lasciare i geni del DNA liberi di crescere** → numeri esplodono in poche generazioni (L19)

---

## 1. Prerequisiti (gli stessi di `android-dgx-build` + Node via login shell)

| Componente | Verifica | Atteso |
|------------|----------|--------|
| JDK 17 | `ssh dgx 'echo $JAVA_HOME && $JAVA_HOME/bin/java -version'` | `/usr/lib/jvm/java-17-openjdk-arm64` + `openjdk 17.0.x` |
| aapt2 Debian ARM64 | `ssh dgx 'file /usr/lib/android-sdk/build-tools/29.0.3/aapt2'` | `ELF 64-bit LSB executable, ARM aarch64` |
| adb Debian ARM64 | `ssh dgx 'file /usr/bin/adb'` | symlink a `/usr/lib/android-sdk/platform-tools/adb` + `ELF 64-bit ARM` |
| node + npm | `ssh dgx 'bash -lc "node --version && npm --version"'` | v24.x + 11.x (login shell per nvm!) |
| Tailscale | `ssh dgx 'tailscale status \| grep oneplus'` | vede `oneplus-15r` |
| Telefono debug wireless ON | popup "Debug wireless" sul telefono | mostra porta tipo `41271` |

**⚠️ IMPORTANTE**: `node` richiede **login shell** (`bash -lc 'cmd'`) perché nvm
è caricato DOPO il `case $-` check in `.bashrc` (L13). Stesso pattern: ogni
comando che usa `node`/`npm`/`npx` DEVE essere wrappato in `bash -lc`.

---

## 2. Percorsi canonici

| Cosa | Path |
|------|------|
| Working root giochi | `/home/jagones/Repositories/games-dev/` |
| └─ Progetti | `/home/jagones/Repositories/games-dev/projects/<NomeGame>/` |
| └─ Script canonici | `/home/jagones/Repositories/games-dev/scripts/` |
| └─ Log build | `/home/jagones/Repositories/games-dev/logs/` |
| └─ Esempi reali | `games-dev/projects/PixelDash/` (platformer) + `games-dev/projects/Troglets/` (ALife) |
| Sorgenti web (input Phaser) | `<proj>/www/{index.html,js/game.js,css/style.css,js/phaser.min.js,assets/}` |
| Sorgenti web copiati in Android | `<proj>/android/app/src/main/assets/public/` |
| Wrapper Android (generato da Capacitor) | `<proj>/android/` |
| Output APK | `<proj>/android/app/build/outputs/apk/debug/app-debug.apk` |
| Script `create_game.sh` | `games-dev/scripts/create_game.sh` |
| Script `build_and_install.sh` | `games-dev/scripts/build_and_install.sh` |

Env vars (in `.bashrc` managed block `>>> android-dev >>>`, vedi `android-dgx-build` §1):
- `ANDROID_HOME=/home/jagones/Repositories/android-dev/android-sdk`
- `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64`
- `PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$GRADLE_HOME/bin:$JAVA_HOME/bin:$PATH`

---

## 3. WORKFLOW CANONICO (3 step, sempre uguale)

### STEP 1 — Creare progetto (una volta per nuovo gioco)

```bash
ssh dgx 'bash /home/jagones/Repositories/games-dev/scripts/create_game.sh <NomeGame> com.jagones.<nomegame>'
```

Lo script:
- Crea struttura `www/{js,css,assets}/` + `package.json` + template `game.js` (mostra "$NAME Ready!")
- `npm install` (Phaser + Capacitor, ~14s)
- Copia `node_modules/phaser/dist/phaser.min.js` in `www/js/`
- `npx cap init <Nome> <pkg> --web-dir=www`
- `npx cap add android` (genera wrapper Android, ~100ms)
- Aggiunge automaticamente `aapt2FromMavenOverride` a `android/gradle.properties` (L12)

**Output**: `games-dev/projects/<NomeGame>/` pronto per ricevere il codice Phaser.

### STEP 2 — Scrivere/modificare il gioco (LLM-friendly!)

Modifica `<proj>/www/js/game.js` con la logica del gioco in Phaser 3.

**Convenzioni LLM-friendly** (per partire veloce):
- USA una sola `class extends Phaser.Scene` con `preload()` + `create()` + `update()`
- Texture procedurali con `this.add.graphics().generateTexture(key, w, h)` → niente asset esterni = niente licensing
- Controlli: `this.cursors` (tastiera) + touch zones per mobile (vedi esempio PixelDash)
- Gravità: `this.physics.world.gravity.y = 800` + `arcade` physics
- Camera: `this.cameras.main.startFollow(this.player)` per platformer
- **ALife/GA**: vedi §8b per template `DNA` + `Creature` + `World`

**Riferimenti completi**:
- Platformer: `games-dev/projects/PixelDash/www/js/game.js` (~250 righe)
- ALife/GA: `games-dev/projects/Troglets/www/js/game.js` (~280 righe)

Dopo aver modificato `www/`, copia in Android:
```bash
ssh dgx 'bash -lc "cd /home/jagones/Repositories/games-dev/projects/<NomeGame> && npx cap copy android"'
```

### STEP 3 — Build + install + launch (un solo comando)

```bash
# Scrivi la porta su /tmp/adb_port (per non ripassarla ogni volta)
ssh dgx 'echo 41271 > /tmp/adb_port'

# Build + install + launch + verify
ssh dgx 'bash /home/jagones/Repositories/games-dev/scripts/build_and_install.sh <NomeGame>'

# Oppure con porta esplicita:
ssh dgx 'bash /home/jagones/Repositories/games-dev/scripts/build_and_install.sh <NomeGame> 41271'
```

Lo script `build_and_install.sh`:
- `cd android && ./gradlew assembleDebug` (primo: ~100s download gradle 8.2.1; successivi: 30-60s)
- `adb connect oneplus-15r:<PORT>` + `install -r -d -t -g` (4-10s)
- `adb shell am start -n <pkg>/.MainActivity` (1s)
- `adb exec-out screencap -p` → screenshot in `games-dev/logs/launch-<Nome>-<TS>.png`
- `dumpsys activity activities` per verificare foreground
- `logcat` per verificare no crashes (esce con 2 se ci sono crash)

**Output finale**:
```
APK=/home/jagones/Repositories/games-dev/projects/<Nome>/android/app/build/outputs/apk/debug/app-debug.apk
PKG=com.jagones.<nome>
PORT=41271
[verify] No crashes. SUCCESS.
```

---

## 4. PRE-FLIGHT CHECK (esegui prima di iniziare)

```bash
# P1: login shell ha node
ssh dgx 'bash -lc "node --version && npm --version"'
# ATTESO: v24.x.x \n 11.x.x

# P2: aapt2 Debian presente
ssh dgx 'file /usr/lib/android-sdk/build-tools/29.0.3/aapt2 | grep aarch64'
# ATTESO: ELF 64-bit LSB executable, ARM aarch64

# P3: adb Debian (NON Google)
ssh dgx 'file /usr/bin/adb | grep -E "aarch64|symbolic link"'
# ATTESO: symbolic link to ../lib/android-sdk/platform-tools/adb (Debian)

# P4: gradle.properties del progetto ha override
ssh dgx 'grep aapt2FromMavenOverride /home/jagones/Repositories/games-dev/projects/<Nome>/android/gradle.properties'
# ATTESO: android.aapt2FromMavenOverride=/usr/lib/android-sdk/build-tools/29.0.3/aapt2

# P5: porta telefono
ssh dgx 'adb connect oneplus-15r:41271 2>&1; adb devices | grep oneplus'
# ATTESO: oneplus-15r:41271  device
```

Se QUALSIASI check fallisce → NON procedere. Vedi §7 troubleshooting.

---

## 5. LESSONS INTEGRATE

### L12 — aapt2 ARM64 (già documentata in `android-dgx-build`)
Google distribuisce `build-tools/<v>/aapt2` SOLO x86_64. Su DGX (aarch64) NON gira. **Fix**: `android.aapt2FromMavenOverride=/usr/lib/android-sdk/build-tools/29.0.3/aapt2` in `android/gradle.properties`. **Lo script `create_game.sh` lo applica automaticamente.**

### L12b — compileSdk ≤ 34
aapt2 29.0.3 (Debian) legge solo `android.jar` di platforms ≤ 34. **Capacitor 6 imposta già `compileSdk = 34, targetSdk = 34` di default** → OK out-of-the-box, NON toccare `android/variables.gradle`.

### L13 — login shell per node (CRITICA per Phaser/Capacitor)
nvm è caricato in `~/.bashrc` DOPO il `case $-` check. Shell SSH non-interattive (`ssh dgx 'cmd'`) escono prima. **Workaround**: usare `bash -lc 'cmd'` oppure `bash -c 'source ~/.nvm/nvm.sh && cmd'`. **Lo script `build_and_install.sh` usa la prima variante.**

### L14 — porta ADB Tailscale DINAMICA
OnePlus 15R espone porte random 37000-37999 dal popup "Debug wireless", NON la 5555. Porta cambia ad ogni riavvio. **Workaround**: leggi la porta dal popup, salvala in `/tmp/adb_port` con `echo 41271 > /tmp/adb_port`, oppure passala al volo come 2° argomento.

### L16 — adb Google x86_64 (NUOVA, scoperta oggi)
`$ANDROID_HOME/platform-tools/adb` (scaricato da Google) è x86_64, NON gira su aarch64 DGX. **Fix**: usa `/usr/bin/adb` (Debian package `android-sdk-platform-tools`, ARM64 nativo). `which adb` deve ritornare `/usr/bin/adb`, NON il path Google. **Lo script `build_and_install.sh` chiama `adb` senza path → usa il primo in PATH, che è quello Debian.**

### L17 — Capacitor 6 default OK per compileSdk (NUOVA, scoperta oggi)
Capacitor 6 imposta già `compileSdkVersion = 34, targetSdkVersion = 34` in `android/variables.gradle`. **NON serve patcharlo**, è già compatibile con aapt2 Debian 29.0.3.

### L18 — `npx cap copy` DOPO modifiche a www/
Se modifichi `www/js/game.js` o qualsiasi file in `www/`, DEVI rieseguire `npx cap copy android` prima di `assembleDebug`, altrimenti l'APK contiene la vecchia versione. **Lo script `build_and_install.sh` NON lo fa automaticamente** (è una scelta: build rapido senza risincronizzare) → se hai modificato www/, esegui prima `npx cap copy android`.

### L19 — DNA normalizzato in [0,1] (NUOVA per ALife, 2026-09-04)
**Errore classico** in un gioco ALife/GA: lasciare i geni del DNA come numeri float liberi, applicare mutazione additiva `(g + (rand-0.5)*strength)`. Dopo ~50 generazioni i geni sono a 1e6 o a -500 → la popolazione degenera. **Fix canonico**:
- Ogni gene è un float in `[0,1]` (rappresenta una % sul tratto).
- I metodi `dna.speed()`, `dna.size()`, ... **mappano** `[0,1]` → range utile (`0.5 + gene*2.5`, `4 + gene*8`, `30 + gene*120`, ...).
- Mutazione: `Math.max(0, Math.min(1, g + delta))` — clamp, NON somma libera.
- Crossover: punto singolo `i < cut ? d1.genes[i] : d2.genes[i]`.
- Questo garantisce **stabilità per migliaia di generazioni** e che la pressione selettiva (energia/cibo/morte) sia l'unica forza evolutiva.

### L20 — gestione estinzione e cap popolazione (NUOVA per ALife, 2026-09-04)
**Due problemi opposti ma entrambi letali** in un ALife game:
1. **Estinzione totale** (pop=0 dopo catastrofe): schermo statico, l'utente pensa "non funziona". **Fix obbligatorio**: se `pop === 0` e gen > 5, fai **re-seed automatico** con N creature random `new DNA()` e incrementa `gen` (oppure reimposta gen=0).
2. **Popolazione esplosiva** (decine di figli per round): WebView si impasta a 100+ cerchi, frame rate crolla. **Fix obbligatorio**: `MAX_POP` hard cap (es. 80). Quando `creatures.length >= MAX_POP`, nuove nascite = `creatures.shift()` (muore il più vecchio) OPPURE la riproduzione fallisce finché qualcuno non muore di fame/età.
3. **Statistiche ogni N frame** (es. 60): `text.setText(\`Gen: ${gen}  Pop: ${pop}  Food: ${food}\`)` — NON ogni frame, altrimenti il GC rallenta.
4. **Cleanup sprites**: `this.gfx.destroy()` + `this.energyBar.destroy()` quando una creatura muore — Phaser NON libera memoria automaticamente.

### L21 — Forward pass identico Python↔JS (NUOVA per NeuralCreatures, 2026-09-04)
Dopo aver addestrato una MLP off-line, **validarla in Python con numpy** PRIMA di integrarla in JS. Stessa formula, stesso ordine di operazioni, stesse funzioni di attivazione (ReLU + tanh). Output deve essere in `[-1, 1]` per le azioni. Questo vincolo "stesso forward pass" evita drift comportamento quando l'app mobile produce azioni diverse dal training. Vedi `games-dev/training/validate_brain.py`.

### L22 — MatMul 4D vettorizzato (NUOVA per training ALife, 2026-09-04)
Per fitness evaluation batch (1000 creature × forward pass), `np.einsum('ijk,ik->ij', W, obs)` **fallisce** su numpy 2.5 con `ValueError: operands could not be broadcast together` quando W=(N,6,8) e obs=(N,6). **Fix canonico**: `np.matmul(W.transpose(0, 2, 1), obs[:, :, None]).squeeze(-1)`. Sfrutta BLAS, vettorizzato vero, ~0.046ms/batch su DGX = 21M inferenze/sec. Loop Python `for c in creatures: brain_forward(W[c], obs[c])` è 100x più lento e inutile per batch uniformi.

### L23 — npx cap copy per subdir nuove (NUOVA per NeuralCreatures, 2026-09-04)
Se aggiungi una nuova cartella in `www/` (es. `www/models/brain.json`), DEVI rieseguire `npx cap copy android` — `capacitor.config.json` si basa sulla snapshot di `www/` al momento del copy, non scansiona ricorsivamente. `build_and_install.sh` NON lo fa per scelta build rapido. **Sequenza canonica**: modifica `www/` → `npx cap copy android` → `build_and_install.sh`.


---

## 6. TROUBLESHOOTING (sintomo → causa → fix)

| # | Sintomo | Causa | Fix |
|---|---------|-------|-----|
| T1 | `node: command not found` da `ssh dgx` | nvm non caricato (L13) | usa `bash -lc 'cmd'` oppure `source ~/.nvm/nvm.sh` |
| T2 | `aapt2: 1: Syntax error: word unexpected` | aapt2 Google x86_64 usato (L12) | verifica `gradle.properties` abbia `aapt2FromMavenOverride`; reinstalla: `bash create_game.sh` |
| T3 | `RES_TABLE_TYPE_TYPE entry offsets overlap` | `compileSdk` 35/36 in `variables.gradle` (L12b) | ripristina `compileSdkVersion = 34` in `android/variables.gradle` |
| T4 | `cannot execute binary file: Exec format error` su adb | adb Google x86_64 in PATH (L16) | usa `/usr/bin/adb` esplicitamente, o `apt install android-sdk-platform-tools` se manca |
| T5 | `adb: no devices/emulators found` | Tailscale disconnesso o porta cambiata | apri Tailscale sul telefono, rileggi porta dal popup, `echo PORT > /tmp/adb_port` |
| T6 | `failed to install: INSTALL_FAILED_USER_RESTRICTED` | telefono blocca install da ADB | Impostazioni → App → Speciale → Installa app sconosciute → consenti per la sorgente |
| T7 | `BUILD FAILED` su `npm install phaser` | npm non in PATH | `bash -lc 'which npm'`; reinstalla nodejs se manca |
| T8 | `Module not found: phaser` in game.js | phaser.min.js non copiato in www/js/ | `cp node_modules/phaser/dist/phaser.min.js www/js/` |
| T9 | `Webpage not available` nell'app | `www/index.html` non trovato | `npx cap copy android` |
| T10 | APK vecchio dopo modifica a `www/js/game.js` | `npx cap copy` non eseguito (L18) | `bash -lc "cd <proj> && npx cap copy android"` poi rebuild |
| T11 | `gradle: Permission denied` | eseguibile mancante | `ssh dgx "chmod +x /home/jagones/Repositories/games-dev/projects/<Nome>/android/gradlew"` |
| T12 | `topResumedActivity` non mostra il package | app è andata in crash | `adb logcat -d -t 300 \| grep -E "FATAL\|chromium" \| head -50` |
| T13 | Schermo nero dopo launch | WebView non ha caricato assets | controlla `android/app/src/main/assets/public/` esista; `npx cap copy android` |
| T14 | `Cannot find aapt2` warning ignorato + crash aapt2 | `aapt2FromMavenOverride` non letto | ricrea il progetto con `create_game.sh` (lo applica) o aggiungi manualmente |
| T15 | `gradle 8.2.1` download lentissimo | primo download ~80MB | attendi 60-90s, è one-time per progetto |
| T16 | ALife game: popolazione si estingue e schermo resta vuoto | niente re-seed (L20) | aggiungi `if (pop === 0) { reseedN(20); gen++; }` in update() |
| T17 | ALife game: WebView lagga con 100+ creature | niente cap popolazione (L20) | `if (creatures.length >= MAX_POP) return;` prima di `reproduce()` |
| T18 | ALife game: geni degenerano (velocità=NaN, size=infinito) | geni non normalizzati (L19) | clamp `Math.max(0, Math.min(1, g + delta))` su ogni gene mutato |

---

## 7. COMANDI ONE-LINER (TL;DR per agente futuro)

```bash
# SETUP (esegui 1 volta)
# Già fatto in hello-dgx build. Verifica con §4 PRE-FLIGHT.

# CREA NUOVO GIOCO
ssh dgx 'bash /home/jagones/Repositories/games-dev/scripts/create_game.sh MyGame com.jagones.mygame'
# → crea struttura, npm install, cap init+add android, aapt2 override

# MODIFICA GIOCO (LLM scrive/modifica www/js/game.js)
# Quindi:
ssh dgx 'bash -lc "cd /home/jagones/Repositories/games-dev/projects/MyGame && npx cap copy android"'

# BUILD + INSTALL + LAUNCH + VERIFY (tutto in uno)
ssh dgx 'echo 41271 > /tmp/adb_port'  # una volta per sessione
ssh dgx 'bash /home/jagones/Repositories/games-dev/scripts/build_and_install.sh MyGame'

# VERIFY FOREGROUND
ssh dgx 'adb -s oneplus-15r:41271 shell dumpsys activity activities | grep topResumedActivity | head -1'

# LOGCAT LIVE
ssh dgx 'adb -s oneplus-15r:41271 logcat -c && adb -s oneplus-15r:41271 logcat | grep -E "chromium|FATAL"'
```

**Tempo end-to-end tipico**:
- Crea progetto: 30-60s (npm install = 14s + cap setup)
- Modifica + cap copy: 1-2s
- Build (primo): 90-180s (download gradle 8.2.1 ~80s)
- Build (successivi): 20-60s
- Install + launch + verify: 5-10s

---

## 8. ESEMPIO REALE — PixelDash Platformer (fatto 2026-09-04)

- **Progetto**: `/home/jagones/Repositories/games-dev/projects/PixelDash/`
- **Package**: `com.jagones.pixeldash`
- **Gioco**: 2D Platformer con player pixel-art (rosso), monete (gialle), nemici (viola), 9 piattaforme, 25 monete, 5 nemici, livello 3 schermi di larghezza, goal flag
- **Controlli**: tastiera (frecce) + touch zones (3 aree: sinistra/destra/jump)
- **Texture**: 100% procedurali via `add.graphics().generateTexture()` (nessun asset esterno, niente licensing)
- **Build**: 1m 46s (primo, con download gradle 8.2.1)
- **APK**: 4.1 MB
- **Install**: ~5s
- **Launch**: ok, screenshot mostra "Score: 10" (moneta raccolta automaticamente dal player che spawna vicino)
- **Porta usata**: 41271 (dinamica, letta dal popup)

**File principale** (estratto da `www/js/game.js`):
```javascript
class GameScene extends Phaser.Scene {
  create() {
    // ... ground, platforms, player, coins, enemies ...
    this.player = this.physics.add.sprite(100, height - 100, 'player');
    this.cursors = this.input.keyboard.createCursorKeys();
    // touch zones: this.add.rectangle(...).setInteractive().on('pointerdown', ...)
  }
  update() {
    if (this.cursors.left.isDown) this.player.setVelocityX(-220);
    else if (this.cursors.right.isDown) this.player.setVelocityX(220);
    if (this.cursors.up.isDown && this.player.body.touching.down) this.player.setVelocityY(-480);
  }
}
new Phaser.Game({ type: Phaser.AUTO, parent: 'game-container', width: window.innerWidth, height: window.innerHeight, physics: { default: 'arcade', arcade: { gravity: { y: 800 } } }, scene: [BootScene, GameScene] });
```

**Vedi file completo**: `/home/jagones/Repositories/games-dev/projects/PixelDash/www/js/game.js` (~250 righe, commentato).

---

## 8b. PATTERN ALIFE / GENETIC ALGORITHM — Template riusabile (Troglets, fatto 2026-09-04)

Per implementare un gioco "creature che evolvono" (Troglets, Tamagotchi evolutivi, ecosistema simulato) **senza dipendenze esterne**, riusando Phaser + Capacitor.

### Architettura minima (4 classi)

```javascript
// 1. DNA = vettore di geni in [0,1] (L19)
class DNA {
  constructor(genes = null) {
    this.genes = genes || Array.from({length: 6}, () => Math.random());
    // 6 geni: [speed, size, vision, hungerRate, aggression, hue]
  }
  static crossover(d1, d2) {
    const cut = Math.floor(Math.random() * d1.genes.length);
    return new DNA(d1.genes.map((g, i) => i < cut ? g : d2.genes[i]));
  }
  mutate(rate = 0.1, strength = 0.15) {
    return new DNA(this.genes.map(g =>
      Math.random() < rate
        ? Math.max(0, Math.min(1, g + (Math.random() - 0.5) * strength * 2))  // CLAMP (L19)
        : g
    ));
  }
  // Mappature [0,1] → range utile:
  speed()      { return 0.5 + this.genes[0] * 2.5; }
  size()       { return 4   + this.genes[1] * 8;   }
  vision()     { return 30  + this.genes[2] * 120; }
  hungerRate() { return 0.05 + this.genes[3] * 0.25; }
  aggression() { return this.genes[4]; }
  hue()        { return Math.floor(this.genes[5] * 360); }
}

// 2. Creature = ha DNA + energia + età
class Creature {
  constructor(scene, x, y, dna = null) {
    this.scene = scene; this.dna = dna || new DNA();
    this.x = x; this.y = y; this.vx = 0; this.vy = 0;
    this.energy = 100; this.age = 0; this.alive = true;
    const r = this.dna.size();
    this.gfx = scene.add.circle(x, y, r,
      Phaser.Display.Color.HSLToColor(this.dna.hue()/360, 0.8, 0.5).color);
    this.energyBar = scene.add.rectangle(x, y - r - 4, r*2, 2, 0x00ff00);
  }
  update(dt, food) {
    // 1. cerca cibo più vicino nel raggio di visione
    // 2. muovi verso di esso (seek) o wander random
    // 3. se abbastanza vicino (<5px) → eat, energy += ENERGY_FROM_FOOD
    // 4. energy -= hungerRate() * dt; age += 1
    // 5. if (energy <= 0 || age > MAX_AGE) die() → destroy() sprites (L20.4)
  }
  canReproduce() { return this.energy >= 150; }
  reproduce(partner) {
    const childDna = DNA.crossover(this.dna, partner.dna).mutate();
    this.energy -= 80; partner.energy -= 40;
    return new Creature(this.scene, this.x, this.y, childDna);
  }
  die() {
    this.alive = false;
    this.gfx.destroy(); this.energyBar.destroy();  // L20.4 cleanup
  }
}

// 3. Food = cibo statico che spawna random
class Food {
  constructor(scene, x, y) {
    this.x = x; this.y = y; this.alive = true;
    this.gfx = scene.add.circle(x, y, 3, 0x00ff88);
  }
  destroy() { this.alive = false; this.gfx.destroy(); }
}

// 4. Scene = loop genetico
class ALifeScene extends Phaser.Scene {
  create() {
    this.creatures = []; this.food = [];
    this.gen = 0; this.frame = 0;
    this.MAX_POP = 80; this.MAX_FOOD = 120;
    // init: 30 creature random + 80 food
    for (let i = 0; i < 30; i++) this.creatures.push(new Creature(this, ...));
    for (let i = 0; i < 80; i++) this.food.push(new Food(this, ...));
  }
  update(_, dt) {
    this.frame++;
    // 1. update creatures
    this.creatures.forEach(c => c.update(dt, this.food));
    // 2. riproduzione sessuale (vicini < 30px, energia > 150, MAX_POP check, L20.2)
    for (let i = 0; i < this.creatures.length; i++) {
      if (this.creatures.length >= this.MAX_POP) break;
      for (let j = i+1; j < this.creatures.length; j++) {
        if (this.creatures[i].canReproduce() && this.creatures[j].canReproduce() &&
            dist(this.creatures[i], this.creatures[j]) < 30) {
          this.creatures.push(this.creatures[i].reproduce(this.creatures[j]));
        }
      }
    }
    // 3. spawn cibo (rate 0.5/s)
    if (Math.random() < 0.5 * dt && this.food.length < this.MAX_FOOD)
      this.food.push(new Food(this, ...));
    // 4. cleanup morti
    this.creatures = this.creatures.filter(c => c.alive);
    this.food     = this.food.filter(f => f.alive);
    // 5. statistiche ogni 60 frame (L20.3, no GC ogni frame)
    if (this.frame % 60 === 0) {
      this.gen++;
      this.statsText.setText(`Gen: ${this.gen}  Pop: ${this.creatures.length}  Food: ${this.food.length}`);
    }
    // 6. RE-SEED se estinto (L20.1)
    if (this.creatures.length === 0 && this.gen > 5) {
      for (let i = 0; i < 20; i++) this.creatures.push(new Creature(this, ...));
      this.gen = 0;
    }
  }
}
```

### Progetto demo Troglets (fatto 2026-09-04)
- **Path**: `/home/jagones/Repositories/games-dev/projects/Troglets/`
- **Package**: `com.jagones.troglets`
- **Config**: 30 creature iniziali, 80 cibi, MAX_POP=80, MAX_FOOD=120, energia_max=200, mutazione=10%/15%, riproduzione a 150 energia (costo 80+40)
- **6 geni DNA**: speed, size, vision, hungerRate, aggression, hue
- **Controlli**: tap ovunque = spawn cibo manuale; pulsante PAUSE in basso
- **Header live**: Gen / Pop / Food / Avg DNA (speed, size, vision medi)
- **Verifica**: dopo 15s → screenshot mostra Gen=24, Pop=80, Food=11, AvgDNA speed=0.60 size=0.48 vision=0.60. Evoluzione in corso, creature con colori/dimensioni diverse.
- **Build**: 10s (incrementale), APK 4.0 MB, install OK, no crashes.

### Variazioni riusabili (LLM, personalizza facilmente)
- **Aggiungere un predatore**: nuova `class Predator` con DNA che mangia `Creature` direttamente
- **Più geni**: aggiungi `lifespan`, `reproduction_threshold`, `metabolism` a `DNA.genes`
- **Speciazione**: due specie con DNA `crossover_cost` se `hue` differisce > 0.3
- **Obiettivo utente**: l'utente può "salvare" un DNA preferito e re-inseminarlo (bottone "Inject DNA")
- **Visualizzazione grafo**: traccia linee di parentela (padre → figlio) usando `scene.add.line`

---

## 8c. PATTERN NEURAL — Cervello MLP addestrato off-line + DNA on-device (NeuralCreatures, fatto 2026-09-04)

Per implementare giochi con **creature con un cervello che evolve**, dove il cervello è una piccola MLP (6→8→3, 83 parametri) addestrata off-line sul DGX con numpy in ~15 minuti, serializzata in JSON (~2KB) e consumata in Phaser via `fetch` + forward pass JS-puro (Float32Array, ~0.01ms/inferenza). Vedi implementazione in `games-dev/projects/NeuralCreatures/{www/js/brain.js, www/js/game.js, www/models/brain.json}` + script `games-dev/training/train_creatures.py`.

### Posizionamento rispetto ad ALife+GA puro (§8b) e RL/SLM (§11)
- **ALife+GA puro (§8b)**: cervello è un behavior tree hard-coded (seek food, flee, brake). Nessuna ottimizzazione.
- **NeuralCreatures (§8c)**: cervello è una MLP i cui PESI evolvono via GA off-line. Strategie di comportamento emergono dall'ottimizzazione. Ancora CPU-only, zero dipendenze nuove.
- **RL vero (§11.1)**: cervello ottimizzato con gradient descent su ricompense dense. Richiede PyTorch + GPU.
- **SLM on-device (§11.2)**: cervello è un LLM 1B+ parametri. Richiede nativo, +50MB APK.

**Scegli §8c quando**: il task ha 4-8 osservazioni naturali (energy, distanza, direzione, ...) e 2-4 azioni continue (thrust, brake, eat, ...). Esempi: creature che cacciano, NPC che esplorano, droni che seguono un pattern.

### Architettura minima (3 file, ~300 righe totali)

| File | Responsabilità |
|------|----------------|
| `training/train_creatures.py` | GA off-line: 1000 MLP random → 100 gen mu+lambda → `output/brain.json` |
| `www/js/brain.js` | Classe `Brain`: carica JSON, `forward(obs) → {tx, ty, brake}` con Float32Array |
| `www/js/game.js` | `Brain.load('models/brain.json')` + loop `observe() → forward() → applica azione` |

### Schema cervello (6→8→3)

```
osservazioni (6): [energy/200, age/MAX, nearest_dist/200, dir_x, dir_y, in_vision]
       ↓
hidden (8, ReLU)
       ↓
azioni (3, tanh): [thrust_x, thrust_y, brake]  in [-1, 1]
```

### Training off-line (training/train_creatures.py)

Pattern canonico numpy vettorizzato (vedi L22):
```python
W1, b1, W2, b2, dna = init_population(cfg)  # 1000 MLP random
for gen in range(100):
    fitness = simulate(W1, b1, W2, b2, dna)  # 1500 step vettorizzati
    W1, b1, W2, b2, dna = make_offspring(fitness, ...)  # mu+lambda
save_brain(W1, b1, W2, b2, dna, fitness, 'output/brain.json')
```

**Parametri tipici**: POP=1000, N_GEN=100, N_STEPS=1500, N_FOOD=200, ELITE_FRAC=0.10, MUT_SIGMA_START=0.10→END=0.02, FRESH_BLOOD=0.05 ogni 10 gen, DNA_MUT_RATE=0.10, DNA_MUT_STR=0.15.

**Performance**: 100 generazioni in ~15 minuti su DGX Spark (numpy + BLAS).

### Forward pass JS-puro (www/js/brain.js)

```javascript
class Brain {
  constructor(json) {
    this.W1 = new Float32Array(48);  // 6*8 row-major
    this.b1 = new Float32Array(8);
    this.W2 = new Float32Array(24);  // 8*3
    this.b2 = new Float32Array(3);
    // popola da json...
  }
  forward(obs) {
    const H = new Float32Array(8);
    for (let j=0; j<8; j++) {
      let s = this.b1[j];
      for (let i=0; i<6; i++) s += this.W1[i*8+j] * obs[i];
      H[j] = s > 0 ? s : 0;  // ReLU
    }
    const Y = new Float32Array(3);
    for (let j=0; j<3; j++) {
      let s = this.b2[j];
      for (let i=0; i<8; i++) s += this.W2[i*3+j] * H[i];
      Y[j] = Math.tanh(s);
    }
    return { tx: Y[0], ty: Y[1], brake: Y[2] };
  }
  static async load(url) {
    const j = await (await fetch(url)).json();
    return new Brain(j);
  }
}
```

**Performance**: ~0.01ms/inferenza su OnePlus 15R WebView. 100 creature × 60fps = 6000 inferenze/sec, < 1% CPU.

### Integrazione in Phaser (www/js/game.js)

```javascript
class NeuralCreaturesScene extends Phaser.Scene {
  async create() {
    this.brain = await Brain.load('models/brain.json');
    this.initPopulation();
  }
  updateCreature(c) {
    const obs = this.observe(c);            // 6 elementi come in training
    const act = this.brain.forward(obs);    // {tx, ty, brake}
    c.vx += act.tx * (30 + c.dna[0] * 110);
    c.vy += act.ty * (30 + c.dna[0] * 110);
    c.vx *= 1 - 0.08 * (act.brake + 1) * 0.5;
    // ... wrap, age, energy, food collision, DNA mutation
  }
}
```

### Decisioni di design chiave

1. **NO ONNX Runtime / ExecuTorch / torch.js**: 83 parametri NON giustificano runtime da 500KB-1MB. Float32Array JS-puro è 10-50x più veloce per queste dimensioni.
2. **Training OFF-LINE, non on-device**: 100 generazioni × 1000 creature × 1500 step = 150M forward pass. Fattibile in 15min su numpy DGX, IMPOSSIBILE in WebView (richiederebbe ore). Cervello "congelato" caricato come asset; l'unica evoluzione on-device è la mutazione del DNA (6 geni).
3. **mu+lambda vettorizzato**: `argpartition` O(N) per selezionare elite, tournament selection vettorizzato. Risultato: da >30min a 15min per 100 generazioni vs loop Python ingenuo.
4. **Validazione PRIMA di JS** (vedi L21): `validate_brain.py` ricostruisce lo stesso forward pass in Python e verifica che l'output sia in [-1, 1] + comportamento emergente sensato. Vincolo "stesso forward pass" evita drift.
5. **`npx cap copy` per subdir nuove** (vedi L23): se aggiungi `www/models/brain.json`, DEVI rieseguire `npx cap copy android`. `capacitor.config.json` non scansiona ricorsivamente.

### Progetto demo NeuralCreatures (fatto 2026-09-04)
- **Path**: `games-dev/projects/NeuralCreatures/`
- **Package**: `com.jagones.neuralcreatures`
- **Training**: 100 generazioni in 916s (15min), numpy vettorizzato, mu+lambda + σ decrescente 0.10→0.02
- **Risultati training**: avg_food mangiato 55→102 (+85%), avg_fit 291→526 (+80%), dna_vision 89→110 (pressione selettiva verso più visione)
- **Build**: 6s incrementale, APK 4.0 MB
- **Install**: ~5s
- **Screenshot Gen 0 tick 182/1800**: 100 creature DNA-varianti con linee direzionali, 220 cibo giallo, Fit avg 6.2 max 14.8 (alcune hanno già mangiato 14 volte in 3 secondi)
- **Controlli**: zero (autonomo, evoluzione visibile)
- **Visualizzazione**: cerchi HSL colorati (DNA hue), dimensione da DNA[2], linee bianche di direzione

### Variazioni riusabili (LLM, personalizza facilmente)

- **Più cervelli (speciazione)**: addestra 3-5 MLP con fitness functions diverse (food-seek vs flee-vs-center), ogni creatura ne sceglie uno via DNA.
- **Cervello ricorrente**: aggiungi 4 hidden state ai 6 input → 10 input. Memoria del passato recente.
- **Predatori**: nuovo cervello per `class Predator` addestrato con reward su caccia creature.
- **Visualizzazione attivazioni**: a ogni frame, disegna 8 linee dall'hidden layer (intensità = activation). Vedere il "pensiero" in tempo reale.
- **Cervello utente-modificabile**: slider HUD per modificare pesi live, osservare come cambiano le strategie.
- **Salvataggio/carico**: bottone "Save best brain" → localStorage, "Load" → ricarica brain.json.
- **Training on-device (limitato)**: GA con popolazione 30, 20 generazioni on-device (~4 secondi a 100K forward/sec). Utile per "evoluzione istantanea" di creature dopo che l'utente cambia regole.

### Estensioni scartate con motivazione
- **PyTorch + ONNX export**: PyTorch 2GB+ su DGX, ONNX Runtime Web 1MB+, inferenza 0.1-0.5ms. Non giustificato per 83 param.
- **ExecuTorch / llama.cpp**: nativo richiesto (no WebView), APK +50MB, inferenza 5-15s/token. Solo se modello > 1M params.
- **WebGL shaders per il forward**: 10x più veloce, ma codice 5x più complesso. Non serve a 0.01ms/inferenza.

---

## 9. ROLLBACK

```bash
# Rimuovi singolo gioco
rm -rf /home/jagones/Repositories/games-dev/projects/<NomeGame>/

# Rimuovi tutto il setup giochi
rm -rf /home/jagones/Repositories/games-dev/

# Le dipendenze Capacitor sono user-space (npm); per pulizia totale:
ssh dgx 'bash -lc "npm cache clean --force"'
```

---

## 10. RIFERIMENTI INCROCIATI

- **Skill `android-dgx-build`**: app native Kotlin/Java (gemella, no Phaser)
- **Skill `android-tailscale-adb`**: setup ADB Tailscale (prerequisito)
- **Manuale canonico DGX Android**: `/home/jagones/Repositories/.agent/README-android-dgx.md`
- **Manuale canonico DGX Giochi**: `/home/jagones/Repositories/.agent/README-games-dgx.md`
- **HANDOFF**: `/home/jagones/Repositories/.agent/HANDOFF.md` sezione `## 2026-09-04` (parte 2 = giochi, parte 3 = Troglets ALife, parte 4 = NeuralCreatures cervello+DNA)
- **Progetti demo funzionanti**:
  - Platformer: `games-dev/projects/PixelDash/`
  - ALife/GA: `games-dev/projects/Troglets/`
  - NeuralCreatures: `games-dev/projects/NeuralCreatures/` (cervello MLP addestrato off-line + DNA)
- **Documentazione Phaser 3**: https://photonstorm.github.io/phaser3-docs/
- **Documentazione Capacitor 6**: https://capacitorjs.com/docs (Android workflow: https://capacitorjs.com/docs/android)

---

## 11. ESTENSIONI FUTURE (RIFERIMENTO, non implementate)

Valutate il 2026-09-04 e **scartate** per il workflow attuale. Da riprendere solo se l'utente chiede esplicitamente.

### 11.1 Reinforcement Learning (Godot + godot-rl-agents)
- **Pro**: training vero con PyTorch su DGX GPU; cervello .onnx embeddato nel gioco.
- **Contro**: richiede Godot 4 + export templates 1.5 GB + Python venv con Stable-Baselines3 → primo setup 2-3 ore, fragile.
- **Quando sì**: se l'utente vuole "creature che imparano a sopravvivere con RL vero", non semplice GA.
- **Setup**: `godot-rl-agents` (https://github.com/edbeeching/godot-rl-agents), training `python train.py`, export `.onnx`, import in Godot.

### 11.2 SLM on-device (ExecuTorch / ONNX Runtime Mobile)
- **Pro**: le creature "parlano" o "ragionano" con un piccolo LLM 1B parametri offline.
- **Contro**: APK 50-200 MB extra, inferenza 5-15s/token su OnePlus 15R, progetto nativo (non Phaser).
- **Quando sì**: se l'utente vuole "personaggi che parlano italiano/francese" con personalità persistenti.
- **Setup**: `llama.cpp` su DGX genera `.gguf`, export ONNX, integrazione in app Kotlin nativa (`android-dgx-build`).

### 11.3 Perché per ora vince ALife+GA in Phaser
- **Zero dipendenze nuove** (riusa Phaser 3.80 + Capacitor 6 già installati)
- **LLM scrive naturalmente** (template §8b è ~150 righe copiabili)
- **APK resta 4 MB** (vs 50-200 MB di opzioni 11.1/11.2)
- **Evoluzione visibile in 30 secondi** (Gen 0 → Gen 24 in 15s di test)
- **CPU only**, non richiede GPU sul telefono

Se l'utente chiede "ma perché non usiamo RL/SLM?" → rispondi con questo paragrafo e offri la scelta consapevole.

### 11.4 NeuralCreatures — via di mezzo tra ALife+GA puro e RL pesante (IMPLEMENTATO 2026-09-04)
- **Cosa è**: cervello MLP 6→8→3 (83 parametri) addestrato off-line con GA in numpy (~15min su DGX), serializzato in JSON (2.1KB), caricato in Phaser via `fetch` + forward pass JS-puro.
- **Pro**: strategie di comportamento emergono dall'ottimizzazione (vs behavior tree hard-coded di §8b); zero dipendenze nuove; APK resta 4MB.
- **Contro**: cervello è "congelato" al momento del training; l'unica evoluzione on-device è la mutazione del DNA (6 geni). Se l'utente vuole che il cervello impari dalle azioni del giocatore in tempo reale → serve RL vero (§11.1) o apprendimento per rinforzo on-device.
- **Quando sì**: il task ha 4-8 osservazioni naturali (energy, distanza, direzione) e 2-4 azioni continue. Esempi: creature che cacciano, NPC che esplorano, droni che seguono un pattern.
- **Pattern completo**: vedi §8c sotto. **Demo**: `games-dev/projects/NeuralCreatures/` (100 creature, 220 cibo, cervello 83 param, APK 4.0MB, screenshot Gen=0 Fit max 14.8).
- **Quando NO**: task con ricompense dense o delay brevi (platformer preciso) → RL o behavior tree. Cervello che cambia con input utente → RL on-device. >20 input o >10 azioni → MLP satura, scala a 16→32→8.

---

