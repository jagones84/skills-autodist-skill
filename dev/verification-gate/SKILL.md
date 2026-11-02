---
name: "verification-gate"
description: "Applica il contratto di chiusura con Decision, Evidence, Verification e Residual Risk. Usare quando un task modifica file, config, runtime o comportamento e prima di dichiarare DONE."
---

# Verification Gate

## Scopo

Questa skill applica il gate di chiusura dei task del workspace.
Non serve a fare il lavoro al posto del task principale: serve a decidere se il lavoro
puo' essere dichiarato `DONE` oppure deve restare `BLOCKED`.

## Source Of Truth

- `docs/architecture/verification-contract.md` definisce output contract, regole decisionali, task class e prova minima.
- Questo file descrive solo quando invocare `verification-gate` e come applicare il contratto senza ridefinirlo.
- Se questo file e il contratto divergono, prevale `docs/architecture/verification-contract.md`.

## Quando Invocarla

Invocare questa skill quando:

- il task crea o modifica file
- il task aggiorna runbook, README, AGENTS o skill
- il task cambia config, script o comportamento
- il task tocca runtime, servizi o stato live
- si sta per rispondere con una chiusura finale

Non invocarla per:

- pura discussione o brainstorming senza cambi applicati
- domande informative senza decisione finale di completamento

## Procedura Minima

1. Leggi `docs/architecture/verification-contract.md`.
2. Scegli una sola `Task Class` seguendo il contratto.
3. Esegui la prova minima richiesta dal contratto per quella classe.
4. Costruisci la risposta finale con i quattro blocchi obbligatori nell'ordine corretto.
5. Se manca evidenza credibile o la prova minima non sostiene la conclusione, chiudi in `BLOCKED`.

## Formato Di Uscita

```text
Decision: DONE | BLOCKED (Task Class X)
Evidence:
- ...
- ...

Verification:
- ...
- ...

Residual Risk:
- ...
- ...
```

## Guardrail Minimi

- non sostituire `Evidence` con una semplice lista di file se manca la verifica
- non sostituire `Verification` con intenzioni o promesse
- non omettere il `Residual Risk`, anche quando sembra basso
- non usare questa skill per ridefinire task class o prova minima fuori dal contratto

## Esempio Rapido

Per un task di sola documentazione:

```text
Decision: DONE (Task Class A)
Evidence:
- aggiornato `README.md`
- aggiornato `.agent/README.md`
- aggiornato `workspace/skills/verification-gate/SKILL.md`

Verification:
- ispezionati i file modificati
- controllati i riferimenti a `docs/architecture/verification-contract.md`
- verificata la coerenza dei quattro campi obbligatori con il contratto

Residual Risk:
- nessuna verifica runtime richiesta per una modifica di sola documentazione
```
