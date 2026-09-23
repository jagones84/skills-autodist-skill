# Changelog

Tutte le modifiche rilevanti di questa repo. Formato: [Keep a Changelog](https://keepachangelog.com/), versioning [SemVer](https://semver.org/).

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
