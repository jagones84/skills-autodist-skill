# skills-store

Store **unico e canonico** delle skill per gli agent harness del DGX Spark.
Le skill reali vivono qui (versionate); ogni runtime le vede via **symlink** allo store.

## Struttura

```
skills-store/
├── config/redistribution.yaml   # FONTE DI VERITA': agenti -> categorie/skill
├── scripts/redistribute.py      # applica la redistribuzione (idempotente) + report
├── REDISTRIBUTION.md            # mappa generata (da --report)
├── dev/ ops/ tg/ android/ research/ data/ media/ meta/   # le categorie di skill
└── _sources/                    # symlink a repo di terze parti (non-skill)
```

## Applicare la redistribuzione

Il file `config/redistribution.yaml` definisce, per ogni agente (inclusi i 5
sub-agenti OpenClaw: `openclaw.coordinator`, `.coder`, `.researcher`, `.analyst`,
`.writer`) e per gli specialisti (`hermes`, `opencode`, `maka`), quali
categorie/skill sono attive.

```bash
python3 scripts/redistribute.py --dry-run   # anteprima
python3 scripts/redistribute.py             # applica (symlink + openclaw.json)
python3 scripts/redistribute.py --report    # rigenera REDISTRIBUTION.md
```

Lo script e' **idempotente** e fa:
- symlink piatti per OpenClaw (`~/.openclaw/skills`, `~/.openclaw/workspace/skills`),
  OpenCode (`~/.config/opencode/skills`), Maka (`~/.config/Maka/workspaces/default/skills`);
- symlink per-categoria per Hermes (`~/.hermes/skills/<cat>/<skill>`);
- riscrive `agents.entries.<a>.skills` in `~/.openclaw/openclaw.json`, preservando le
  skill bundled/native (non dello store).

`dev` e' **condiviso di proposito** tra `openclaw.coder` e `opencode` (i due coding agent).

## Aggiungere una skill

1. crea `<categoria>/<nome>/SKILL.md` dentro lo store;
2. aggiungi `<nome>` (o `cat:<categoria>`) all'harness giusto in `config/redistribution.yaml`;
3. `python3 scripts/redistribute.py`.

## Il motore: backend generici

`scripts/redistribute.py` e' **generico**: ogni harness dichiara un `type` e il motore lo
applica via un registry (`BACKENDS`). Aggiungere un harness path-based = **solo** una voce
nel config, zero codice.

| `type`        | Cosa fa                                                          | Chiavi |
|---------------|------------------------------------------------------------------|--------|
| `flat`        | symlink piatti `<skills_dir>/<skill>`                            | `skills_dir`, `skills` |
| `categorized` | symlink per categoria `<skills_dir>/<cat>/<skill>`               | `skills_dir`, `skills` |
| `json_list`   | riscrive una lista in un file JSON (dichiarativo)                | `file`, `lists`/`pointer`, `skills`, `preserve`, `backup` |
| `openclaw`    | preset: pool flat (`skills_dir`+`library_dir`) + liste per-agente | `config`, `agents`, `preserve` |

`preserve`: `not_in_store` (default, tiene le voci non dello store) | `none` (riscrive solo
con le skill dello store). Un **nuovo backend** serve solo per una nuova *forma* di layout.

Config d'esempio generico: `examples/redistribution.example.yaml`. Il config reale di questa
istanza e' `config/redistribution.yaml`.

## Test

```bash
python3 -m pytest tests -q
```

Coprono i backend su store sintetici (nessuna scrittura fuori da `tmp`): symlink
flat/categorized, `json_list` (preserve + idempotenza), preset openclaw, registry,
report e `--dry-run` che non scrive.

Dettagli operativi e stato corrente: `REDISTRIBUTION.md`.
