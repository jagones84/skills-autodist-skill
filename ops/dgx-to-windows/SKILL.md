---
name: "dgx-to-windows"
description: "Connects from DGX Spark (Linux) to the Windows PC over SSH using preconfigured shortcuts (win / desktop / win-ts). All three use ed25519 key (no password). Invoke when the user asks to SSH from DGX to the Windows desktop, run a command on the Windows PC, copy files from Windows to DGX, inspect Windows drives, list/read/edit files on the Windows drives mounted under /home/jagones/win_disks/, or troubleshoot SSH access. Triggers: 'ssh su windows', 'collegati al pc windows', 'ssh win', 'ssh desktop', 'ssh win-ts', 'ssh to desktop', 'run on windows', 'esegui su windows', 'lanciare comando su windows', 'copia da windows', 'ispeziona disco windows', 'leggi file windows', 'scrivi su disco windows', 'crea file su windows', 'edit file windows'."
---

# SSH dal DGX Spark al PC Windows

Il DGX Spark (Linux) ha già 3 alias SSH preconfigurati in `~/.ssh/config` per
raggiungere il PC Windows (utente `giova`). Tutti usano la stessa chiave
ed25519 (`~/.ssh/dgx_to_windows`) e **NON chiedono password** (ControlMaster
riusa la connessione, ControlPersist 10min).

> Source of truth: il blocco `# >>> dgx->windows managed block >>>` in
> `~/.ssh/config` sul DGX. NON editarlo a mano (viene rigenerato da script
> gestionali). Leggere sempre il file prima di intervenire.

## I 3 alias

| Alias       | Destinazione             | Quando usarlo                                                  |
|-------------|--------------------------|----------------------------------------------------------------|
| `ssh win`   | MagicDNS `desktop-71niuhh` (Tailscale) | **DEFAULT** — funziona ovunque (casa, 5G, fuori) |
| `ssh desktop` | IP LAN `192.168.1.5`    | Solo quando si è in casa, fallback se Tailscale giù           |
| `ssh win-ts` | IP Tailscale `100.76.251.9` | Bypass MagicDNS se DNS non risolve, utile per debug            |

## Comandi tipici

```bash
# singolo comando remoto (PREFERITO: no shell interattiva, quoting pulito)
ssh win "ipconfig | findstr IPv4"
ssh desktop "powershell -NoProfile -Command 'Get-Service | Where-Object {$_.Status -eq \"Running\"}'"

# copia file DGX → Windows
scp file.txt win:/c/Users/giova/Desktop/

# copia file Windows → DGX
scp win:/c/Users/giova/Downloads/report.pdf ./

# sessione interattiva (usare con parsimonia, preferire ssh <host> "cmd")
ssh win
```

## Regole d'oro

1. **MAI** chiedere la password Windows all'utente: l'auth è a chiave, se
   fallisce c'è un problema di config (rigenerare la chiave lato DGX e
   importarla in `~/.ssh/authorized_keys` lato Windows, oppure controllare
   che il servizio OpenSSH sia in esecuzione su Windows).
2. **MAI** usare password inline in script: la chiave è già caricata.
3. **Preferire `ssh <alias> "cmd"`** rispetto a sessioni interattive:
   evita quoting disordinato, più riproducibile, più veloce.
4. Se `ssh win` fallisce da fuori casa: Tailscale sul DGX è giù
   (`sudo tailscale status`), oppure la coda di multiplexing è corrotta
   (`rm ~/.ssh/sockets/giova@desktop-71niuhh-22` e riprovare).
5. Se `ssh desktop` fallisce in casa: la Windows PC non è sulla LAN
   (firewall / WiFi diverso / risparmio energia). Verificare con
   `ping 192.168.1.5` dal DGX.
6. La connessione `ssh` dal DGX verso Windows è **più lenta** del mount
   CIFS LAN ma **molto più veloce e comoda** di non avere nulla: se serve
   velocità massima su file grossi, preferire il mount CIFS `/mnt/win-*`
   (solo in casa).

## Dischi Windows montati sul DGX (PRIMARY = sshfs, FALLBACK = cifs)

