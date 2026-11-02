---
name: mod-downloader
description: Scarica mod da NexusMods e LoversLab col browser builtin OpenClaw, verifica i magic bytes e sposta i file in destinazione. Usala per richieste tipo scaricami questa mod, ultima versione di X, prendi il file Y da LL/Nexus.
---

# mod-downloader

Flussi testati su DGX (browser builtin via CDP, profilo openclaw, logins remember-me LL e Nexus attivi nel profilo).

## Trigger Telegram (e chat)
- Messaggi tipo "scaricami <mod>", "scarica la mod X", "prendi Y da LL/Nexus" → invoca QUESTA skill, non improvvisare flussi paralleli.
- Default: The Sims 4. Sito: Nexus se non specificato; LL se richiesto o se il file esiste solo su LL.
- Destinazione default: `/home/jagones/sandbox-mission/mods/<nexus|ll>/`.
- Se il sito richiede decisioni (quale file, quale versione): scegli il primo compatibile, dichiaralo nel report e vai avanti. Non fermarti a chiedere.

## Regole di velocita (obbligatorie, non negoziabili)
- Massimo 2 snapshot prima di agire. VIETATO vagliare le dimensioni dei file: scegli il primo file compatibile e procedi.
- Usa le azioni browser in batch quando possibile (piu act in una chiamata).
- Download non partito entro 90 secondi: documenta l errore esatto e passa oltre. Massimo 2 retry per passo.
- Questi sono passi meccanici: non serve reasoning esteso.

## NexusMods
1. URL canonico della mod SENZA /games/: `https://www.nexusmods.com/thesims4/mods/<id>` (con /games/ va in 404).
2. Tab Files → click su `Manual download`. Con account free a volte compare la pagina slow download: resta lì, il download parte da solo; in alcuni casi la coda salta del tutto ed e diretto.
3. Se un click restituisce element not found: snapshot fresco e ripeti UNA volta.

## LoversLab (Invision Community)
1. Check login: `#elUserLink` presente con lo username (snapshot o evaluate). Se assente, apri https://www.loverslab.com/ e documenta lo stato.
2. Flusso download: il click su `Download this file` spesso NON fa nulla → naviga DIRETTAMENTE `<url-pagina>/?do=download`:
   - Caso A: pagina "Download your files" con la lista allegati → scegli il link con `csrfKey` (il param `r=<fileId>` distingue gli allegati) e navigalo.
   - Caso B: la navigazione del download si interrompe con errore tipo `ERR_ABORTED` = SUCCESSO, il file e parto. Non riprovare.
3. Nomi interni: Invision salva nomi tipo `1016.zip`, o `Non confermato XXX.crdownload` che completa e si rinomina → identifica il file NUOVO in `/tmp/openclaw/downloads` per mtime, MAI dal nome atteso.
4. Se il link rimanda a Patreon o altro esterno: file NON scaricabile, documenta e passa a un altro file.
5. Ricerca contenuti: la site-search di LL e inaffidabile → naviga diretto le categorie: `https://www.loverslab.com/files/category/<id>-<slug>/?sortby=title&sortdirection=asc&page=N`. Categorie TS4 note: `161-the-sims-4`, `174-wickedwhims`, `201-animations-wickedwhims`, `202-animations-other`.
6. Stale reads: se una navigazione fallisce, lo snapshot successivo puo mostrare la pagina PRECEDENTE: verifica la coerenza nome ↔ link prima di cliccare.

## Dopo il download (sempre)
1. I file arrivano SOLO in `/tmp/openclaw/downloads/` (il browser rifiuta path esterni: e by design).
2. Verifica il tipo con exec: `od -A x -t x1z -N 8 <file>` → `50 4b` = zip, `52 61 72` = rar, `37 7a` = 7z, `44 42 50 46` = package Sims.
3. Sposta in destinazione con exec (o con il server MCP filesystem se disponibile): `mkdir -p <dest> && mv /tmp/openclaw/downloads/<file> <dest>/`.
4. Report finale: percorso destino, dimensione byte, magic bytes trovato, sito di provenienza, errori eventuali.
