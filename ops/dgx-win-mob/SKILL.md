---
name: "dgx-win-mob"
description: "Network and connectivity reference for the DGX Spark ↔ Windows PC ↔ OnePlus 15R mesh. Covers SSH shortcuts (win / win_eth / win-ts), sshfs disk mounts under /home/jagones/win_disks/, ADB wireless via Tailscale (with 5G handover reconnect), Tailscale IP map, and Termux→DGX self-messaging over /dev/tcp. Use when the user asks to connect from any of the three devices to any other, mount Windows drives, run a command remotely, take a phone screenshot, send a message from the phone to the DGX, debug a broken mount, or troubleshoot SSH/ADB access. Triggers: 'ssh windows', 'ssh win', 'ssh win_eth', 'ssh win-ts', 'mount windows disk', 'sshfs', 'collegati al pc windows', 'collegati al cellulare', 'adb', 'screenshot cellulare', 'telegramma cellulare', 'send to dgx', 'messaggio a te stesso', 'termux ssh dgx', 'mostra agli amici', '5g handover', 'tailscale', 'rete dgx win mobile'."
---

# DGX ↔ Windows ↔ Mobile: rete completa

Riferimento unico per la connettività tra i 3 device del setup:

| Device | Ruolo |
|---|---|
| **DGX Spark** (Ubuntu 24.04, GB10) | server principale |
| **Windows PC** (desktop) | workstation |
| **OnePlus 15R** (OxygenOS, Android) | mobile |

Sono tutti sul **Tailscale mesh** + DGX↔Windows hanno anche cavo **ethernet 10GbE** dedicato.

---

## 📍 Mappa IP

| Device | Tailscale | LAN / ETH |
|---|---|---|
| DGX Spark | `100.102.61.23` (`spark-6263`) | `10.0.0.1` (`enP7s7`) |
| Windows PC | `100.76.251.9` (`desktop-71niuhh`) | `10.0.0.2` (`win_eth`) |
| OnePlus 15R | `100.67.181.54` | — (5G/WiFi) |

Convenzione nomi (`/etc/hosts` su DGX):
```
10.0.0.2        win_eth   # Windows via cavo (latenza <1ms)
100.76.251.9    win-ts    # Windows via Tailscale (~3ms)
```

---

## 🖥️ Da DGX → Windows

```bash
# SSH shell
ssh win_eth                           # via cavo ethernet
ssh win-ts                            # via Tailscale mesh
ssh win                               # alias = cavo (vedi ~/.ssh/config)

# Esegui comando singolo (no shell interattiva)
ssh win_eth "ipconfig | findstr IPv4"
ssh win-ts "powershell.exe -NoProfile -Command Get-Process"

# Copia file DGX → Win
scp file.txt giova@win_eth:D:/backup/

# Sincronizza cartella
rsync -avz ~/mydir/ giova@win-ts:/F:/mirror/

# Accedi ai dischi Win già montati in sshfs
ls /home/jagones/win_disks/CC       # = C:\
ls /home/jagones/win_disks/DD       # = D:\
ls /home/jagones/win_disks/EE       # = E:\
ls /home/jagones/win_disks/FF       # = F:\
ls /home/jagones/win_disks/win_home # = C:\Users\giova
```

## 💻 Da Windows → DGX

```powershell
# PowerShell nativo (Win10/11 ha ssh built-in)
ssh jagones@100.102.61.23    # Tailscale (consigliato, sempre)
ssh jagones@spark-6263       # nome Tailscale
ssh jagones@10.0.0.1         # via cavo (solo LAN diretta)

# Copia Win → DGX
scp file.txt jagones@100.102.61.23:~/

# Apri DGX in Windows Terminal pre-impostato
wt -p "DGX-Spark"
```

## 📱 Da DGX → Cell (OnePlus 15R)

```bash
# Imposta alias (metti in ~/.bashrc)
export DEV=100.67.181.54:5555

# Reconnect robusto (5G handover)
adb disconnect $DEV
for i in 1 2 3 4 5; do
  adb connect $DEV && sleep 2
  adb devices | grep -q "device$" && break
done

# Operazioni ADB
adb -s $DEV shell ls /sdcard
adb -s $DEV shell input text "ciao dal dgx"
adb -s $DEV exec-out screencap -p > /tmp/cell.png

# Installa APK
adb -s $DEV install app.apk

# Push/pull file
adb -s $DEV push local.txt /sdcard/Download/
adb -s $DEV pull /sdcard/DCIM/shot.jpg ./shot.jpg
```

