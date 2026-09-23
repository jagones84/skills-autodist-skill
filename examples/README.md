# examples

Come provare il motore la **prima volta**, senza toccare nulla di tuo.

## Requisiti

- `python3` (>=3.8) + `pyyaml`  ->  `pip install -r ../requirements.txt`

## Prova in 2 minuti (demo autosufficiente)

Lo store demo (`store/`) contiene 2 skill finte; l'output va in `out/` (gitignorato).
**Non tocca `$HOME`.**

```bash
cd ..                                   # root del repo
bash examples/run-demo.sh --dry-run     # 1) anteprima: cosa farebbe (non scrive)
bash examples/run-demo.sh               # 2) applica davvero
```

Output reale dell'ultimo run:

```
store: examples/store  (2 skill, 2 categorie)  dry_run=False
  [demo-flat:*] (1, 0)
  [demo-categorized:*] (2, 0)
  [demo-json-agent:coder] (0, 0)
  [demo-json-agent:ops] (0, 0)
  [demo-openclaw:skills_dir] (2, 0)
  [demo-openclaw:library_dir] (2, 0)
  [demo-openclaw:agent:coder] (0, 1)
  [demo-openclaw:agent:coordinator] (0, 1)
OK
```

Cosa guardare:

| File prodotto | Backend dimostrato |
|---|---|
| `out/demo-flat/hello-world` (symlink) | `flat` |
| `out/demo-categorized/{dev,ops}/...` (symlink) | `categorized` |
| `out/demo-agent.json` (lista riscritta, `bundled-example` preservata) | `json_list` |
| `out/demo-openclaw.json` + `out/demo-openclaw/{pool,library}` | `openclaw` (preset) |

Rilancialo: e' **idempotente** -> di nuovo `(0, 0)` ovunque, nessuna modifica.
`out/*.bak-redistribute` e' il backup creato prima di ogni riscrittura.

## Come si scrive un config

Una sola **fonte**: lo store (cartelle = categorie). Poi, per ogni harness, un `type`:

| `type` | Cosa fa | Chiavi |
|---|---|---|
| `flat` | symlink piatti `<skills_dir>/<skill>` | `skills_dir`, `skills` |
| `categorized` | symlink per categoria `<skills_dir>/<cat>/<skill>` | `skills_dir`, `skills` |
| `json_list` | riscrive una lista dentro un file JSON | `file`, `lists`/`pointer`, `skills`, `preserve`, `backup` |
| `openclaw` | preset: pool flat + liste per-agente | `config`, `agents`, `preserve` |

Selezione: `cat:<categoria>` = categoria intera; nome nudo = una singola skill.

## Template generici (pronti da copiare, senza segreti)

In `templates/`:

- **`openclaw.yaml`** — harness multi-agente: pool condiviso + una lista per sub-agente.
- **`hermes.yaml`** — harness con layout per-categoria.
- **`coding-agent.yaml`** — directory piatta + un secondo agent che tiene le skill in un file JSON.

Copia il template, **sostituisci i path con i tuoi**, poi:

```bash
python3 scripts/redistribute.py --config ~/mio-config.yaml --dry-run
python3 scripts/redistribute.py --config ~/mio-config.yaml
```

## Config di default

Il motore **non** ha un config di default nel repo (il config di ogni persona e' personale):
passa sempre `--config`. Se lo lanci senza, ti avvisa che manca.

## Troubleshooting

- `Skill sconosciuta nel config: 'x'` -> per una categoria usa `cat:x`; altrimenti il nome esatto.
- `Categoria sconosciuta nel config: 'y'` -> controlla le sottocartelle dello store.
- `json_list`/`openclaw` riscrivono un **file che deve esistere**: crealo prima (vedi `seed/`).
- Prima di ogni scrittura il motore crea `<file>.bak-redistribute` (se `backup` e' attivo).
