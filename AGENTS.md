# AGENTS.md

Guida per gli agenti che lavorano **su questo repo** (non per l'uso della skill).

## Cos'e' questo repo

Il motore di distribuzione skill (`scripts/redistribute.py`) + i suoi test + esempi. Le skill
**dell'utente** non sono qui: stanno nello store locale (categorie gitignorate).

## Comandi

```bash
pip install -r requirements.txt        # pyyaml + pytest
python3 -m pytest tests -q             # 14 test (devono passare prima di ogni commit)
bash examples/run-demo.sh --dry-run    # demo senza scrivere
bash examples/run-demo.sh              # demo reale (scrive solo in examples/out/)
python3 scripts/redistribute.py --config <yaml> --dry-run
python3 scripts/redistribute.py --config <yaml> --report
```

## Regole

- **TDD**: test prima; ogni funzione nuova ha un test; i 14 test devono restare verdi.
- **Determinismo**: niente LLM nel motore. Il comportamento dipende solo dal config.
- **Niente skill dell'utente nel repo**: le categorie (`dev/ ops/ ...`), `_sources/`,
  `config/redistribution.yaml` e `REDISTRIBUTION.md` sono gitignorate. Non rimuoverle dal
  `.gitignore` e non usare `git add -f` su quelle.
- **Backend**: aggiungerne uno = nuova voce in `BACKENDS` + `plan`/`apply`. Un harness
  *path-based* (flat/categorized/json_list) e' **solo config**, zero codice.
- **`--dry-run` non deve scrivere nulla** (nemmeno creare cartelle).
- Prima di toccare lo store **dell'utente**: backup + `--dry-run` + approvazione.

## Struttura

```
scripts/redistribute.py   # motore: BACKENDS, plan(), apply_harness(), build_report()
tests/test_redistribute.py# 14 test su store sintetici
examples/                 # demo eseguibile + template generici
```

## Versioning

SemVer + tag annotati + `CHANGELOG.md` (Keep a Changelog). Rilasci: tag `vX.Y.Z` + push del tag.
