---
name: skills-autodist-skill
description: Distribute a canonical store of skills across N harnesses/agents from one YAML config. Deterministic engine (symlinks or config rewrite: flat, categorized, json_list, openclaw). Use when the user wants to choose which skills go to which agent, or a harness looks empty/wrong.
metadata:
  emoji: 🧭
  os: [linux, darwin, win32]
---

# skills-autodist-skill

Distribuisci le skill di uno **store** su piu' **harness/agenti** a partire da **un** config.

## Regola d'oro (leggila prima)

Il motore e' **deterministico**: applica esattamente il config. **Tu (agente) proponi, l'utente
approva, il motore esegue.** Non inventare mapping e non applicare senza approvazione.

```
0. adotta      -> se hai trovato/scaricato una skill: `--adopt <src> --cat <cat>` (NON la modifichi)
1. ispeziona   -> leggi lo store + gli harness presenti
2. proponi     -> scrivi una mappa skill -> harness (mostrala all'utente)
3. approva     -> l'utente conferma o corregge
4. valida      -> `--validate` (il config e' sensato? non scrive)
5. anteprima   -> `--diff` e/o `--dry-run` (non scrivono)
6. applica     -> `--config ...`  (l'engine crea backup `<file>.bak-redistribute`)
7. verifica    -> nessun symlink rotto; `--report` aggiornato
```

## 0) Adotta una skill nuova (solo se ne hai trovata una)

Se l'utente ti ha chiesto di aggiungere una skill (es. trovata sul web e gia' scaricata sul disco),
mettila nello store **senza modificarne il contenuto**:

```bash
python3 scripts/redistribute.py --adopt <src> --cat <cat>            # copia (default, strip .git/dipendenze)
python3 scripts/redistribute.py --adopt <src> --cat <cat> --mode link # symlink relativo (repo tracciato)
python3 scripts/redistribute.py --adopt <src> --cat <cat> --dry-run  # anteprima
```

- Deve contenere `SKILL.md`; se la destinazione esiste serve `--force`.
- **Non** editare la skill, **non** riscriverle il config a mano: l'adopt **stampa lo snippet**.
  Se un harness usa `cat:<cat>`, la skill e' gia' inclusa (zero edit).

## 1) Ispeziona

```bash
# le categorie dello store (una cartella per categoria; una sottocartella per skill)
ls <store>

# gli harness presenti e le loro dir di skill (esempi)
ls ~/.openclaw/skills ~/.openclaw/workspace/skills ~/.hermes/skills 2>/dev/null
ls ~/.config/opencode/skills 2>/dev/null

# il config corrente dell'utente, se esiste
ls <store>/config/redistribution.yaml
```

## 2) Proponi (non applicare)

Costruisci il config dal template giusto in `examples/templates/`:

| Situazione | `type` | Template |
|---|---|---|
| Dir piatta di skill | `flat` | `coding-agent.yaml` |
| Layout per-categoria | `categorized` | `hermes.yaml` |
| Skill elencate in un file JSON dell'harness | `json_list` | `coding-agent.yaml` |
| Harness multi-agente con pool + per-agente | `openclaw` | `openclaw.yaml` |

Regole di selezione: `cat:<categoria>` = categoria intera; nome nudo = una skill.
`preserve: not_in_store` (default) tiene le voci che non vengono dallo store (es. bundled).

**Mostra la mappa proposta all'utente e chiedi conferma.** Esempio di proposta:

```
openclaw.coder      <- cat:dev        (62 skill)
openclaw.coordinator<- cat:ops, cat:meta
hermes              <- cat:research, cat:media
```

## 3-6) Valida, anteprima e applica

```bash
python3 scripts/redistribute.py --config <config> --validate   # errori di config? exit 1 se invalido
python3 scripts/redistribute.py --config <config> --diff       # modifiche voce per voce (+/-)
python3 scripts/redistribute.py --config <config> --dry-run    # conteggi (+/-) per harness
python3 scripts/redistribute.py --config <config>              # applica
```

Non toccare a mano i symlink: li gestisce il motore (idempotente; ripara anche i link rotti).

## 7) Verifica

```bash
python3 scripts/redistribute.py --config <config> --report     # rigenera la mappa
# i link devono risolvere:
find <harness_skills_dir> -maxdepth 2 -type l ! -exec test -e {} \; -print
```

## Errori comuni

- `Skill sconosciuta nel config: 'x'` -> per una categoria usa `cat:x`; altrimenti il nome esatto.
- `Categoria sconosciuta nel config: 'y'` -> non e' una sottocartella dello store.
- `json_list`/`openclaw` riscrivono un file che **deve esistere**: crealo prima (vedi `examples/seed/`).
- Nessun config di default nel repo: passa sempre `--config`.

## Cosa NON fare

- Non committare le skill dell'utente nello store del repo (sono gitignorate di proposito).
- Non eseguire l'applicazione senza approvazione esplicita.
- Non modificare il contenuto di una skill adottata: `--adopt` **colloca e basta** (copy o link), mai edit.
- Non modificare il file di config di un harness a mano quando un backend lo fa gia'.
