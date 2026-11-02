---
name: android-tailscale-adb
description: Connette ADB del PC Windows al telefono OnePlus 15R via Tailscale (WiFi, 5G, ovunque) con auto-reconnect in background. Use quando serve controllare il telefono da remoto, installare APK, leggere logcat, screenshots, o eseguire shell sul telefono senza cavo USB.
---

# ANDROID TAILSCALE ADB

Connessione ADB persistente al telefono **via Tailscale**, funzionante con
WiFi, 5G, dati mobili ovunque. Niente cavo USB, niente WiFi locale richiesto.

**Setup verificato: 2026-09-03. Aggiornato: 2026-09-04 (porta dinamica, non più 5555!).**
Funziona con OnePlus 15R (CPH2769, OxygenOS 16) ma è applicabile a qualsiasi
telefono Android con Debug Wireless + Tailscale.

---

## 1. Identità e componenti

| Componente | Valore |
|---|---|
| Telefono | OnePlus 15R (CPH2769), OxygenOS 16 |
| PC Windows | `desktop-71niuhh` |
| Tailscale account | `jagones84@gmail.com` |
| IP Tailscale telefono | `100.67.181.54` (variabile, usa MagicDNS `oneplus-15r`) |
| IP Tailscale PC | `100.76.251.9` |
| Porta ADB Tailscale | **VARIABILE — scoprirla ogni volta (vedi § 4.4)**. Era 5555, poi **41271** il 2026-09-04. Mai assumere 5555 a memoria |
| ADB | `$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe` |
| Script principale | `F:\GENERAL\android-tailscale\scripts\adb-connect-oneplus.ps1` |
| Auto-reconnect background | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ADB-OnePlus-AutoConnect.lnk` |

---

## 2. Architettura (perché funziona anche su 5G)

```
[PC: tailscale IP 100.76.251.9]
        |
        | adb connect oneplus-15r:<PORTA>   ← comando Tailscale MagicDNS (porta dal § 4.4)
        |
[Tailscale relay DERP / LAN se stesse sulla stessa rete]
        |
        | TCP tunnel cifrato end-to-end (WireGuard)
        |
[OnePlus 15R: tailscale IP 100.67.181.54]
        |
        | adbd in ascolto su una porta (storica: 5555) su tutte le interfacce (tun0 di Tailscale)
```

**Punti chiave**:
- MagicDNS `oneplus-15r` è stabile (nego l'IP cambi) **ma la porta no**: il debug wireless di OnePlus la cambia (5555 → `41271` il 2026-09-04)
- ⚠️ **MAI connettersi a `oneplus-15r:5555` a memoria**: prima scoprire la porta attuale (§ 4.4), poi connettersi
- `setprop service.adb.tcp.port 5555` espone adbd su tutte le interfacce (inclusa `tun0`) **solo finché regge**: dopo un riavvio del debug wireless si torna a una porta random

---

## 3. Setup iniziale (cosa è già stato fatto)

| # | Cosa | File / comando | Stato |
|---|------|----------------|-------|
| 1 | Tailscale installato su PC + telefono | https://tailscale.com/download | ✅ |
| 2 | Account Tailscale `jagones84@gmail.com` attivo | tailscale status | ✅ |
| 3 | PC visibile come `desktop-71niuhh` (100.76.251.9) | tailscale status | ✅ |
| 4 | Telefono visibile come `oneplus-15r` (100.67.181.54) | tailscale status | ✅ |
| 5 | Debug USB attivato sul telefono | Impostazioni → Opzioni sviluppatore → Debug USB ON | ✅ |
| 6 | Debug wireless attivato | Impostazioni → Opzioni sviluppatore → Debug wireless ON | ✅ |
| 7 | `setprop service.adb.tcp.port 5555` eseguito | `adb shell setprop service.adb.tcp.port 5555` | ✅ |
| 8 | Chiave RSA del PC autorizzata sul telefono | `/data/misc/adb/adb_keys` contiene chiave del PC | ✅ |
| 9 | Script PowerShell in `F:\GENERAL\android-tailscale\` | script creato | ✅ |
| 10 | Auto-reconnect in background all'avvio Windows | `.lnk` in `Startup\` | ✅ |

**Per ricreare tutto da zero su un nuovo telefono**, segui il `README.md` in
`F:\GENERAL\android-tailscale\`.

---

## 4. Comandi operativi (uso quotidiano)

### 4.1 Connessione one-shot (la più usata)

```powershell
# Apre PowerShell, lancia script, mostra devices connessi
powershell -ExecutionPolicy Bypass -File F:\GENERAL\android-tailscale\scripts\adb-connect-oneplus.ps1
```

Output atteso (esempio: la porta mostrata è quella corrente, NON sempre 5555):
```
========================================
 ADB Tailscale -> OnePlus 15R
