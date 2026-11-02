---
name: "openclaw-nuke-sessions"
description: "Cancella in modo sicuro una o piu' sessioni del coordinator (o altri agent) direttamente dal DB SQLite, aggirando il bug di `openclaw sessions delete` su 2026.9.x che restituisce 'disk I/O error' mascherando FK violation multi-tabella. Usare quando l'utente vuole ripulire la lista sessioni da test, voxta residue, sessioni orfane o sperimentali senza toccare le canoniche (heartbeat, persona, conversazioni attive)."
---

# OpenClaw Nuke Sessions

## Scopo

Procedura operativa per cancellare N sessioni "a parte" dal database SQLite del
coordinator (o altro agent) in modo **atomico**, **verificabile** e **reversibile**.

Lo script `openclaw sessions delete` incluso in OpenClaw 2026.9.x fallisce con
`Error: disk I/O error: code=ERR_SQLITE_ERROR` quando le sessioni hanno righe
collegate in piu' di una tabella (FK violation mascherata). Questa skill fornisce
l'alternativa funzionante via SQL diretto.

## Source Of Truth

- Schema DB: `agents/<agent>/agent/openclaw-agent.sqlite` (SQLite WAL, FK attive)
- Tabella di verita' per la lista sessioni: `session_windows` (session_id + session_key + status)
- Mapping conversazione: `session_conversations` (session_id <-> conversation_id)
- Per la GUI: la lista delle sessioni in `http://localhost:18789/#token=...` riflette `session_nodes` (sidebar) + `session_windows` (status)

## Quando Invocarla

Usare quando:

- la GUI mostra sessioni "a parte" che l'utente vuole eliminare (test, voxta, prompt one-shot)
- `openclaw sessions delete <key>` fallisce con "disk I/O error"
- servono cancellazioni massive (N > 1) senza rischiare mezze-cancellazioni
- si vuole un audit post-delete (cosa e' stato cancellato, cosa e' rimasto)

Non usarla per:

- "esplorare" la lista sessioni: usare `state-inspector`
- capire perche' una sessione e' in stato `failed`: usare `log-forensics`
- modificare il contenuto di una sessione senza cancellarla: gestire via OpenClaw CLI/GUI

## Prerequisiti

