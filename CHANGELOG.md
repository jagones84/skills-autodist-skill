# Changelog

Tutte le modifiche rilevanti di questa repo. Formato: [Keep a Changelog](https://keepachangelog.com/), versioning [SemVer](https://semver.org/).

## [1.5.0] - 2026-09-23

### Added
- **`--diff`**: mostra le modifiche **voce per voce** che `apply` farebbe (symlink da aggiungere/rimuovere,
  voci JSON da aggiungere/rimuovere) **senza scrivere nulla**. Diverso da `--dry-run`, che dà solo i conteggi.
- **`--validate`**: valida il config **senza applicarlo** — type noti, chiavi obbligatorie per backend,
  file target esistenti, riferimenti a skill/categorie presenti nello store. Stampa `config valido`
  (exit 0) oppure l'elenco degli errori (**exit 1**).
- Helper `resolve_entries()`: come `expand()` ma **non** esce, ritorna anche la lista degli errori.

### Changed
- `main()`: `--validate` e `--diff` girano prima di applicare; uno `store` mancante non fa piu' crashare
  la validazione (viene riportato come errore).
- `_label()`: robusto anche per pointer a segmento singolo.
- Test: **24** (erano 14). Scritti in TDD: prima falliscono, poi passa l'implementazione.

## [1.4.0] - 2026-09-23

### Added
- **`SKILL.md`**: livello agente. L'LLM legge lo store + gli harness, **propone** la mappa
  skill→harness, chiede approvazione, poi il motore **applica** (deterministico, con backup).
  Autonomia nella proposta, determinismo nell'esecuzione.
- `AGENTS.md`: guida per gli agenti che lavorano sul repo.

### Changed
- **Rinomina**: progetto/cartella/repo `skills-store` → **`skills-autodist-skill`** (coerente con
  `yt-whisper-skill`, `android-arm64-devkit-skill`). Aggiornati README, esempi e template.
  Il motore non ha il nome hardcoded: lo `store:` sta nel config.
- README: chiarito che esistono **due livelli** (motore deterministico + layer agente).

## [1.3.0] - 2026-09-23

### Added
- `examples/README.md`: guida al **primo avvio** (demo in 2 minuti, output reale, anatomia
  del config, troubleshooting).
- `examples/templates/`: config generici **pronti da copiare e senza segreti** per OpenClaw
  (multi-agente), Hermes (per-categoria) e un coding agent (flat + json_list).

### Changed
- README: link alla guida in `examples/README.md` e ai template generici.

## [1.2.1] - 2026-09-23

### Changed
- `.gitignore`: tiene esplicitamente i **template** (`!.env.template`, `!*.example*`) mentre
  ignora config locali e segreti.

## [1.2.0] - 2026-09-23

### Added
- Licenza **PolyForm Noncommercial 1.0.0** (`LICENSE`): uso non commerciale con attribuzione;
  l'uso commerciale richiede una licenza separata.
- Store **demo** `examples/store/` (2 skill finte) + config d'esempio eseguibile e
  autosufficiente (`examples/run-demo.sh`, `examples/seed/`), output in `examples/out/`.

### Changed
- `.gitignore`: le categorie di skill locali, `_sources/`, il config d'istanza e
  `REDISTRIBUTION.md` sono esclusi dal repo (il repo pubblico contiene solo il motore).
- README riscritto come **motore generico** (non piu' come istanza di deployment).

## [1.1.0] - 2026-09-23

### Added
- Registry di backend (`BACKENDS`) + dispatch generico: `plan()` e `apply_harness()`
  al posto della catena `if type == ...`.
- Backend dichiarativo **`json_list`**: riscrive una lista dentro un file JSON
  (`file`, `lists`/`pointer`, `skills`, `preserve`, `backup`) — aggiungere un harness
  di questo tipo non richiede codice.
- Suite di test (`tests/`, pytest) su tutti i backend; `requirements.txt`.
- `examples/redistribution.example.yaml`: config generico d'esempio.

### Fixed
- `--dry-run` non crea piu' directory (prima `apply_flat` faceva `makedirs` anche in dry).
- Il report non contiene piu' un timestamp volatile (output riproducibile).

### Changed
- Il preset `openclaw` onora `preserve` come gli altri backend.
- `build_report()` usa `plan()`: nessun ramo hardcoded per-harness.

## [1.0.2] - 2026-09-23

### Fixed
- Smesso di tracciare file non-sorgente: `node_modules/` (548 file), backup `*.bak-*`/`*.bak` (6)
  e `__pycache__/*.pyc` (4). Rimossi dal tracking (restano su disco) e coperti dal `.gitignore`.

### Changed
- Symlink delle skill esterne convertiti da target assoluti (`/home/...`) a relativi (`../../...`),
  come `_sources/`: nessun path locale nel repo, target invariato.
- `.gitignore` esteso con `node_modules/`, `.venv/`, `venv/`.

## [1.0.1] - 2026-09-23

### Fixed
- `redistribute.py` (`type: categorized`): ripara i symlink dangling o con target errato
  (prima controllava solo l'esistenza, quindi non guariva dopo un rename della cartella).

### Changed
- Cartella dello store rinominata `Skills` -> `skills-store` (allineata al nome della repo).
  Aggiornati `config/redistribution.yaml` e `README.md`.

## [1.0.0] - 2026-09-23

### Added
- `config/redistribution.yaml`: fonte di verità della redistribuzione (harness → categorie/skill).
- `scripts/redistribute.py`: applica la redistribuzione in un comando (idempotente);
  `--dry-run` (anteprima) e `--report` (rigenera `REDISTRIBUTION.md`).
- `README.md` e `REDISTRIBUTION.md` (mappa generata).

### Changed
- Modello a back-end generico: ogni harness ha un `type` (`flat`, `categorized`, `openclaw`).
- Deduplica del layout: la mappa agenti/skill non vive più in un doc `.agent`.

### Notes
- SkillKit **non** è usato: la gestione è store + config + script.
- `.gitignore` esteso con pattern difensivi per segreti (`.env`, `*.pem`, `*.key`, ecc.).
