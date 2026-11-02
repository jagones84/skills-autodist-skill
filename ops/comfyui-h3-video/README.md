# comfyui-h3-video - layout

Skill per il motore video **MiniMax-H3** (open weights) su DGX Spark, su ComfyUI affiancato `:8189`.

## Canonical Command
```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-h3-video/scripts/h3-quick.sh --mode t2v --prompt-file prompt.txt --seconds 5
```
Stampa `READY_TO_SEND: /absolute/path` (copia del mp4 nel workspace).

## Layout
```
comfyui-h3-video/
  SKILL.md            procedura canonica (prompt operativo per l'agente)
  README.md           questo file
  PATHS.md            SCHEMA DEI PATH (skill -> ogni singolo path, Linux + Windows)
  PROMPT.md           system-prompt pronto per un agente
  scripts/
    h3-run.sh         passthrough a runners/h3_run.py
    h3-chain.sh       passthrough a runners/h3_chain.py
    h3-doctor.sh      gate: 0 FAIL
    h3-server.sh      start|stop|status del server :8189
    h3-quick.sh       run + copia nel workspace + READY_TO_SEND
    h3-film.sh        film lungo a scene concatenate (new|run|status|verify|stop)
    h3-free-vram.sh   libera la RAM (--kill ferma llama-server e :8188)
  templates/          4 template ufficiali H3 (JSON)
  reference/          puntatori ai canonici
```

## Delivery Rule
Mai inviare file da `ComfyUI/output/`. Solo il path di `READY_TO_SEND:`.

## Troubleshooting
| Issue | Solution |
|---|---|
| `H3 server non risponde` | `bash scripts/h3-server.sh start` poi `h3-doctor.sh` |
| `0 FAIL` assente | leggere il doctor: pin, pesi o torch |
| `LoadImage ... custom validation failed` | input dir non condivisa (vedi SKILL.md) |
| video senza audio | VAEDecodeAudio + VAE audio fp32 |
| OOM | `h3-server.sh stop` + spegnere `:8188` e `llama-server` |