I dischi del PC Windows **SONO MONTATI sul DGX** sotto
`/home/jagones/win_disks/` e `/mnt/`. I nomi delle directory sul DGX
corrispondono alle lettere di unità di rete mostrate in Esplora File
Windows (CC, DD, EE, FF, GG, win_home).

### Mount point PRIMARIO: SSHFS (via alias `ssh win`)

| Path DGX                          | Path Windows     | Note                                    |
|-----------------------------------|------------------|-----------------------------------------|
| `/home/jagones/win_disks/CC`      | `C:`             | sshfs, disco sistema Windows            |
| `/home/jagones/win_disks/DD`      | `D:`             | sshfs                                   |
| `/home/jagones/win_disks/EE`      | `E:`             | sshfs                                   |
| `/home/jagones/win_disks/FF`      | `F:`             | sshfs (6.4T, capiente)                  |
| `/home/jagones/win_disks/GG`      | `G:`             | sshfs                                   |
| `/home/jagones/win_disks/win_home`| `C:\Users\giova` | sshfs, home utente Windows              |

- I processi sshfs girano come `jagones` con `IdentityFile=~/.ssh/dgx_to_windows`
  (la stessa chiave di `ssh win`).
- Opzioni utili: `reconnect`, `ServerAliveInterval=15`,
  `ServerAliveCountMax=3`, `auto_cache`, `transform_symlinks`.
- Gestiti da systemd user (`home-jagones-win_disks-XX.mount`,
  `loaded active mounted`): si riavviano da soli dopo reboot/SSH.
- Funzionano da qualsiasi rete (casa, 5G, fuori) **purché Tailscale sia
  attivo** (passano per `ssh win`).

```bash
ls /home/jagones/win_disks/CC/Users/giova/Desktop
cp /home/jagones/win_disks/FF/bigfile.zip /tmp/
```

### Mount point FALLBACK: CIFS/SMB (solo in LAN)

| Path DGX     | Share SMB                | Note                       |
|--------------|--------------------------|----------------------------|
| `/mnt/win-c` | `//192.168.1.5/C$`       | admin share, richiede LAN  |
| `/mnt/win-d` | `//192.168.1.5/D$`       | admin share, richiede LAN  |
| `/mnt/win-e` | `//192.168.1.5/E$`       | admin share, richiede LAN  |
| `/mnt/win-f` | `//192.168.1.5/F$`       | admin share, richiede LAN  |

- Configurati in `/etc/fstab` con creds in
  `/home/jagones/.smb/win-shares-credentials`, opzioni
  `_netdev,x-systemd.mount-timeout=30` (non montano se rete giù).
- **NON** montano la G: (manca in fstab).
- **NON** funzionano fuori casa: richiedono Windows sulla LAN
  `192.168.1.5`. Usare sshfs quando si è fuori.
- Velocità: ~10x più veloce di sshfs ma limitato alla LAN.

### Confronto sshfs vs CIFS

|                    | sshfs (`win_disks/`)   | CIFS (`/mnt/win-*`)         |
|--------------------|------------------------|-----------------------------|
| Rete               | ovunque via Tailscale  | solo LAN 192.168.1.5        |
| Velocità           | media (~LAN cifrata)   | alta                        |
| Richiede auth      | chiave SSH             | creds file SMB              |
| Copertura dischi   | C/D/E/F/G + home       | solo C/D/E/F (no G)         |
| Default uso        | **SÌ** (sempre)        | solo se serve velocità LAN  |

### Altro

- `/home/jagones/thinclient_drives` = mount xrdp-chansrv, attualmente
  **rotto** ("Transport endpoint is not connected"). Ignorare.
- `Z:` sul **DGX** = `/home/jagones` (locale, NVMe).
- `Z:` su **Windows** = share di rete della home (la stessa che si vede
  come `win_home` sul DGX). Sono due `Z:` diversi su due macchine diverse.

### Se i mount sshfs si rompono