========================================
>> adb connect oneplus-15r:41271
connected to oneplus-15r:41271
 phone: OnePlus 15R
 phone: 16
```

⚠️ Se lo script non trova la porta (perché il debug wireless l'ha cambiata),
usa la scoperta manuale del § 4.4: `adb devices -l` → porta → `adb connect
oneplus-15r:<porta>`.

### 4.2 Comandi ADB remoti (dopo connessione)

```powershell
# ⚠️ PRIMA: scopri la porta corrente (vedi § 4.4) e usa SEMPRE quella al posto di <PORTA>

# lista tutti i device ADB (Tailscale + USB)
adb devices -l

# informazioni telefono
adb -s oneplus-15r:<PORTA> shell getprop ro.product.model
adb -s oneplus-15r:<PORTA> shell getprop ro.build.version.release

# lista app installate
adb -s oneplus-15r:<PORTA> shell pm list packages | head -30

# installa APK
adb -s oneplus-15r:<PORTA> install C:\path\to\app.apk

# logcat live (Ctrl+C per uscire)
adb -s oneplus-15r:<PORTA> logcat

# screenshot
adb -s oneplus-15r:<PORTA> exec-out screencap -p > C:\path\screen.png

# key event (power, home, back, volume)
adb -s oneplus-15r:<PORTA> shell input keyevent 26      # power
adb -s oneplus-15r:<PORTA> shell input keyevent 3       # home
adb -s oneplus-15r:<PORTA> shell input keyevent 4       # back
adb -s oneplus-15r:<PORTA> shell input keyevent 24      # volume up
adb -s oneplus-15r:<PORTA> shell input keyevent 25      # volume down

# testo input (clona stringa nel campo attivo)
adb -s oneplus-15r:<PORTA> shell input text "ciao"

# tap coordinate (x, y in pixel)
adb -s oneplus-15r:<PORTA> shell input tap 540 1200

# pull file (telefono → PC)
adb -s oneplus-15r:<PORTA> pull /sdcard/Download/file.pdf C:\Users\giova\Downloads\

# push file (PC → telefono)
adb -s oneplus-15r:<PORTA> push C:\file.apk /sdcard/Download/

