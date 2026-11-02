---
name: "telegram-ops-debug"
description: "Debugs Telegram-side operational issues such as wrong status, stale /model state, loops, and command anomalies. Use when the incident starts from Telegram behavior and needs triage across session, config, runtime, and logs."
---

# Telegram Ops Debug

## Scopo

Questa skill e' la procedura operativa per incidenti e anomalie che emergono prima di
tutto su Telegram.

Esempi tipici:

- `/status` incoerente con il backend
- `/model` che sembra non avere effetto
- loop di stato o messaggi ripetuti
- mismatch tra card/status e modello servito
- output mancanti o comportamento Telegram apparentemente stantio

Questa skill non presume che il problema sia nel runtime, nella sessione o nei log:
serve a triagiare il sintomo Telegram e a capire quale layer sia davvero guasto o solo
fuorviante.

## Source Of Truth

- `docs/architecture/state-coherence-model.md` per la semantica dei layer e dei mismatch
- `docs/runbooks/telegram-model-state-debug.md` per il runbook pratico focalizzato sul modello/stato
- `docs/architecture/verification-contract.md` per il formato di chiusura

Se questo file e il runbook divergono sulla procedura specifica di debug Telegram,
prevale il runbook.

## Quando Invocarla

Invocare questa skill quando il sintomo primario arriva da Telegram:

- utente confuso da `/status`
- sessione Telegram apparentemente sfasata dal backend
- dubbio su pin di chat, override o presentazione fuorviante dei layer
- sospetto loop o ripetizione legato a stato sessione
- debug di comando Telegram che sembra corretto a livello backend ma errato lato chat

Non usarla come skill primaria quando:

- il task e' solo "capire quale modello e' attivo": usare `state-inspector`
- il task e' solo "ricostruire dai log": usare `log-forensics`
- il task e' solo "cambia modello": usare la skill di switch dedicata

## Obiettivo

Produrre un triage affidabile che dica:

1. qual e' il sintomo
2. quale layer e' coinvolto
3. se il problema e' di presentazione, sessione, config, runtime o timeline
4. quale prossimo passo e' corretto

## Procedura Standard

1. Cattura il sintomo in una frase precisa.
2. Definisci l'aspettativa corretta dell'utente.
3. Verifica se il problema riguarda:
   - selected state
   - configured state
   - effective runtime
   - observed evidence
4. Leggi le fonti primarie nell'ordine minimo utile:
   - runtime live
   - config live
   - stato sessione
   - log e messaggi storici
5. Classifica l'incidente:
   - `none` se non esiste mismatch dimostrato tra i layer rilevanti
   - `M1` se `selected != effective runtime`
   - `M2` se `configured default != effective runtime`
   - `M3` se `selected != configured default`
   - `M4` se l'evidenza osservata e' in ritardo rispetto al live
6. Restituisci i fatti separando sempre "cio' che Telegram mostra" da "cio' che il backend serve".

## Checklist Operativa

Per un debug Telegram standard, controlla almeno:

1. cosa Telegram mostra all'utente
2. quale modello il backend serve ora
3. quale default e' pubblicato nel config
4. se la sessione corrente e' pinnata a un override
5. se i log mostrano uno switch recente o differito

## Guardrail

- non trattare il testo mostrato da Telegram come prova definitiva del runtime
- non trattare il runtime live come prova del pin di chat
- se una risposta Telegram e' generata da session metadata, dichiaralo esplicitamente
- se lo switch e' differito, non chiamarlo "gia' applicato" senza una verifica post-switch
- se il sintomo non e' riproducibile live, usa `log-forensics` per la timeline invece di improvvisare

## Classi Di Mismatch Canoniche

### none

Non esiste mismatch dimostrato tra i layer rilevanti per la domanda corrente.

Usarlo solo quando:

- hai confrontato almeno i layer necessari
- non emergono divergenze canoniche `M1`-`M4`

### M1

`selected != effective runtime`

Esempio tipico:

- Telegram o metadata di sessione mostrano un modello diverso da quello realmente servito dal backend

### M2

`configured default != effective runtime`

Esempio tipico:

- il config pubblica un default che il servizio non sta servendo davvero

### M3

`selected != configured default`

Esempio tipico:

- la chat corrente e' pinnata a un override diverso dal default globale

### M4

L'evidenza osservata e' in ritardo rispetto al live.

Esempio tipico:

- un messaggio Telegram, una card o un log storico vengono letti come se descrivessero ancora il presente

Se la prova minima manca, non inventare una classe parallela:

- dichiara l'incertezza nel corpo del report
- chiudi in `BLOCKED` se il layer richiesto non e' dimostrabile

## Integrazione Con Altre Skill

- usa `state-inspector` per formalizzare i layer e la classe di mismatch
- usa `log-forensics` per timeline, correlazioni e verifica ipotesi da log
- usa la skill di model switch solo se la correzione richiesta e' cambiare il runtime

## Output Minimo Atteso

```text
symptom: ...
user expectation: ...
telegram shows: ...
requested: ...
requested source of truth: ...
selected: ...
selected source of truth: ...
configured: ...
configured source of truth: ...
effective runtime: ...
effective runtime source of truth: ...
observed evidence: ...
observed evidence source of truth: ...

mismatch class: none | M1 | M2 | M3 | M4

next action:
- ...
```
