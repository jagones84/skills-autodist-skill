# skills-autodist-skill

**Distribuisci le tue skill su N harness/agenti** da un'unica fonte di verita' (un config YAML).
Le skill vivono in uno **store** di cartelle-categoria; l'engine le aggancia a ogni harness come
dice il config — con symlink (`flat`, `categorized`) o riscrivendo un file di configurazione
dell'harness (`json_list`, `openclaw`).

Due livelli, di proposito separati:

1. **Motore deterministico** — `scripts/redistribute.py`. Applica *esattamente* il config scritto
   da te. **Nessun LLM nel loop.** Idempotente. `--dry-run` (conteggi), `--diff` (modifiche **voce per
   voce**) e `--validate` (controlla il config) **non scrivono nulla**; `--report` genera la mappa.
2. **Livello agente** — `SKILL.md`. Un LLM legge lo store e i tuoi harness, **propone** la mappa
   skill→harness, ti fa **approvare**, poi lancia il motore. Autonomia nella *proposta*,
   determinismo nell'*esecuzione*.

**Licenza**: PolyForm Noncommercial 1.0.0 — libero per uso **non commerciale** con attribuzione.
Per l'uso commerciale serve una licenza separata (vedi `LICENSE`).

## Quick start (demo autosufficiente)

Guida al primo avvio: **[`examples/README.md`](examples/README.md)**.

```bash
pip install -r requirements.txt
bash examples/run-demo.sh --dry-run     # anteprima (semina examples/out/)
bash examples/run-demo.sh               # applica (scrive solo in examples/out/)
python3 scripts/redistribute.py --validate --config examples/redistribution.example.yaml
python3 scripts/redistribute.py --diff     --config examples/redistribution.example.yaml
python3 -m pytest tests -q              # 24 test
```

Comandi dalla **root del repo** (lo store d'esempio usa percorsi relativi).

Il demo usa lo store `examples/store` (2 skill finte) e scrive in `examples/out/`:
**non tocca `$HOME`**. Template generici (OpenClaw/Hermes/coding agent) in `examples/templates/`.

## Backend

| `type`        | Cosa fa                                                          | Chiavi |
|---------------|------------------------------------------------------------------|--------|
| `flat`        | symlink piatti `<skills_dir>/<skill>`                            | `skills_dir`, `skills` |
| `categorized` | symlink per categoria `<skills_dir>/<cat>/<skill>`               | `skills_dir`, `skills` |
| `json_list`   | riscrive una lista dentro un file JSON (dichiarativo)            | `file`, `lists`/`pointer`, `skills`, `preserve`, `backup` |
| `openclaw`    | preset: pool flat (`skills_dir`+`library_dir`) + liste per-agente | `config`, `agents`, `preserve` |

`preserve`: `not_in_store` (default, tiene le voci non dello store) | `none` (riscrive solo
con le skill dello store). Un **nuovo backend** serve solo per una nuova *forma* di layout.

## Il config

```yaml
version: 2
store: <dove vivono le skill>        # le categorie dello store = sue sottocartelle
harnesses:
  <nome>:
    type: <backend>
    # ...chiavi del backend
```

Selezione delle skill: `cat:<categoria>` = categoria intera; nome nudo = skill puntuale.
Esempio completo e commentato: `examples/redistribution.example.yaml`.

## Comandi

| Comando | Effetto |
|---|---|
| `python3 scripts/redistribute.py` | applica il config (idempotente; backup dei JSON prima di riscriverli) |
| `--dry-run` | conteggi `(aggiunte, rimosse)` per target — **non scrive** |
| `--diff` | modifiche **voce per voce** (`+`/`-`) — **non scrive** |
| `--validate` | valida il config; **exit 1** con l'elenco errori se invalido — **non scrive** |
| `--report` | rigenera `REDISTRIBUTION.md` |
| `--config <file>` | usa un config diverso da `config/redistribution.yaml` |

## Dove stanno le skill (importante)

Le categorie dello store nella root (`dev/`, `ops/`, `android/`, ...) e `_sources/` sono
**gitignorate**: questo repository contiene **solo il motore** — script, test, esempi, licenza.
Ognuno mette le **proprie** skill dove vuole (di default `<categoria>/<nome>/SKILL.md`) e le
elenca nel proprio config.

## Usarlo da un agente (LLM)

Vedi **[`SKILL.md`](SKILL.md)**: l'agente legge lo store + gli harness, **propone** il config,
aspetta la tua approvazione, poi esegue `--dry-run` e infine applica.

## Test

```bash
python3 -m pytest tests -q                    # 24 test
```

Coprono i backend su store sintetici (nessuna scrittura fuori da `tmp`): symlink
flat/categorized, `json_list` (preserve + idempotenza), preset openclaw, registry,
report, `--dry-run` che non scrive, `--validate` (ok / errori / exit code) e
`--diff` (aggiunte e rimosse voce per voce, onorando `preserve`).

## Struttura

```
skills-autodist-skill/
├── SKILL.md                         # livello agente (llm-driven, con approvazione)
├── scripts/redistribute.py          # il motore (registry di backend)
├── tests/test_redistribute.py       # 24 test
├── examples/
│   ├── README.md                    # guida al primo avvio
│   ├── redistribution.example.yaml  # config d'esempio eseguibile
│   ├── templates/                   # openclaw / hermes / coding-agent (senza segreti)
│   ├── store/{dev,ops}/...          # 2 skill demo
│   ├── seed/*.json                  # seed per i backend JSON
│   └── run-demo.sh
├── requirements.txt
├── LICENSE                          # PolyForm Noncommercial 1.0.0
└── README.md / CHANGELOG.md / AGENTS.md / .gitignore
```