# reverse port forward (esponi porta PC sul telefono)
adb -s oneplus-15r:<PORTA> reverse tcp:8080 tcp:8080
```

### 4.3 Watch mode (background, notifica quando torna online)

Lo script `-Watch` gira in background e tenta la connessione ogni 30s:

```powershell
# Avvia in foreground (per debug o test)
powershell -ExecutionPolicy Bypass -File F:\GENERAL\android-tailscale\scripts\adb-connect-oneplus.ps1 -Watch
```

**Di solito NON serve lanciarlo a mano** perché all'avvio di Windows parte
automaticamente un'istanza hidden (vedi § 6).

---

### 4.4 ⚠️ PRIMA DI TUTTO: scoprire la porta corrente (mai assumere 5555)

Il debug wireless di OnePlus **cambia porta** (es. 5555 → 41271). La fonte
**autorevole** è l'ADB server del PC Windows, che tiene vivo il transport:

```powershell
# Dal PC Windows:
adb devices -l
# output: oneplus-15r:41271  device product:CPH2769 ...
# → la porta è ciò che segue i ":" (es. 41271)
```

Da Linux/DGX (PC raggiungibile via SSH):

```bash
ssh win-ts 'powershell -NoProfile -Command "& C:\Users\giova\AppData\Local\Android\Sdk\platform-tools\adb.exe devices -l"'
```

Oppure sul telefono via USB:

```bash
adb shell getprop service.adb.tcp.port   # se vuoto → porta random attiva
```

**Regola d'oro per agente letterale**:
1. Mai `adb connect oneplus-15r:5555` senza aver verificato la porta
2. Porta = letta da `adb devices -l` del PC (es. `oneplus-15r:41271`)
3. Poi: `adb connect oneplus-15r:<porta>` → `adb devices -l` → deve apparire `device`

---

## 5. Limitazione nota: deep sleep OnePlus

Quando il telefono resta in tasca con schermo spento per **> 5-10 minuti**,
OxygenOS 16 manda Tailscale client in deep sleep e `adbd` non risponde più
su Tailscale.

**Workaround (unico pratico, no root)**:

1. Apri l'app **Tailscale** sul telefono (5 secondi, lo risveglia)
2. Torna al PC e rilancia `adb-connect-oneplus.ps1`
3. Connessione torna subito disponibile

**Perché non si può automatizzare senza root** (vedi
`F:\GENERAL\android-tailscale\docs\oxygenos-permissions.md` per i dettagli):

- OxygenOS 16 blocca `pm grant WRITE_SECURE_SETTINGS` da shell USB
- Tasker serve quel permesso per riavviare adbd in autonomia
- Anche con Tasker + plugin "ADB WiFi" (João Dias) installato, l'azione
  riporta sempre il popup "Allow permission" perché il permesso non si può
  dare via shell
- L'unica seria soluzione è **root con Magisk** (sblocco bootloader, perde
  Knox-like warranty)

**Per il 90% dei casi reali** (controllo rapido, installare app, leggere
file, screenshot), questa limitazione è accettabile.

---

## 6. Auto-reconnect all'avvio di Windows

Lo script `F:\GENERAL\android-tailscale\scripts\auto-connect-hidden.vbs`
è collegato a `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ADB-OnePlus-AutoConnect.lnk`.

**Cosa succede ad ogni boot Windows**:
1. Windows esegue il `.lnk` in `Startup\`
2. Lancia `wscript.exe auto-connect-hidden.vbs` (nessuna finestra visibile)
3. Il VBS lancia PowerShell `-WindowStyle Hidden` con script `-Watch`
4. Lo script tenta `adb connect oneplus-15r:5555` ogni 30s (funziona solo se la
   porta è ancora 5555; con porta dinamica il primo collegamento va fatto a mano
   con la porta del § 4.4)
5. Quando il telefono è online e Tailscale sveglio: beep + MessageBox "ADB Tailscale connesso"

**Per disattivare**:
- Cancella `C:\Users\giova\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\ADB-OnePlus-AutoConnect.lnk`
- Oppure Task Manager → tab "Startup" → disabilita "ADB-OnePlus-AutoConnect"

---

## 7. Verifica pre-flight (esegui sempre prima di una sessione lunga)

```powershell
# 1. Tailscale attivo su entrambi
tailscale status
# atteso: desktop-71niuhh + oneplus-15r + spark-6263 visibili, tutti "online"

# 2. Debug wireless ON sul telefono (impostazioni rapide non mostrano, devi andare in Impostazioni)
# 3. Scopri la porta corrente (NON assumere 5555!) — vedi § 4.4
adb devices -l            # es. -> oneplus-15r:41271 device
adb disconnect
adb connect oneplus-15r:41271   # usa la porta appena letta
# atteso: "connected to oneplus-15r:41271"

