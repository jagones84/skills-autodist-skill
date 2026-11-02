---
name: "state-inspector"
description: "Inspects selected, configured, runtime, and evidence state layers and reports coherence or mismatch. Use when the user asks what is really active, whether state is stale, or which layer is the source of truth."
---

# State Inspector

## Scopo

Questa skill ispeziona i layer di stato del workspace e produce un report coerente su:

- `requested`
- `selected`
- `configured`
- `effective runtime`
- `observed evidence`

Usarla quando il problema principale non e' ancora "sistemare Telegram", ma capire
quale stato esiste davvero, quale fonte di verita' valga per la domanda corrente e
quale mismatch sia presente.

## Source Of Truth

- `docs/architecture/state-coherence-model.md` definisce layer, invarianti e classi di mismatch.
- `docs/architecture/verification-contract.md` definisce come dichiarare `DONE` o `BLOCKED`.
- Questa skill non sostituisce skill di esecuzione o di change: chiarisce lo stato.

Se questo file e il modello architetturale divergono, prevale
`docs/architecture/state-coherence-model.md`.

## Quando Invocarla

Invocare questa skill quando l'utente chiede o implica una di queste domande:

- "quale modello e' davvero attivo?"
- "Telegram dice X ma il backend sembra Y"
- "lo stato e' stantio?"
- "qual e' la fonte di verita'?"
- "selected, configured e runtime sono allineati?"
- "questo mismatch e' reale o solo visivo?"

Non usarla come skill primaria se il problema e' chiaramente:

- una timeline da ricostruire dai log: usare `log-forensics`
- un incidente Telegram da triagiare end-to-end: usare `telegram-ops-debug`
- uno switch di modello o un cambio runtime da eseguire: usare la skill operativa specifica

## Obiettivo

Produrre un report di stato che separi chiaramente i layer e non li collassi.

Output minimo atteso:

```text
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
source of truth:
- requested: ...
- selected: ...
- configured: ...
- effective runtime: ...
- observed evidence: ...
next action: ...
```

## Procedura Standard

1. Identifica la domanda reale.
2. Mappa la domanda al layer in scope.
3. Leggi prima la fonte primaria del layer in scope.
4. Leggi poi i layer adiacenti per trovare divergenze.
5. Classifica il risultato:
   - `none` se non esiste mismatch dimostrato tra i layer rilevanti
   - `M1` se `selected != effective runtime`
   - `M2` se `configured default != effective runtime`
   - `M3` se `selected != configured default`
   - `M4` se l'evidenza osservata e' in ritardo rispetto al live
6. Restituisci il report separando fatti, fonti e interpretazione.

## Ordine Di Ispezione Consigliato

Segui questo ordine salvo motivi forti per cambiarlo:

1. `requested`
2. `effective runtime`
3. `configured`
4. `selected`
5. `observed evidence`

Razionale:

- il runtime live e' la fonte primaria per il presente operativo
- config e sessione spiegano il perche' del mismatch
- i log servono per timeline e causalita', non per definire il presente se il live e' leggibile

## Mappa Rapida Delle Fonti

- `requested`: prompt, comando, richiesta utente
- `selected`: session metadata, card/status basati su sessione, override `/model`
- `configured`: `openclaw.json` e config live caricata
- `effective runtime`: `/health`, `/v1/models`, stato servizio, porta attiva
- `observed evidence`: log gateway, NDJSON, messaggi di debug, trace storiche

## Guardrail

- non usare un messaggio `/status` come fonte primaria universale
- non usare log storici per descrivere il presente senza dichiarare il timestamp
- non dichiarare "allineato" senza aver confrontato almeno `selected`, `configured` ed `effective runtime`
- se il live non e' leggibile, dillo esplicitamente e riduci la fiducia della conclusione
- se manca la prova minima, chiudi in `BLOCKED`

## Classi Di Mismatch Canoniche

### none

I layer in scope risultano allineati oppure non emerge alcuna divergenza canonica dimostrata.

### M1

`selected != effective runtime`

Esempio:

- UI o metadata di sessione presentano un modello diverso da quello realmente servito

### M2

`configured default != effective runtime`

Esempio:

- il config live indica un default che il servizio non sta servendo

### M3

`selected != configured default`

Esempio:

- chat corrente in override rispetto al default globale

### M4

L'evidenza osservata e' in ritardo rispetto al live.

Esempio:

- log, card o messaggi storici vengono letti come prova del presente

Se manca accesso credibile alla fonte primaria del layer richiesto:

- non inventare una classe parallela
- dichiara il limite esplicitamente
- chiudi l'esito finale in `BLOCKED` se il layer richiesto non e' dimostrabile

## Integrazione Con Altre Skill

- passa a `telegram-ops-debug` se il problema richiede riproduzione, triage e verifica del flusso Telegram
- passa a `log-forensics` se serve una timeline o correlazione forte di log
- passa alla skill di cambio modello solo se l'utente chiede un'azione correttiva sul runtime

## Template Di Risposta

```text
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

source of truth:
- requested: ...
- selected: ...
- configured: ...
- effective runtime: ...
- observed evidence: ...

assessment:
- ...

next action:
- ...
```
