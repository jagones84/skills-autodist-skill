---
name: termux-ssh
description: SSH e SCP tra DGX Spark, PC Windows e Android via Termux + Tailscale. Trigger: connetti telefono, ssh termux, manda file al cellulare, entra nel terminale del cell, connect to phone, termux ssh, send file to phone.
---

# Termux SSH

Connessione SSH persistente DGX/PC -> OnePlus 15R via Termux + Tailscale.
Porta 8022 fissa, stesso comando in WiFi e 5G.

## Identita (OnePlus 15R)

| Parametro | Valore |
|---|---|
| Host | oneplus-15r via MagicDNS (IP 100.67.181.54, usa sempre il nome) |
| Utente Termux | u0_a66 |
| Porta SSH | 8022 |
| Home Termux | /data/data/com.termux/files/home |
| Download | ~/storage/downloads/ (dopo termux-setup-storage) |
| Password | MAI in chiaro qui: file ~/.openclaw/credentials/termux.pass (mode 600) |

## Comandi dal DGX

```bash
PASS=$(cat ~/.openclaw/credentials/termux.pass)
sshpass -p "$PASS" ssh -p 8022 -o StrictHostKeyChecking=no u0_a66@oneplus-15r "uptime"
sshpass -p "$PASS" scp -P 8022 -o StrictHostKeyChecking=no file.mp4 u0_a66@oneplus-15r:~/storage/downloads/
```

## Comandi da PC Windows (password chiesta una volta, poi key)

```powershell
scp -P 8022 C:\file.mp4 u0_a66@oneplus-15r:~/storage/downloads/
```

## Setup permanente (una volta, sul telefono)

1. Termux: `pkg install openssh`, poi `passwd`, poi `termux-setup-storage`
2. Termux a ogni avvio: `sshd` + `termux-wake-lock` (resta vivo a schermo spento)
3. Android: Tailscale come Always-on VPN; togli ottimizzazione batteria a Tailscale e Termux

## Se cade (in ordine, fermati al primo che funziona)

1. Aspetta 30 secondi (auto-reconnect PC/DGX)
2. Apri l app Tailscale sul telefono per 5 secondi (risveglia rete + sshd)
3. `tailscale status` su DGX/PC: se oneplus-15r risulta offline serve intervento sul telefono
4. Se online ma ssh refused: riapri Termux sul telefono e dai `sshd`