# 4. Test shell
adb -s oneplus-15r:<PORTA> shell echo "ciao da $(getprop ro.product.model)"
# atteso: ciao da OnePlus 15R
```

Se il comando 3 fallisce con "cannot connect" o "Connection refused":
- Verifica Tailscale attivo sul telefono (apri app Tailscale)
- Verifica Debug wireless ON (Impostazioni → Opzioni sviluppatore)
- Verifica `setprop service.adb.tcp.port 5555` ancora attivo:
  ```powershell
  adb -s oneplus-15r:5555 shell getprop service.adb.tcp.port
  # atteso: 5555
  ```
  Se vuoto, riesegui `adb -s oneplus-15r:5555 shell setprop service.adb.tcp.port 5555`
  (o fallo via USB momentaneamente)

---

## 8. Troubleshooting

| Sintomo | Causa | Fix |
|---|---|---|
| `cannot connect to oneplus-15r:<porta>` | Tailscale sleep sul telefono | Apri app Tailscale sul telefono, riprova |
| `cannot connect a oneplus-15r:5555` (porta vecchia) | Porta cambiata dal debug wireless | Rileggi la porta con § 4.4 e riconnetti |
| `Connection refused` | Debug wireless OFF sul telefono | Impostazioni → Opzioni sviluppatore → Debug wireless ON |
| `device unauthorized` | Chiave RSA PC non autorizzata | Collega USB, accetta popup "Consenti debug USB" sempre |
| `error: device offline` | ADB server in stato confusionale | `adb kill-server; adb start-server; adb connect oneplus-15r:<porta da § 4.4>` |
| `getprop service.adb.tcp.port` vuoto | `setprop` non ha persistito | `adb shell setprop service.adb.tcp.port 5555` (o collega USB) |
| Port 5555 connessa ma `shell` non risponde | Adbd congelato | Stacca e riattacca Tailscale sul telefono, poi `adb disconnect` + reconnect |
| `tailscale status` non mostra `oneplus-15r` | Tailscale non loggato sul telefono | Apri app Tailscale, fai login con QR o key |
| `-Watch` script non parte all'avvio | `.lnk` in `Startup\` rimosso | Reinstalla con `adb-connect-oneplus.ps1 -Install` (TODO: aggiungere) |

---

## 9. File e cartelle di riferimento

```
F:\GENERAL\android-tailscale\
├── README.md                              ← TL;DR + setup completo
├── SKILL.md                               ← QUESTO FILE
├── scripts\
│   ├── adb-connect-oneplus.ps1            ← script principale
│   └── auto-connect-hidden.vbs            ← VBS per startup
├── docs\
│   ├── oxygenos-permissions.md            ← perché WRITE_SECURE_SETTINGS è bloccato
│   └── tasker-attempts.md                 ← tutti i workaround Tasker provati
└── logs\
    └── 20260903-discover-port.log         ← come abbiamo trovato la porta 5555
```

Documentazione locale (sempre consultabile):
- `F:\GENERAL\android-tailscale\README.md` — TL;DR per setup rapido
- `F:\GENERAL\android-tailscale\docs\oxygenos-permissions.md` — dettagli permessi
- `F:\GENERAL\android-tailscale\docs\tasker-attempts.md` — perché Tasker non basta
- `F:\GENERAL\android-tailscale\logs\20260903-discover-port.log` — discovery porta 5555

---

## 10. Riepilogo: cosa uso, quando

| Vuoi... | Fai... |
|---|---|
| Connettersi subito | § 4.4: scopri la porta, poi `adb connect oneplus-15r:<porta>` |
| Connettersi con notifica automatica | Usa lo script `-Watch` o aspetta il boot Windows |
| Controllare app installate | `adb -s oneplus-15r:<PORTA> shell pm list packages` |
| Installare APK | `adb -s oneplus-15r:<PORTA> install app.apk` |
| Screenshot | `adb -s oneplus-15r:<PORTA> exec-out screencap -p > screen.png` |
| Leggere logcat | `adb -s oneplus-15r:<PORTA> logcat` |
| Automatizzare tap/input | `adb -s oneplus-15r:<PORTA> shell input tap X Y` |
| Trasferire file | `adb -s oneplus-15r:<PORTA> push/pull` |
| Risvegliare il telefono (Tailscale sleep) | Apri app Tailscale sul telefono |
| Disattivare auto-reconnect | Cancella `.lnk` in `Startup\` |

---

## 11. Lezione appresa (cross-project)

> **ADB wireless + Tailscale = robusto, ma con caveat deep sleep su OEM Android.**

- Tailscale + Debug wireless è **la combinazione giusta** per controllo remoto persistente (vs `adb over WiFi LAN` che richiede stessa rete)
- La porta ADB può cambiare (`setprop service.adb.tcp.port 5555` espone adbd su tutte le interfacce, incluse quelle virtuali come `tun0` di Tailscale — ma solo finché regge)
- OnePlus OxygenOS 16 (e molti OEM 2024+) bloccano `WRITE_SECURE_SETTINGS` da shell ADB senza root
- Per il 90% dei casi pratici il deep sleep è gestibile (5 sec di "risveglio manuale" aprendo Tailscale)
- Solo se serve **persistenza assoluta** (telefono in tasca per giorni, 5G only, schermo spento), serve root con Magisk
- `mstsc`-like esperienza: una volta auto-reconnect attivo, ti dimentichi di dover gestire la connessione, funziona e basta

**Lezione 2026-09-04 — la porta NON è stabile**: la skill originale diceva
"5555 fissa", ma il debug wireless di OnePlus l'ha cambiata in `41271`.
Un agente che segue le istruzioni alla lettera deve **sempre** rileggere la
porta da `adb devices -l` (PC) prima di connettersi — Regola § 4.4.

**Regola d'oro per debug Android remoto**:
1. USB + Tailscale insieme = zero problemi (USB primario, Tailscale fallback)
2. Se solo Tailscale, parti con la scoperta porta (§ 4.4), poi `adb connect oneplus-15r:<PORTA>` (MagicDNS > IP fisso)
3. Se cade, `adb kill-server && adb start-server && adb connect ...` risolve il 70% dei casi
4. Se non risolve, apri app Tailscale sul telefono per svegliarlo

---

## 8. Variante DGX Spark (testata 2026-09-03)

Il **DGX Spark** è anch'esso su Tailscale (`spark-6263`, IP `100.102.61.23`) e può
quindi pilotare il telefono ADB direttamente dal cloud locale. Stessa
architettura, nessuna porta diversa, ma tre differenze operative importanti.

### 8.1 Installazione adb + JDK 17 sul DGX (Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y adb openjdk-17-jdk-headless unzip
```

