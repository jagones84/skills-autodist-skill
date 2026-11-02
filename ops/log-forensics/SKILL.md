---
name: "log-forensics"
description: "Reconstructs timelines, correlates evidence, and tests hypotheses from logs and traces. Use when the user needs incident forensics, sequence reconstruction, or proof from gateway, NDJSON, and related log artifacts."
---

# Log Forensics

## Scopo

Questa skill ricostruisce incidenti e divergenze usando log, trace e artefatti storici.

Usarla quando il problema richiede:

- una timeline affidabile
- correlazione tra eventi
- verifica o smentita di ipotesi
- spiegazione di come due layer siano andati fuori coerenza

Non e' la skill primaria per sapere cosa gira **adesso** se il runtime live e'
interrogabile.
Per quello, prima leggere la fonte primaria del runtime.

## Source Of Truth

- `docs/architecture/state-coherence-model.md` per distinguere stato live da evidenza storica
- `docs/architecture/verification-contract.md` per la chiusura con evidenza e verifica

Questa skill usa i log per spiegare causalita' e ordine temporale.
Non deve ridefinire le fonti primarie dei layer live.

## Quando Invocarla

Invocare questa skill quando l'utente chiede o implica:

- "guarda i log"
- "ricostruisci cos'e' successo"
- "quando si e' rotto?"
- "quale ipotesi e' supportata dai log?"
- "serve una timeline dell'incidente"
- "serve capire se il mismatch e' recente, vecchio o intermittente"

Non usarla come prima skill se la domanda e':

- "quale modello gira ora?"
- "qual e' il default attuale?"
- "quale sessione e' pinnata?"

In quei casi, prima usare la fonte primaria del layer richiesto e poi eventualmente
integrare con i log.

## Obiettivo

Produrre un risultato che contenga:

1. ipotesi considerate
2. evidenze trovate
3. timeline minima
4. grado di fiducia per ogni conclusione
5. gap residui

## Procedura Standard

1. Definisci l'evento o il sintomo da ricostruire.
2. Elenca 2-5 ipotesi plausibili e mutualmente distinguibili.
3. Identifica i log e gli artefatti rilevanti.
4. Estrai solo gli eventi che cambiano davvero la diagnosi.
5. Ordina gli eventi per timestamp o, se manca il timestamp, per relazione causale dichiarata.
6. Mappa ogni evidenza a una o piu' ipotesi.
7. Classifica le ipotesi:
   - supported
   - contradicted
   - unresolved
8. Dichiara esplicitamente cosa i log **non** possono provare da soli.

## Guardrail

- non usare una singola riga di log come prova totale senza contesto
- non confondere tempo di emissione del log con tempo di effetto se c'e' uno switch differito
- non sostituire una fonte primaria live con log storici quando il live e' disponibile
- se i timestamp sono incompleti o rumorosi, dichiarare la limitazione
- non chiudere in `DONE` se la timeline non distingue davvero le ipotesi in gioco

## Pattern Di Output

```text
incident: ...

hypotheses:
- H1 ...
- H2 ...

evidence:
- ...
- ...

timeline:
- T1 ...
- T2 ...

assessment:
- H1: supported | contradicted | unresolved
- H2: supported | contradicted | unresolved

confidence:
- ...

gaps:
- ...
```

## Relazione Con Le Altre Skill

- integra `state-inspector` quando serve capire quale layer era in divergenza
- integra `telegram-ops-debug` quando il sintomo iniziale nasce lato Telegram
- non eseguire azioni correttive sul runtime: questa skill spiega, non cambia
