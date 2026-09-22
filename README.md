# skills-store

Store **unico e canonico** delle skill per gli agent harness del DGX Spark.
Le skill reali vivono qui (versionate); ogni runtime le vede via **symlink** allo store.

## Struttura

```
Skills/
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

1. crea `Skills/<categoria>/<nome>/SKILL.md`;
2. aggiungi `<nome>` (o la categoria) all'agente giusto in `config/redistribution.yaml`;
3. `python3 scripts/redistribute.py`.

Dettagli operativi e stato corrente: `REDISTRIBUTION.md` e, sul DGX,
`~/Repositories/.agent/HANDOFF.md`.