Verifica:
```bash
adb version          # → Android Debug Bridge version 1.0.41
java -version        # → openjdk version "17.x"
```

### 8.2 Sync della chiave ADB (CRUCIALE)

Il telefono ha autorizzato la chiave privata del **PC Windows** in
`/data/misc/adb/adb_keys`. Il DGX genera una chiave diversa al primo avvio
di adb → `unauthorized` sistematico.

**Fix**: copiare la chiave privata del PC Windows nella home del DGX **con `scp`, NON con i mount SSHFS** (i mount `win_disks` sono stantii e `win_home` è una cartella LOCALE del DGX, verificato 2026-09-18):

```bash
# adbkey si trova sul PC Windows in C:\Users\giova\.android\adbkey
mkdir -p ~/.android
scp win-ts:C:/Users/giova/.android/adbkey ~/.android/
scp win-ts:C:/Users/giova/.android/adbkey.pub ~/.android/
chmod 600 ~/.android/adbkey
# verifica l'hash su entrambi i lati (Get-FileHash su Windows)
adb kill-server && adb start-server
```

Dopo questo, `adb connect oneplus-15r:<porta da § 4.4>` ritorna `connected`
(non più `unauthorized`) e i pacchetti installati sono visibili (`adb shell pm
list packages | wc -l` → 627+).

### 8.3 Comandi operativi dal DGX

⚠️ Porta = quella attuale dal § 4.4 (es. 41271), MAI 5555 a memoria.

```bash
# Connessione
export DEV=oneplus-15r:41271   # sostituisci con la porta letta dal § 4.4
adb -s $DEV shell echo "ok"

# Installare APK
adb -s $DEV install -r /percorso/app-debug.apk

# Screenshot (vedi § 8.4 per unlock)
adb -s $DEV exec-out screencap -p > /tmp/screen.png

# Logcat filtrato
adb -s $DEV logcat -d --pid=$(adb -s $DEV shell pidof <package>)
```

### 8.4 ⚠️ TRAPPOLA OxygenOS: unlock + sblocca tendina prima di screenshot

La OxygenOS 16 di OnePlus 15R ha un **lockscreen "dream"** che blocca
`screencap` con un framebuffer cached nero (20239 bytes, sempre lo stesso
MD5) anche quando l'app è `ResumedActivity`. `uiautomator dump` ritorna
0 nodi dell'app.

⚠️ In tutti i comandi qui sotto usa la porta attuale (§ 4.4), non 5555.

**Sequenza che funziona** (testata 2026-09-03 con app `HelloFromDGX`):

