---
name: "h3-film-pipeline"
description: "Use when making or extending a long AI film with MiniMax-H3 on the DGX, when a generated AI video looks stagnant or monotonous, or when concatenated clips show seams at the junctions. This is a wrapper: it points to the canonical docs and holds no procedure of its own, so it must be followed by reading them."
---

# H3 film pipeline — WRAPPER (il metodo canonico vive nella repo)

Questa skill **non duplica** la procedura: il metodo esiste in **un solo posto**
(`diffusion-pipelines/film/` + `video/h3_turbo/`) ed e' leggibile sia da Windows (`Z:\...`) sia dal
DGX (`/home/jagones/...`). Qui restano **solo i trigger e le trappole che si pagano care**.

## Quando usarla

- costruire o estendere un film AI con MiniMax-H3 (da 5 s a 10+ minuti);
- un video AI generato risulta **stagnante / monotono** ("cammina e basta");
- due clip concatenate mostrano **stacchi** alle giunzioni.

**Non per**: una singola clip isolata (usa `h3_run.py` diretto, `--mode t2v`); il ramo Wan2.2/WAMU.

## Dove sta il metodo (LEGGI PRIMA DI AGIRE)

| Cosa | Dove |
|---|---|
| **Metodo MULTI-SHOT, default per un film nuovo**: blocchi da 4 shot con tagli dichiarati (`[Shot N] At MM:SS.mmm`), ricetta, costi e trappole misurate | `Z:\Repositories\diffusion-pipelines\film\H3_RECIPE.md` **§14** |
| Entry point del pipeline: **i due metodi a confronto**, comandi, criteri di accettazione, eco-inputs | `Z:\Repositories\diffusion-pipelines\video\h3_turbo\README.md` |
| Continuita' C0/C1/C2, camera score, anti-spawn, azioni (§12-§13) | `Z:\Repositories\diffusion-pipelines\film\H3_RECIPE.md` |
| Ricerca su fonti primarie (shotcraft, workflow ufficiali) | `...\film\RESEARCH-pro-shotcraft.md` |
| Ricerca precedente (continuita', spawn, azioni) | `...\film\RESEARCH.md` |
| Grammatiche: azioni, montaggio/audio | `...\film\ACTION-GRAMMAR.md`, `...\film\FILM-GRAMMAR.md` |
| Motore, server, preset, gate (`:8189`) | skill OpenClaw **`comfyui-h3-video`** |
| Produzione di riferimento **verificata** | `...\video\h3_turbo\outputs\film_noir_full\` (fonti vive in `...\film_specs\noir_full\`) |

## Le trappole che non si deducono (il motivo per cui questa skill esiste)

1. **Due tipi di taglio, da NON confondere.** Taglio **dentro** una generazione = formato ufficiale,
   e si **deve** usare (e' cosi' che nasce un film). Cambio di inquadratura **fra** due generazioni =
   discontinuita'. Chi legge solo il vecchio metodo "camera score" ricostruisce un film monotono.
2. **`--trim` vale esattamente K**, mai `length - base`: lo snap `17n+5` aggiunge frame di contenuto
   vero e tagliarli apre un buco nella timeline.
3. **Eco degli input negli outputs** (`inputs/` + `scripts/` + `README.md` con la regola dei seed):
   `film_specs/<titolo>/` e' la fonte viva, `outputs/film_<titolo>/` porta la **copia usata**.
   Senza eco la produzione non e' consegnabile.
4. **Non riavviare il server H3 fra i blocchi**: il primo run paga il load, riavviarlo lo ripaga.

## Verifica (non dichiarare "fatto" senza)

```bash
cd /home/jagones/Repositories/diffusion-pipelines/video/h3_turbo
python3 verify_junctions.py <film>.mp4 --frames <frame per scena>
```

C0 (contenuto) / C1 (moto, `acc/vel`) / C2 (jerk, `jerk/acc`) / audio: soglie in **§14.3-14.4**.
**Lettura invertita**: ai giunti **fra blocchi** un C0 basso e un C2 alto sono **ATTESI** (cambio di
scena voluto, e' un montaggio). Le metriche restano obbligatorie **dentro** il blocco e per scoprire
giunti non voluti.
