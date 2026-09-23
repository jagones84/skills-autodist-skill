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
1. ispeziona   -> leggi lo store + gli harness presenti
2. proponi     -> scrivi una mappa skill -> harness (mostrala all'utente)
3. approva     -> l'utente conferma o corregge
4. dry-run     -> `--dry-run` (non scrive)
5. applica     -> `--config ...`  (l'engine crea backup `<file>.bak-redistribute`)
6. verifica    -> nessun symlink rotto; `--report` aggiornato
```

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

## 3-5) Applica con approvazione

```bash
python3 scripts/redistribute.py --config <config> --dry-run   # mostra +/- per harness
python3 scripts/redistribute.py --config <config>             # applica
```

Non toccare a mano i symlink: li gestisce il motore (idempotente; ripara anche i link rotti).

## 6) Verifica

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
- Non modificare il file di config di un harness a mano quando un backend lo fa gia'.