- `openclaw-gateway.service` (systemd user). Comandi canonici:
  - `openclaw daemon start` (avvia; safe anche con gateway gia' enabled ma fermo)
  - `openclaw daemon stop --force` (ferma)
  - `openclaw daemon status` (verifica stato + log path)
  - `openclaw daemon restart` (riavvio)
  - **NON** usare `start_openclaw_withbrows.sh`: referenzia `~/.openclaw/moltbot_gateway_start.sh` che NON esiste piu' sul disco (rimosso 2026-09-08)
- `sqlite3` installato e disponibile nel PATH lato DGX
- Working directory lato DGX scrivibile (default `/home/jagones/.openclaw/skills/openclaw-nuke-sessions/scripts/`)
- **Permesso utente** a cancellare le sessioni (le sessioni di sistema tipo `agent:coordinator:main:heartbeat` o
  `agent:coordinator:telegram:direct:...:heartbeat` NON vanno toccate, sono gestite dal runtime)

## Procedura Standard

### 1. Identificare le sessioni target

Ottenere la lista corrente e filtrare le sessioni "a parte" da cancellare:

```bash
ssh dgx "bash ~/.openclaw/skills/openclaw-nuke-sessions/scripts/list_sessions.sh"
```

Output: tabella con `session_id`, `session_key` (abbreviata), `status`, `primo_msg`
(primi 80 caratteri del primo evento user). Le sessioni di sistema hanno sempre
una `session_key` con prefisso `agent:coordinator:...:heartbeat`, `cron:`, o
`cccc-bridge`. Le sessioni "a parte" da cancellare di solito sono voxta, openai-user
single-shot, o openai puro (senza suffisso).

### 2. Conferma con l'utente

Prima di cancellare, elencare le sessioni target all'utente e chiedere conferma
esplicita. Le 5 categorie da NON toccare:

- `agent:coordinator:main:heartbeat` (heartbeat principale)
- `agent:coordinator:telegram:direct:407582054:heartbeat` (heartbeat Telegram)
- `agent:coordinator:openai-user:voxta-*` con prefisso persona (Vexa, Scarlett) — sono le **canoniche**
- `agent:coordinator:cccc-bridge` (bridge CCCC)
- `agent:coordinator:cron:*` (job schedulati)

### 3. Dry-run

Generare lo script SQL in dry-run e mostrarne il contenuto all'utente:

```bash
ssh dgx "bash ~/.openclaw/skills/openclaw-nuke-sessions/scripts/nuke_sessions.sh \
  --ids 'c697cd0c-5a79-424c-8d62-fe8ebd5b23a8 47e2bedf-106c-406f-b399-d7d63cc74ad7' \
  --keys 'agent:coordinator:openai-user:voxta-e3b0c44298fc-20260908 agent:coordinator:openai:f5db2b71-cf06-4f26-aadd-03b070ab5173' \
  --dry-run"
```

Lo script scrive in `/tmp/nuke_preview.sql` (NON tocca il DB) e mostra le righe
`DELETE FROM ...` che verrebbero eseguite.

### 4. Verifica lock sul DB

```bash
ssh dgx "fuser ~/.openclaw/agents/coordinator/agent/openclaw-agent.sqlite"
```

Se l'ouput non e' vuoto, il gateway sta lockando il DB. **NON serve fermare il
gateway** per la DELETE: lo script usa `PRAGMA foreign_keys=OFF` e SQLite WAL
consente letture/scritture concorrenti; il rischio e' solo se il gateway sta
scrivendo nelle tabelle che tocchiamo durante la DELETE, ma la transazione
`BEGIN/COMMIT` rende l'operazione atomica lato nostro e lato gateway le nuove
scritture vengono serializzate dopo il nostro COMMIT. Per ambienti con
concorrenza elevata, fermare prima con `openclaw daemon stop --force`.

### 5. Esecuzione (con backup automatico)

```bash
ssh dgx "bash ~/.openclaw/skills/openclaw-nuke-sessions/scripts/nuke_sessions.sh \
  --ids '...' \
  --keys '...'"
```

Lo script:
1. Crea backup del DB in `openclaw-agent.sqlite.bak-pre-nuke-<TS>` (52 MB tipico)
2. Verifica che il DB sia libero (no lock attivi)
3. Genera il file SQL in `~/.openclaw/tmp/nuke_<TS>.sql`
4. Esegue `sqlite3 < sqlfile` con `PRAGMA foreign_keys=OFF` + `BEGIN TRANSACTION` + COMMIT
5. `PRAGMA wal_checkpoint(TRUNCATE)` finale
6. Mostra conteggi pre/post per conferma

### 6. Verifica post-delete

```bash
ssh dgx "bash ~/.openclaw/skills/openclaw-nuke-sessions/scripts/verify_clean.sh \
  --keys 'agent:coordinator:openai-user:voxta-e3b0c44298fc-20260908 ...'"
```

Conta i record rimasti per le chiavi cancellate (deve essere **0** in tutte le
tabelle) e per le canoniche (deve essere **> 0**).

### 7. Riavvio gateway (se fermato al punto 4)

```bash
ssh dgx "openclaw daemon restart"
```

## Schema DB Di Riferimento

Il DB `openclaw-agent.sqlite` ha 25+ tabelle rilevanti per le sessioni. Tre
categorie di colonna per identificare una sessione:

| Categoria | Colonne tipiche | Tabelle |
|---|---|---|
| `session_id` (UUID) | TEXT NOT NULL | `session_conversations`, `transcript_events`, `session_windows`, `session_transcript_active_events`, `session_transcript_index_state`, `session_transcript_archives`, `session_transcript_fts`, `transcript_event_identities`, `transcript_rewrite_watermarks`, `trajectory_runtime_events`, `memory_session_tombstones`, `acp_parent_stream_events`, `context_engine_turn_outbox` |
| `session_key` (stringa) | TEXT NOT NULL (PK) | `session_nodes` (PK), `session_participants`, `session_progress_cards`, `session_suggestions`, `message_tool_run_outcomes`, `session_members`, `board_tabs`, `board_widgets`, `heartbeat_outcomes` |
| Entrambe | entrambe presenti | `session_windows`, `session_transcript_archives`, `session_pending_inputs`, `session_goal_operations`, `memory_entry_origins` |
| `conversation_id` | TEXT NOT NULL | `conversation_deliveries`, `conversations` |
| Speciali | `source_session_id`, `current_session_id` | `standing_intents`, `session_nodes` |

## Tabelle Coperte Dalla Cancellazione (25+)

Tutte le DELETE sono coperte dallo script `nuke_sessions.sh`. Per ispezione
manuale, l'elenco completo e' visibile nel sorgente.

## Output Dello Script `nuke_sessions.sh`

```text
[nuke <TS>] Check che DB sia libero
  DB libero.
[nuke <TS>] Backup DB -> openclaw-agent.sqlite.bak-pre-nuke-<TS>
[nuke <TS>] Mapping conversation_id residue
  conversation_id: <lista o "nessuno">
[nuke <TS>] Genero SQL file: ~/.openclaw/tmp/nuke_<TS>.sql
[nuke <TS>] Eseguo SQL
[nuke <TS>] sqlite3 exit: 0

[nuke <TS>] VERIFICA POST-DELETE
  session_conversations: sid=0  skey=n/a
  session_windows: sid=0  skey=0
  transcript_events: sid=0  skey=n/a
  ...

[nuke <TS>] VERIFICA canoniche INTATTE
  session_windows: canon_sid=5  canon_skey=31
  ...
```

## Guardrail

- **SEMPRE** backup prima di qualsiasi DELETE: lo script lo crea automaticamente
- **SEMPRE** verifica lock con `fuser` prima di procedere
- **SEMPRE** conferma esplicita dell'utente con lista delle sessioni target
- **MAI** cancellare sessioni con `session_key` che contiene `heartbeat`, `cron:`, `cccc-bridge`, o i prefissi persona canonici (Vexa `voxta-4b3df473`, Scarlett `voxta-9caa8e59`, Vexa persona `voxta-547ec369`)
- **MAI** eseguire lo script con il gateway attivo se vedi FK violation o lock
- In caso di dubbio, **NON procedere**: chiedi conferma elencando le sessioni target
- Dopo la cancellazione, **VERIFICA** sempre che le canoniche siano intatte prima di riavviare il gateway

## Rollback

Il backup `openclaw-agent.sqlite.bak-pre-nuke-<TS>` contiene lo stato pre-delete.
Per ripristinare:

```bash
# 1. Fermare il gateway
ssh dgx "pkill -f 'openclaw.*gateway' || true"

# 2. Ripristinare il backup
ssh dgx "cp -a ~/.openclaw/agents/coordinator/agent/openclaw-agent.sqlite.bak-pre-nuke-<TS> \
            ~/.openclaw/agents/coordinator/agent/openclaw-agent.sqlite"

# 3. Riavviare il gateway
ssh dgx "openclaw daemon restart"
```

**IMPORTANTE**: il rollback sovrascrive TUTTO lo stato del DB, incluse eventuali
modifiche avvenute DOPO la cancellazione. Se nel frattempo l'utente ha fatto
altro, valutare un ripristino parziale con INSERT INTO ... SELECT dalle tabelle
del backup (procedura manuale, non script-ready).

## Relazione Con Altre Skill

- `state-inspector` per capire **quali** sessioni sono in stato divergente prima di cancellare
- `log-forensics` per ricostruire **perche'** una sessione e' finita in stato `failed` o `done` anomalo
- `verification-gate` per chiudere il task dopo la cancellazione con la struttura Decision/Evidence/Verification/Residual Risk

## Esempio Rapido (reale, 2026-09-08)

Cancellazione di 6 sessioni "a parte" (PUMPKIN, BLUEFALCON x2, voxta prompt,
"Test: una parola") mantenendo Vexa, Scarlett, persona, 2 heartbeat.

```bash
# 1. Lista
ssh dgx "bash ~/.openclaw/skills/openclaw-nuke-sessions/scripts/list_sessions.sh"

# 2. Conferma utente → "Sì, cancella"

# 3. Esegui
ssh dgx "bash ~/.openclaw/skills/openclaw-nuke-sessions/scripts/nuke_sessions.sh \
  --ids 'c697cd0c-5a79-424c-8d62-fe8ebd5b23a8 \
         47e2bedf-106c-406f-b399-d7d63cc74ad7 \
         57b7fb7a-4a98-40cd-94f4-dfa5aede1201 \
         75d9b6bd-314a-4822-a9e6-beee3d665d5c \
         61826e3e-5ee1-4b2b-93c8-14a561eb0376 \
         6111f8b4-eae8-4892-b4d1-952ff718b5c2' \
  --keys 'agent:coordinator:openai-user:voxta-e3b0c44298fc-20260908 \
         agent:coordinator:openai:f5db2b71-cf06-4f26-aadd-03b070ab5173 \
         agent:coordinator:openai:8dc1ae1e-6459-4def-aba5-6e653e35132c \
         agent:coordinator:openai:7479e8a0-d8e8-40a5-9960-36ecadbbb459 \
         agent:coordinator:openai-user:voxta-e802d959198f-20260908 \
         agent:coordinator:openai-user:voxta-4cc574bc22ce-20260908'"

# Risultato: 6 sessioni a 0 in 14 tabelle, 5 canoniche intatte, backup 52 MB salvato
```

## File Di Riferimento Interni

- Script principale: `scripts/nuke_sessions.sh`
- Lista sessioni: `scripts/list_sessions.sh`
- Verifica post-delete: `scripts/verify_clean.sh`
- Incident originale e mappatura completa tabelle: `~/.openclaw/.agent/HANDOFF.md` sezione "[2026-09-08 09:58] CLEANUP 6 sessioni 'a parte' — RISOLTO"

## Limitazioni Note

- Funziona SOLO sul DB del coordinator (path di default). Per altri agent, passare `--db <path>`
- Non gestisce transazioni concorrenti: se due script girano in parallelo, le DELETE possono interleaved
- Il `PRAGMA foreign_keys = OFF` e' necessario per evitare l'errore, MA significa che le FK non sono controllate durante la DELETE: se una tabella viene aggiunta in futuro e non e' nello script, la riga orfana restera' (verificare con `verify_clean.sh` post-delete)
- La GUI potrebbe richiedere F5 per riflettere le cancellazioni (cache locale)