```bash
# ⚠️ Sostituisci <PORTA> con la porta attuale (vedi § 4.4)

# 1. Sveglia display
adb -s oneplus-15r:<PORTA> shell input keyevent 224   # WAKEUP
adb -s oneplus-15r:<PORTA> shell svc power stayon true

# 2. Esci dal lockscreen dream (swipe up viene intercettato
#    dalla NotificationShade → meglio HOME)
adb -s oneplus-15r:<PORTA> shell input keyevent 3     # HOME
sleep 2

# 3. Lancia l'app (HOT start: task già in cima)
adb -s oneplus-15r:<PORTA> shell am start -n <package>/.MainActivity
sleep 4

# 4. Verifica focus reale
adb -s oneplus-15r:<PORTA> shell dumpsys window | grep mCurrentFocus
# → deve contenere "<package>/<activity>", NON "NotificationShade"

# 5. Solo ORA screenshot
adb -s oneplus-15r:<PORTA> exec-out screencap -p > /tmp/screen.png
```

Senza questa sequenza, lo screenshot è di 20239 bytes (cached) e la
view hierarchy non contiene l'app.

### 8.5 Build APK direttamente sul DGX

Il DGX può buildare APK Android via Gradle wrapper, **ma serve JDK 17**
(AGP 8.13.1 rifiuta JDK 21+):

```bash
# Setup una tantum
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME=$HOME/android-sdk          # oppure path pre-esistente
# il resto come da skill android-studio-workflow
```

Per build rapidi, **più pratico buildare sul PC Windows** e copiare
l'APK sul DGX con **`scp` diretto** per installarlo (i mount SSHFS
`win_disks` sono stantii — non usarli, verificato 2026-09-18):

```bash
# Windows build → APK in C:\Users\giova\AndroidStudioProjects\<proj>\app\build\outputs\apk\debug\app-debug.apk
scp win-ts:C:/Users/giova/AndroidStudioProjects/<proj>/app/build/outputs/apk/debug/app-debug.apk /tmp/app-debug.apk
md5sum /tmp/app-debug.apk   # confronta con Get-FileHash -Algorithm MD5 sul PC
adb -s oneplus-15r:<porta da § 4.4> install -r /tmp/app-debug.apk
```

### 8.6 Riepilogo differenze PC Windows vs DGX Spark

| Aspetto | PC Windows | DGX Spark |
|---|---|---|
| Tailscale IP client | `100.76.251.9` | `100.102.61.23` (`spark-6263`) |
| Adb installato | `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe` | `apt install adb` (system) |
| Chiave ADB | `C:\Users\giova\.android\adbkey` (già autorizzata) | `~/.android/adbkey` (copiata dal PC, vedi § 8.2) |
| Path APK | `<proj>\app\build\outputs\apk\debug\app-debug.apk` | copiato con `scp win-ts:C:/Users/giova/...` (NON SSHFS, mount stantii) |
| Java | JDK 17 in `C:\Tools\jdk17\jdk-17.0.12+7` | `apt install openjdk-17-jdk-headless` |
| Trappola lockscreen | No (Tailscale app gestisce) | **Sì** (sequenza § 8.4 obbligatoria) |
| Build Android | `gradlew.bat assembleDebug` (PC nativo) | `gradlew assembleDebug` (lento, preferibile build su PC) |

**Conclusione**: la skill `android-tailscale-adb` originale (PC Windows)
resta valida al 100% sul DGX per l'install/test/screenshot. L'unica
aggiunta necessaria è il **sync della chiave ADB** (§ 8.2) e la
**sequenza di unlock** (§ 8.4) per screenshot reali.

---

## 8.7 Pilotare Termux dal DGX via ADB + messaggi Termux→DGX (verificato 2026-09-24)

Controllo del terminale **Termux** del telefono dal DGX, **senza SSH e senza
root**, scrivendo comandi via ADB. Caso d'uso verificato: far inviare al
telefono (in 5G) un messaggio che arriva sul DGX.

### Connessione (5G, IP Tailscale diretto)

La porta `5555` ha funzionato di nuovo il 2026-09-24 (esposta su `tun0`);
resta valida la regola § 4.4: **verificare SEMPRE la porta** da `adb devices -l`.

