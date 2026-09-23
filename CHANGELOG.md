# Changelog

Tutte le modifiche rilevanti di questa repo. Formato: [Keep a Changelog](https://keepachangelog.com/), versioning [SemVer](https://semver.org/).

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
