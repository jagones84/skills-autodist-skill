---
name: create-openclaw-skill
description: "Crea una nuova skill OpenClaw (file SKILL.md + symlink + allowlist) sul DGX Spark. Use quando l'utente chiede 'crea una skill per X', 'salva questa procedura come skill', 'trasforma in skill openclaw', 'registra la skill', o 'metti la skill su openclaw'. Triggers IT: 'crea skill openclaw', 'registra skill', 'metti skill su openclaw', 'salva come skill', 'trasforma in skill', 'fai una skill per', 'skill per openclaw', 'nuova skill', 'skill openclaw'. Triggers EN: 'create openclaw skill', 'register skill', 'add skill openclaw', 'new openclaw skill'."
---

# Creare una skill OpenClaw — procedura validata (2026-09)

Flusso testato su `dgx-to-windows` e `openrouter-catalog-refresh`. Da eseguire
quando l'utente chiede "crea una skill per X" o "salva questa procedura come
skill". Lavora sul **DGX Spark via SSH** (`ssh dgx` da Windows PowerShell).
Tutti i file sul DGX sono raggiungibili anche come `Z:\.openclaw\...` dal
PC Windows (mount locale della home utente `jagones`).

## 1. Decidi nome + scope

| Campo        | Regola                                                                                            |
|--------------|---------------------------------------------------------------------------------------------------|
| Nome         | `kebab-case` corto, <= 30 char, unico. Esempi: `dgx-to-windows`, `openrouter-catalog-refresh`     |
| Scope        | Una cosa sola, ben precisa. NON "tutto" — meglio 2 skill piccole che 1 gigante                    |
| Trigger (IT)  | 3-6 frasi che l'utente potrebbe dire per invocarla (es. "ssh su windows", "aggiorna modelli")      |
| Trigger (EN)  | Stesse 3-6 in inglese per utenti misti                                                           |
| Prerequisiti | Servono CLI extra, chiavi, file particolari? Documentarli nella sezione "Prereq"                  |

## 2. Crea la cartella sul DGX

Scrivere i file tramite `Z:\.openclaw\workspace\skills\<nome>\SKILL.md` (visto
dal PC Windows). Il DGX lo vede come `/home/jagones/.openclaw/workspace/skills/<nome>/`.

```
Z:\.openclaw\workspace\skills\<nome>\
|-- SKILL.md          # OBBLIGATORIO - file che OpenClaw carica
|-- scripts\          # OPZIONALE - script Python/Bash riusabili
|-- references\       # OPZIONALE - doc extra, link, API reference
```

## 3. Scrivi SKILL.md (formato obbligatorio)

```markdown
---
name: "<nome-stesso-della-cartella>"
description: "<1-2 frasi: cosa fa + trigger IT/EN. La description e QUELLO
             che fa matchare la skill - se mancano i trigger, la skill
             non viene mai invocata. Includi 5-10 varianti per lingua>"
---

# <Titolo in Title Case>

<1 paragrafo: scopo della skill, in 1-2 righe.>

## Sezione operativa
<istruzioni passo-passo, concise, con comandi pronti.>

## Regole d'oro / Gotchas
<le trappole note, le cose da non fare.>

## File (se scripts/)
<lista scripts/ con una riga di descrizione per ognuno.>
```

**Vincoli rigidi** (presi da field-test, vedi journal errori):
- `name` nella frontmatter = nome cartella **identico**
- `description` NON superare ~600 caratteri (description >160 byte
  -> trigger lunghi vengono rifiutati dal parser; meglio stare
  sotto i 400)
- Trigger in description = SEMPRE lista (virgole), NON prosa
- Lingua del corpo: italiano (utente parla italiano, l'allievo impara
  piu veloce)
- Niente emoji in description (rompe alcuni parser)
- Tabelle markdown per dati strutturati (mount, comandi, output)

## 4. Registra la skill (3 step meccanici)

Crea uno script Python in `Z:\.openclaw\.agent\scripts\register_<nome>.py`
**prima** di toccare la config. Lo script fa: symlink + backup + modifica
allowlist. NON editare `openclaw.json` a mano (rischio di rovinare il
JSON, 18MB di config).

Schema dello script (adatta nomi):