## 🪟 Da Windows → Cell

```powershell
# ADB wireless via Tailscale
adb connect 100.67.181.54:5555

# Operazioni ADB normali
adb -s 100.67.181.54:5555 shell ls /sdcard
adb -s 100.67.181.54:5555 push AppName.apk /sdcard/Download/

# Screenshot
adb -s 100.67.181.54:5555 exec-out screencap -p > shot.png

# Oppure da Chrome desktop
chrome://inspect/#devices
```

## 📱 Da Cell → DGX (Termux)

### Setup una tantum (DGX)
```bash
# Listener TCP (singolo processo!)
setsid nc -l -k -p 12345 >> /tmp/cell_messages.log 2>/tmp/cell_err.log </dev/null &
```

### Apri Termux da ADB (DGX → Cell)
```bash
export DEV=100.67.181.54:5555
adb -s $DEV shell am start -n com.termux/.app.TermuxActivity
# unlock schermo OxygenOS
adb -s $DEV shell svc power stayon true
adb -s $DEV shell input keyevent 224          # WAKEUP
adb -s $DEV shell wm dismiss-keyguard        # sblocca
adb -s $DEV shell input tap 540 1200         # focus Termux
```

### Messaggio da Termux (Termux "nudo", senza curl/nc/openssh)
```bash
# Dentro Termux sul cellulare
exec 3<>/dev/tcp/100.102.61.23/12345
echo "CIAO_SONO_TERMUX_SU_5G" >&3
exec 3>&-
```

Oppure con `adb shell input text` dal DGX:
```bash
adb -s $DEV shell "input text 'echo ciao dal dgx'"
```

---

## 🔄 Auto-recovery setup

Lo script `~/Repos/scripts/mount_win_disks.sh` è **idempotente** e gestisce:
- sshfs morti → killa + fusermount -uz + sudo umount -lf
- SSHFS stale FUSE dopo `kill -9` → aspetta kernel GC fino a 130s, poi unshare namespace
- Crea mountpoint freschi se bloccati

Mount persistente al boot:
- `~/.config/systemd/user/win-disks.service` (aspetta network-online + 5s, poi monta)
- `~/.config/systemd/user/win-disks-watchdog.timer` (controlla ogni 5 min)
- `Linger=yes` → user services partono al boot senza login

Riavvio mount manuale:
```bash
bash ~/Repos/scripts/mount_win_disks.sh
```

---

## 🐛 Troubleshooting rapido

| Sintomo | Fix |
|---|---|
| `ssh win_eth` → Permission denied | Controlla `~/.ssh/config.d/win-windows.conf` e che `dgx_to_windows` sia in `~/.ssh/authorized_keys` su Win |
| `ssh win-ts` → "host key verification failed" | `ssh-keyscan -t ed25519 win-ts >> ~/.ssh/known_hosts` |
| `Transport endpoint is not connected` (sshfs) | Aspetta 60-90s (kernel GC) o riavvia DGX |
| ADB `device offline` su 5G | `adb disconnect $DEV; adb connect $DEV; sleep 3` |
| ADB non si connette dopo WiFi → 5G | Apri app Tailscale sul cell (no deep sleep) |
| `win_eth` ping fallisce | Cavo DGX `enP7s7` staccato o Windows spento |
| `win-ts` ping fallisce | Tailscale giù su uno dei due: `sudo tailscale up` |

---

## 📂 File rilevanti

- `/etc/hosts` (DGX) → mapping `win_eth` e `win-ts`
- `~/.ssh/config.d/win-windows.conf` (DGX) → shortcut SSH
- `~/.ssh/dgx_to_windows` (DGX) → chiave ed25519 per Win
- `~/Repos/scripts/mount_win_disks.sh` → mount/refresh sshfs
- `~/.config/systemd/user/win-disks.service` + `.timer` → auto-mount al boot + ogni 5 min
- `/etc/NetworkManager/dispatcher.d/10-win-hosts` → riapplica hosts su link up
- `/etc/sudoers.d/jagones-mountwin` → NOPASSWD per umount (recovery stale FUSE)
