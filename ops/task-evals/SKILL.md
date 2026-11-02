---
name: "task-evals"
description: "Esegue o coordina task eval seed del workspace, usando i workstream 1-3 come source of truth. Usare quando serve valutare task reali su Telegram, model-state, runtime-coherence, log-debug o governance correlata."
---

# Task Evals

## Scopo

Questa skill applica Workstream 4.
Serve a eseguire o coordinare eval task seed reali del workspace, non benchmark sintetici astratti.

La skill non ridefinisce i workstream 1-3.
Li usa come fondazione per misurare:

- task success
- correttezza stato finale
- completezza verifica
- efficienza tool
- latenza
- intervento manuale

## Source Of Truth

- `docs/evals/openclaw-task-evals.md`
- `docs/evals/baseline-scorecard-2026-08.md`
- `docs/evals/tasks/README.md`
- `docs/architecture/verification-contract.md`
- `docs/architecture/state-coherence-model.md`
- `workspace/skills/verification-gate/SKILL.md`
- `workspace/skills/state-inspector/SKILL.md`
- `workspace/skills/telegram-ops-debug/SKILL.md`
- `workspace/skills/log-forensics/SKILL.md`

Se questa skill diverge dai documenti sopra, prevalgono i documenti canonici.

## Quando Invocarla

Invocare questa skill quando serve:

- valutare un task seed del baseline
- confrontare piu' run sullo stesso task reale
- aggiornare la scorecard con esiti osservati o riallinearla editorialmente senza perdere failure mode e note operative
- capire se un task fallisce per outcome, prova o traiettoria
- misurare task Telegram/model-state/runtime/log con una rubrica comune
- revisionare skill o documenti locali per drift normativo rispetto ai workstream 1-3

Non usarla come skill primaria quando il lavoro richiesto e' solo:

- capire lo stato corrente: usare `state-inspector`
- triagiare direttamente un incidente Telegram: usare `telegram-ops-debug`
- ricostruire solo la timeline: usare `log-forensics`
- chiudere un task gia' fatto: usare `verification-gate`

## Procedura Standard

1. Seleziona il `task seed id`.
2. Dichiara la domanda corretta e l'end state atteso.
3. Identifica il workstream dominante.
4. Invoca la skill primaria giusta.
5. Usa skill secondarie solo quando cambiano davvero la diagnosi.
6. Raccogli evidence e verification separate.
7. Assegna i sei punteggi della rubrica.
8. Sintetizza `Failure mode` e `Proof quality`.
9. Chiudi con `verification-gate`.
10. Se richiesto, aggiorna la scorecard.

## Routing Rapido

- task su layer `selected/configured/effective runtime` -> `state-inspector`
- task su sintomo nato in Telegram -> `telegram-ops-debug`
- task su causalita', timeline o ipotesi dai log -> `log-forensics`
- task su validita' della chiusura finale -> `verification-gate`
- `G03` review di skill locale, riferimenti canonici o routing -> `task-evals`, con `verification-gate` solo come chiusura finale
- `G04` aggiornamento di scorecard e seed catalog -> `task-evals`, con `verification-gate` solo come chiusura finale

## Rubrica Obbligatoria

Usa sempre queste sei dimensioni con scala `0-2`:

- `task success`
- `final state correctness`
- `verification completeness`
- `tool efficiency`
- `latency`
- `manual intervention`

## Regole Di Scoring

### Pass minimo

Un task puo' essere valutato come riuscito solo se:

- `task success = 2`
- `final state correctness = 2`
- `verification completeness = 2`

### Failure minimo

Se una delle tre dimensioni sopra e' sotto `2`, il task non e' un successo pieno.

### Proof Quality

Mappa `verification completeness` in modo operativo.
Nella baseline pre-run la stessa etichetta puo' essere usata come aspettativa editoriale della soglia di verifica richiesta dal seed, non come outcome osservato.

- `weak`: manca almeno uno tra fonte primaria appropriata, verifica separata dall'evidence o residual risk proporzionato
- `mixed`: esiste una verifica reale ma copre solo parte dell'end state, usa proxy parziali oppure lascia un gap esplicitato
- `strong`: la conclusione e' sostenuta da fonte primaria appropriata, verifica separata e residual risk coerente con la task class

## Guardrail

- non valutare il task solo dal testo finale
- non chiamare successo un task con stato finale non dimostrato
- non usare la fonte di verita' sbagliata per il layer in scope
- non nascondere loop, retry inutili o tool ridondanti
- non saltare `Residual Risk`
- non aggiornare la scorecard senza annotare il failure mode principale

## Output Minimo Atteso

```text
task: ...
task seed id: ...
workstream dominant: ...

rubric:
- task success: 0|1|2
- final state correctness: 0|1|2
- verification completeness: 0|1|2
- tool efficiency: 0|1|2
- latency: 0|1|2
- manual intervention: 0|1|2

failure mode:
- ...

proof quality: weak | mixed | strong

Decision: DONE | BLOCKED (Task Class X)
Evidence:
- ...

Verification:
- ...

Residual Risk:
- ...
```

## Seed Iniziali Supportati

- `T01` stato runtime effettivo
- `T02` mismatch `/status` vs `/v1/models`
- `T03` override di chat vs default
- `T04` config vs runtime live
- `T05` classificazione mismatch `M1-M4`
- `T06` timeline switch modello
- `T07` mismatch attuale vs evidenza storica
- `T08` `/model` apparentemente ignorato
- `T09` Telegram stantio dopo switch
- `T10` chiusura finale con output contract
- `G01` verifica formato finale
- `G02` report senza collasso dei layer
- `G03` review di skill locale con check di source of truth, routing e output contract
- `G04` aggiornamento scorecard con preservazione di failure mode, proof quality e note operative