```bash
# stato (6 mount dovrebbero essere active)
systemctl --user status 'home-jagones-win_disks-*.mount' | head -30

# rimontare uno specifico (es. CC)
systemctl --user restart home-jagones-win_disks-CC.mount

# rifare tutto da zero
systemctl --user daemon-reload
for m in CC DD EE FF GG win_home; do
  sudo -u jagones systemctl --user restart home-jagones-win_disks-$m.mount
done

# se Tailscale giù: sshfs non riparta, montare manualmente
# (in questo caso usare il path CIFS /mnt/win-c..f SE si è in LAN)
```

## ⚠️ REGOLA VELOCITÀ: preferisci MCP filesystem, MAI `exec` su SSHFS

I mount sshfs (`/home/jagones/win_disks/CC`, etc.) sono **lenti** perché
ogni operazione attraversa la rete (Tailscale cifrato). Eseguire
`find`, `ls -R`, `grep -r` o `cat` di file grandi via `exec` su path
sshfs può richiedere **minuti** e bloccare il turno.

**SEMPRE usare i tool del MCP filesystem di OpenClaw** (14 tools, paths
`/home/jagones`, `/home/jagones/win_disks/{CC,DD,EE,FF,GG,win_home}`
esplicitamente in allowlist). Sono pensati per I/O file-oriented e
molto più reattivi:

| Invece di... | Usa |
|--------------|-----|
| `exec "ls /home/jagones/win_disks/CC/Users/giova"` | `mcp__filesystem__list_directory` |
| `exec "cat /home/jagones/win_disks/FF/file.txt"` | `mcp__filesystem__read_text_file` |
| `exec "find ... -iname Android*"` su SSHFS | `mcp__filesystem__search_files` |
| `exec "mkdir /home/jagones/win_disks/CC/Users/giova/x"` | `mcp__filesystem__create_directory` |
| `exec "echo ... > /home/jagones/win_disks/..."` | `mcp__filesystem__write_file` |
| `exec "sed -i ... file"` | `mcp__filesystem__edit_file` |

`exec` resta valido SOLO per:
- avviare/fermare servizi (systemctl, ssh)
- montare/smontare dischi (mount, umount, fusermount)
- operazioni che richiedono rete/comandi shell complessi
- NIENTE `find`, `ls -R`, `cat`, `grep -r` su path `/home/jagones/win_disks/*`

Verifica allowlist MCP filesystem:
```bash
ssh dgx "openclaw mcp probe filesystem"   # deve dire "14 tools"
```

## Troubleshooting rapido

| Sintomo | Causa probabile | Fix |
|---------|-----------------|-----|
| `ssh win` hangs da fuori casa | Tailscale giù sul DGX | `sudo tailscale status` → ri-login |
| `ssh win` hangs da fuori casa (2) | Tailscale giù sul **Windows** | `tailscale status` su Windows (PowerShell) |
| `Permission denied (publickey)` | Chiave non autorizzata su Windows | Verificare `~/.ssh/authorized_keys` in `C:\Users\giova\.ssh\` |
| `Connection refused` su porta 22 | Servizio OpenSSH Windows non attivo | `Get-Service sshd` su Windows, `Start-Service sshd` |
| `Connection timed out` su `ssh desktop` | PC Windows non in LAN | Stessa rete WiFi? PC acceso? |
| `Host key verification failed` | Known hosts corrotto | `ssh-keygen -R desktop-71niuhh` o `ssh-keygen -R 192.168.1.5` |
| Multiplexing stuck (comando si blocca) | Socket socket orfano | `rm ~/.ssh/sockets/giova@desktop-71niuhh-22` |
| `ssh win` da in casa: lentissimo | Sta passando per Tailscale invece di LAN | Forzare `ssh desktop` |

## Verifica veloce della connettività

```bash
# da DGX, test in <1s:
ssh -o ConnectTimeout=3 -o BatchMode=yes win "echo OK_win"
ssh -o ConnectTimeout=3 -o BatchMode=yes desktop "echo OK_desktop"
ssh -o ConnectTimeout=3 -o BatchMode=yes win-ts "echo OK_win-ts"
```

Se tutti e 3 rispondono, la connettività è sana. Se solo `desktop`
risponde in casa, controllare Tailscale. Se solo `win-ts` risponde da
fuori casa, controllare MagicDNS (`tailscale ping desktop-71niuhh`).
