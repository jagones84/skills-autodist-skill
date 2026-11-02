---
name: connect to DGX SPARK
description: Z: drive auto-mapped = working directory di default (TUTTI i workspace Trae sono qui dentro). SSH per i comandi (dgx via wifi, dgx_eth via cavo diretto 10.0.0.1), RDP GNOME 3389 per il desktop grafico, port forward per esporre servizi. Use quando serve shell remota, desktop grafico, o servizi dal DGX verso il PC.
---

# DGX SPARK — collegamento rapido

**Z: = `/home/jagones` del DGX, montato automaticamente all'avvio Windows.**
Tutti i workspace aperti in Trae puntano già a `Z:\...`, quindi la lettura file
è nativa (Read/Glob). Questa skill copre solo le 3 cose per cui serve altro:

1. **Comandi shell** sul DGX → `ssh dgx '...'`
2. **Desktop grafico** del DGX → RDP GNOME (porta 3389)
3. **Servizi del DGX** esposti sul PC → SSH port forward

**Fallback di emergenza** (se Z: non risponde, WiFi perso, DGX spento):
vedi §6 — l'SSH via Tailscale funziona **anche quando tutto il resto è giù**.

---

## 0. Identità (riferimento rapido)

| Campo | Valore |
|---|---|
| Hostname | `DGX-SPARK-ETH` |
| IP LAN (wifi) | `192.168.1.37` (alias `dgx`) |
| IP cavo diretto | DGX `10.0.0.1` ↔ PC `10.0.0.2`, alias `dgx_eth`, 2.5 Gbps, SENZA gateway (2026-09-08) |
| IP Tailscale | `100.102.61.23` (host `spark-6263` in MagicDNS) |
| User | `jagones` |
| Home | `/home/jagones` ≡ `Z:\` (auto-montato) |
| RDP | porta 3389 (GNOME Remote Login, factory NVIDIA) |
| Chiave SSH | `~/.ssh/id_ed25519` (già autorizzata) |

**Verifica pre-flight** (10s):
```powershell
Get-PSDrive Z                                            # Root = \\192.168.1.37\Home
ssh dgx 'echo ok; whoami'                                # ok / jagones
```

---

## 1. Z: (auto-montato, lettura file nativa)

**Z: è il workspace.** Qualsiasi `Read`, `Glob`, `RunCommand` su `Z:\` funziona
già senza configurazione. Gli strumenti nativi (Read/Glob) su Z: sono il modo
**più veloce** per lavorare sui file del DGX.

**Auto-mount all'avvio**:
- Script: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DGX-Z-Autostart.vbs`
- Launcher manuale: `F:\GENERAL\launchers\Open-DGX-Z.bat`

**Se Z: mostra X rossa** (perso WiFi o DGX spento):
```powershell
# da PowerShell
& "F:\GENERAL\scripts\windows\remap-z-to-wifi.ps1"
```

### Cosa funziona e cosa NO con Z:

| Operazione | Stato | Note |
|---|---|---|
| `Read` su `Z:\...` | ✅ | nativo, veloce |
| `Glob` su `Z:\...\*.py` | ✅ | pattern funzionano |
| `Grep` su `Z:\...` | ❌ errore UNC 267 | usa `ssh dgx 'grep -RIn ...'` |
| `Write` su nuovo file in Z: | ⚠️ prima volta passa, poi blocca allowlist | preferisci `ssh dgx 'cat > ...'` |
| `Edit` su file esistente in Z: | ❌ allowlist sandbox | usa `ssh dgx 'sed -i ...'` o riscrivi via SSH |
| `Delete` su Z: | ❌ allowlist | `ssh dgx 'rm ...'` |

**Regola**: per leggere/listare usa Z: nativo. Per editare/cancellare/eseguire, usa SSH.

---

## 2. SSH (per qualsiasi comando sul DGX)

Alias già configurati in `~/.ssh/config`: `dgx` (wifi 192.168.1.37), `dgx_eth` (cavo diretto 10.0.0.1, 2.5 Gbps) o `DGX-SPARK-ETH` (lungo).

**ATTENZIONE underscore**: l'alias è `dgx_eth` col TRATTINO BASSO. `ssh dgx-eth` col trattino NON esiste: risolve un altro host, entra come utente `giova` e chiede password a vuoto (errore visto 2026-09-08).

**Regola wifi vs cavo**: comandi e lavoro normale via `ssh dgx` (wifi); trasferimenti grossi (scp/rsync, backup) via `ssh dgx_eth` (cavo: ping ~0.3ms vs ~3ms wifi). Il cavo NON ha gateway: internet resta sul wifi da entrambi i lati (`never-default` sul DGX, nessuna rotta default su Ethernet 2 del PC).

**Viceversa (dal DGX al PC)**: alias `win_eth` in `~/.ssh/config` del DGX = PC `10.0.0.2` via cavo (chiave `dgx_to_windows`, user `giova`). ATTENZIONE prospettiva: dal DGX il PC è `10.0.0.2`, `10.0.0.1` è il DGX stesso (errore 2026-09-08: HostName sbagliato faceva SSH del DGX verso se stesso). Nota: `giova` è admin Windows → la chiave deve stare in `administrators_authorized_keys`, non in `~/.ssh/authorized_keys`.