```bash
export DEV=100.67.181.54:5555        # IP Tailscale del telefono
adb connect $DEV
adb -s $DEV shell getprop ro.product.model       # → CPH2769
```

Se dopo un handover 5G compare `device offline`, riconnetti in loop:

```bash
adb disconnect 100.67.181.54:5555
for i in $(seq 1 5); do
  adb connect 100.67.181.54:5555
  sleep 2
  [ "$(adb devices | awk '/100.67.181.54/{print $2}')" = device ] && break
done
```

### Portare Termux in primo piano (OxygenOS "Dozing")

Se `dumpsys power` mostra `mWakefulness=Dozing`, gli `input` finiscono sulla
`NotificationShade`. Sequenza che funziona:

```bash
adb -s $DEV shell input keyevent 224              # WAKEUP
adb -s $DEV shell svc power stayon true
adb -s $DEV shell wm dismiss-keyguard
adb -s $DEV shell am start -n com.termux/.app.TermuxActivity
sleep 4
adb -s $DEV shell dumpsys window | grep mCurrentFocus
# atteso: com.termux/com.termux.app.TermuxActivity
adb -s $DEV shell input tap 540 1200              # tap sul terminale (cursore)
```

### ATTENZIONE: digitare testo CON SPAZI in Termux (trappola quoting)

`adb shell` passa l'argomento allo `sh` di Android: **senza quoting gli spazi
spezzano il comando** e Termux riceve solo la prima parola.

```bash
# SBAGLIATO → digita solo "curl"
adb -s $DEV shell input text curl http://100.102.61.23:8000/x

# GIUSTO → argomento quotato per lo sh remoto (spazi preservati)
adb -s $DEV shell "input text 'echo hello world spazi ok'"
sleep 1
adb -s $DEV shell input keyevent 66                # ENTER
```

- `%s` **non** viene convertito in spazio (verificato): servono spazi reali.
- Termux non espone `EditText`: `uiautomator dump` ritorna **0 nodi**. Per lo
  stato usa SEMPRE lo screenshot (`exec-out screencap -p > /tmp/t.png`) e
  leggilo come immagine.

### Termux "nudo": niente curl/nc → `bash /dev/tcp`

Il Termux del OnePlus **non** ha `curl`, `nc` né openssh. Per una connessione
TCP usa la net-redirection di bash:

```bash
# dentro Termux (digitato via ADB con la regola di quoting sopra):
exec 3<>/dev/tcp/100.102.61.23/12345
echo CIAO_SPARK_DAL_CELL_5G >&3
exec 3>&-
```

### Ricevere sul DGX (listener)

```bash
# Sul DGX: UN solo listener (SO_REUSEPORT → più listener si rubano le connessioni)
> /tmp/cell_messages.log
setsid nc -l -k -p 12345 >> /tmp/cell_messages.log 2>/tmp/cell_err.log </dev/null &
```

Risultato verificato: il testo digitato in Termux compare in
`/tmp/cell_messages.log` (`CIAO_SPARK_SONO_TERMUX_SU_CELL_5G`).

### ATTENZIONE: trappola `pkill -f` (vale per qualsiasi comando via SSH)

`pkill -f "<pattern>"` uccide **anche la shell SSH che lo esegue** se il pattern
compare nella sua stessa riga di comando (es. `pkill -f "nc -l"` o
`pkill -f listen_msg.sh`): la sessione muore con exit `4294967295` e output
vuoto. Fix: match esatto del nome (`pkill -x nc`) oppure kill per PID:

```bash
for p in $(pgrep -x nc); do kill -9 "$p"; done
```

---

## 9. TODO / miglioramenti possibili

- [ ] Auto-reconnect ADB Tailscale in background sul DGX (systemd user service analogo al `.lnk` Windows Startup)
- [ ] Script `verify-app.sh` standard che include la sequenza § 8.4
- [ ] Wrapper `dgx-adb` che inietta automaticamente `adb -s oneplus-15r:<porta da § 4.4>` davanti a ogni comando
- [ ] Script `dgx-termux-send.sh` (DGX): listener + digita/incolla il comando in Termux e attende il messaggio in arrivo
- [ ] Termux: valutare `pkg install openssh` per la skill `termux-ssh` (oggi Termux è "nudo": niente sshd)