```python
#!/usr/bin/env python3
import json, os, shutil
from pathlib import Path
from datetime import datetime

SRC = Path('/home/jagones/.openclaw/workspace/skills/<nome>')
DST = Path('/home/jagones/.openclaw/skills/<nome>')        # symlink
CONFIG = Path('/home/jagones/.openclaw/openclaw.json')
TS = datetime.now().strftime('%Y%m%d-%H%M%S')

# 1) symlink (idempotente)
if DST.is_symlink() or DST.exists():
    if DST.is_symlink(): DST.unlink()
    elif DST.is_dir(): shutil.rmtree(DST)
    else: DST.unlink()
DST.symlink_to(SRC)

# 2) backup + allowlist
backup = CONFIG.with_suffix(f'.json.bak-skill-<nome>-{TS}')
shutil.copy2(CONFIG, backup)

cfg = json.loads(CONFIG.read_text())
skills = cfg['agents']['entries']['coordinator']['skills']  # o altro agente
if '<nome>' not in skills:
    skills.append('<nome>')
    tmp = CONFIG.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    os.replace(tmp, CONFIG)  # atomic write
print(f"OK - {len(skills)} skills totali")
```

Poi esegui:

```powershell
ssh dgx "python3 /home/jagones/.openclaw/.agent/scripts/register_<nome>.py"
```

Il **HOT RELOAD e automatico** (OpenClaw rilegge la allowlist + symlink
ad ogni invocazione skill; conferma dal journal).

## 5. Verifica (3 check)

```powershell
# A. file system: symlink + file presenti
ssh dgx "ls -la /home/jagones/.openclaw/skills/<nome>"
ssh dgx "head -3 /home/jagones/.openclaw/skills/<nome>/SKILL.md"

# B. CLI: la skill e "ready" (PATH node v24 obbligatorio)
ssh dgx "/home/jagones/.nvm/versions/node/v24.15.0/bin/node /home/jagones/.local/bin/openclaw skills list --agent coordinator"
# cerca la riga: | ready  | <nome>            | ... | openclaw-managed |

# C. end-to-end: invoca la skill dal canale (Telegram, UI) e guarda
# che il modello la trovi.
```

Se B mostra `excluded` o non la vedi: il problema e nella description
(troppo lunga / trigger mancanti). Modifica e riverifica senza restart.

## 6. Persisti in HANDOFF.md (cross-session)

L'LLM **dimentica** la skill dopo N sessioni. Per non farla ricreare
ogni volta, appendi una riga a `Z:\.openclaw\.agent\HANDOFF.md`:

```markdown
[YYYY-MM-DD HH:MM] TRAE: SKILL <nome> CREATA. (1) <cosa fa>. (2) <trigger chiave>.
(3) <verifica fatta>. (4) <dove sta>. Skill pronta: l'allievo impara da SKILL.md.
```

## 7. Cose da NON fare

| Errore                                                 | Cosa succede                                       |
|--------------------------------------------------------|----------------------------------------------------|
| **Dimenticare il frontmatter YAML** in cima a SKILL.md | Trae mostra la skill "nuda" (solo nome, no descrizione, no trigger) |
| Editare `openclaw.json` a mano (no script)             | Rischio corrompere 18MB di config; niente atomic   |
| Trigger in IT ma non in EN (o viceversa)                | LLM non abbina quando utente parla l'altra lingua   |
| Description > 600 char                                 | Skill esclusa o rifiutata dal parser               |
| Nome cartella != nome frontmatter                      | "skill not found" misteriosi                       |
| Cancellare il symlink pensando sia la skill            | Perdi il riferimento, ripristinalo con lo script   |
| Dimenticare il backup `.bak-skill-<nome>-<ts>`         | Rollback impossibile se sbagli qualcosa            |
| Non testare E2E dopo la registrazione                  | Skill "ready" ma con description sbagliata         |

## 8. Esempi di riferimento (gia sul disco)

- `Z:\.openclaw\workspace\skills\openrouter-catalog-refresh\SKILL.md` - canonico
  (description <500 char, 5-6 trigger IT+EN, tabella files, sezione
  "Regole d'oro" con 7 bullet)
- `Z:\.openclaw\workspace\skills\dgx-to-windows\SKILL.md` - minimal (~150 righe,
  focus su tabella path + troubleshooting)

## 9. Quando NON creare una skill

- **Una tantum** (l'utente non lo rifara mai) -> script + HANDOFF.md bastano
- **3-4 comandi noti** -> meglio un cheat sheet in HANDOFF.md
- **Gia esiste** in `openclaw skills list` con altro nome -> riusa/estendi
- **Non hai testato la procedura almeno una volta** -> prima validala, POI
  scrivi la skill (regola "field-proven" del workspace)