```powershell
# Comando one-shot
ssh dgx 'cmd...'

# Comando che ha bisogno del login shell (PATH, env, alias)
ssh dgx 'bash -lc "comando"'

# Comando sudo (solo se sai la password)
ssh dgx 'sudo cmd...'
```

### Esempi utili (uno per caso d'uso)

```powershell
# Stato GPU
ssh dgx 'nvidia-smi --query-gpu=name,utilization.gpu,power.draw,temperature.gpu --format=csv,noheader'

# Processi per uso memoria
ssh dgx 'ps -eo pid,user,pmem,rss,cmd --sort=-rss | head -15'

# Servizi attivi (gateway, model server, OpenClaw)
ssh dgx 'systemctl list-units --type=service --state=running | head -20'

# Spazio disco
ssh dgx 'df -h /home/jagones'

# Log di un servizio
ssh dgx 'journalctl -u nome-servizio -n 50 --no-pager'

# Lanciare un processo lungo in background (sopravvive alla chiusura del terminale)
ssh dgx 'tmux new-session -d -s nome "comando-lungo"'
# dopo: ssh dgx 'tmux attach -t nome' per rientrare
```

### Editare/cancellare/creare file sul DGX

```powershell
# patch con sed (piccole modifiche)
ssh dgx 'sed -i "s/vecchio/nuovo/" /percorso/file'

# creare/scrivere un file
$testo = @"
contenuto
multilinea
"@
$testo | ssh dgx 'cat > /percorso/file'

# cancellare
ssh dgx 'rm /percorso/file'
```

### Copiare file PC ↔ DGX

```powershell
# singolo file
scp C:\locale.txt dgx:/tmp/

# cartella
scp -r C:\dir dgx:/home/jagones/

# sync incrementale (grossi, riprende da dove si è interrotto)
rsync -avz --progress C:\dir\ dgx:/home/jagones/dir/
```

---

## 3. RDP (desktop grafico GNOME)

Connessione grafica al desktop del DGX. Configurazione verificata e funzionante.

**Credenziali**: `jagones` / `Starfield_` (RDP NTLM, no dominio).

**Apri il desktop remoto**:
- Launcher: `F:\GENERAL\launchers\Open-DGX-RDP-WiFi.bat` (doppio click)
- Oppure: `mstsc F:\GENERAL\launchers\DGX-Spark-WiFi-2560x1440.rdp`
- File .rdp: `screen mode id:i:1` (windowed), 3440x1440, bpp 24, CRLF

**Se il desktop non risponde o mostra "un'altra sessione loggata"**:
```powershell
ssh dgx 'loginctl list-sessions'
# cerca sessioni zombie in "closing" da ore
ssh dgx 'loginctl terminate-session <ID>'
ssh dgx 'sudo systemctl stop session-<ID>.scope'
```

Documentazione completa: `F:\GENERAL\.agent\README-xrdp-dgx.md`.

---

## 4. Port forward (servizi DGX sul PC)

Aprire un servizio del DGX sul tuo browser Windows senza esporlo a internet.

```powershell
# Esempio: gateway OpenClaw (porta 8092 sul DGX → 127.0.0.1:8092 sul PC)
ssh dgx -L 8092:127.0.0.1:8092 -N
# ora apri http://127.0.0.1:8092/health nel browser

# Model server (llama.cpp su porta 8000)
ssh dgx -L 8000:127.0.0.1:8000 -N

# Più servizi in un comando
ssh dgx -L 8092:127.0.0.1:8092 -L 8000:127.0.0.1:8000 -N
```

`Ctrl+C` per chiudere. Per lasciarlo in background:
```powershell
Start-Process ssh -ArgumentList "dgx","-L","8092:127.0.0.1:8092","-N" -WindowStyle Hidden
```

---

## 5. Riepilogo: cosa uso, quando

| Vuoi... | Fai... |
|---|---|
| Leggere un file del DGX | `Read` su `Z:\...` (nativo, veloce) |
| Listare una cartella del DGX | `Glob` su `Z:\...` (nativo) |
| Cercare testo nel DGX | `ssh dgx 'grep -RIn ...'` |
| Editare/cancellare un file del DGX | SSH (`sed`/`rm`/`cat >`) |
| Eseguire un comando shell sul DGX | `ssh dgx '...'` (wifi) |
| Aprire il desktop grafico del DGX | `Open-DGX-RDP-WiFi.bat` |
| Esporre un servizio del DGX sul browser locale | `ssh dgx -L PORTA:127.0.0.1:PORTA -N` |
| Trasferire file grossi PC ↔ DGX | `scp` o `rsync` via `dgx_eth` (cavo 2.5 Gbps) |
| Monitorare power/temp pre-crash (OpenClaw, Hermes, ComfyUI, training) | `ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh start\|status\|stop\|tail\|stats'` + CSV `~/Programs/VRAM_shield/outputs/crashwatch_*.csv` (1Hz, flush+fsync per riga, systemd-run `crashwatch.service` con `Restart=on-failure`, sopravvive a crash/kill) |
| Lavorare solo su Windows locale | nessun SSH, tutto nativo |

**Regola d'oro**: se il file è in Z:, sei già lì. SSH solo per quello che Read/Glob/Write nativi non possono fare.

---

## 5bis. Real-time crash forensics (crashwatch)

Per OpenClaw, Hermes, ComfyUI, training, o qualsiasi carico CPU+GPU
di lunga durata: prima di lanciare il carico, accendi `crashwatch`.
Sopravvive a process kill, reboot, e crash improvvisi: i sample sono
`flush+os.fsync` su disco ad ogni riga, quindi l'ultimo secondo di
telemetria e' sempre recuperabile dal CSV.

```powershell
# Avvia (systemd-run --user --unit=crashwatch, Restart=on-failure, 1Hz)
ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh start'

# Stato: dice se la unit e' attiva + path del CSV corrente
ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh status'

# Ultime 20 righe del CSV
ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh tail'

# Stats aggregate: max/min/avg GPU temp, GPU power, CPU temp
ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh stats'

# Path del CSV attivo (utile per piping)
ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh path'

# Stop (cancella la unit ma lascia il CSV su disco)
ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh stop'

# Restart (chiude il CSV corrente, ne apre uno nuovo)
ssh dgx '~/Programs/VRAM_shield/scripts/crashwatch.sh restart'
```

Prima di usarlo la prima volta serve `sudo loginctl enable-linger $USER`
(sul DGX) perche' le user unit systemd sopravvivano al logout grafico.

Dopo un crash, il CSV piu' recente in
`~/Programs/VRAM_shield/outputs/crashwatch_*.csv` contiene gli ultimi
sample. Controlla in ordine: `gpu_temp_c >= 95` (GPU thermal), `cpu_max_temp_c >= 95`
(CPU/LPDDR5x thermal), `gpu_power_w` spike poi 0 (driver hang), `oom_kill_total`
aumentato, `driver_err_30s > 0`, `alert_* = 1`. Doc completa in
`Z:\Programs\VRAM_shield\README.md` sezione "Real-Time Crash Forensics".

---

## 6. Fallback di emergenza (quando Z: muore)

Z: puo' morire per vari motivi: DGX spento, WiFi perso, IP DGX cambiato,
DGX in manutenzione, drive mappato corrotto. In questi casi **SSH funziona
sempre**, a patto di avere uno di questi accessi:

### 6.1 Tentativi in ordine di preferenza

```powershell
# 0. SSH via cavo diretto (funziona anche se wifi/router sono giu', ma solo PC e DGX accesi e cavo inserito)
ssh dgx_eth 'echo ok'                               # 10.0.0.1, alias con UNDERSCORE

# 1. SSH via Tailscale (funziona anche se il DGX e' spento e poi riacceso, o se il router e' impazzito)
ssh spark-6263 'echo ok'                                # MagicDNS Tailscale
ssh 100.102.61.23 'echo ok'                             # IP Tailscale fisso

# 2. SSH via LAN (solo se sei sulla stessa rete del DGX)
ssh dgx 'echo ok'                                       # alias ~/.ssh/config
ssh jagones@192.168.1.37 'echo ok'                      # IP LAN diretto
ssh jagones@DGX-SPARK-ETH 'echo ok'                     # hostname LAN (se DNS risolve)
```

### 6.2 Se SSH proprio non risponde

| Test | Comando | Atteso |
|---|---|---|
| DGX raggiungibile in LAN | `Test-Connection 192.168.1.37 -Count 2 -Quiet` | True |
| DGX raggiungibile via Tailscale | `tailscale status` mostra `spark-6263` online | True |
| DGX spento | `Test-Connection` False + niente rumore ventole | accendilo |
| DGX in WiFi ma tu no | Tailscale ancora attivo | usa §6.1 caso 1 |
| Chiave sbagliata | `Permission denied (publickey)` | riusa `ssh dgx` (ha IdentitiesOnly) |
| DNS non risolve | `Could not resolve hostname DGX-SPARK-ETH` | usa IP diretto |

### 6.3 SSH "bare-metal" (se niente di configurato funziona)

Pattern che funziona **sempre** se la rete va e la chiave e' quella giusta:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" `
    -o IdentitiesOnly=yes `
    -o ConnectTimeout=5 `
    -o StrictHostKeyChecking=accept-new `
    jagones@192.168.1.37 'echo ok; whoami; uname -r'
```

Se questo non funziona, il problema e' fisico (DGX spento, cavo staccato,
firewall, chiave sbagliata) — niente di software risolvera'.

### 6.4 Recupero Z: dopo che SSH funziona

```powershell
# Dopo che ssh dgx funziona, ricrea il mapping Z:
& "F:\GENERAL\scripts\windows\remap-z-to-wifi.ps1"

# Verifica
Get-PSDrive Z                                           # Root deve essere \\192.168.1.37\Home
```

**Mai disperare**: se SSH funziona, TUTTO il resto si puo' recuperare.

