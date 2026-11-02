---
name: comfyui-start
description: Start the local ComfyUI server and make it ready for use. Use when the user wants to launch ComfyUI quickly from a single command.
---

## Overview

This skill provides a simple way to start the ComfyUI server using the existing `start_comfy.sh` script on the desktop. It ensures the virtual environment is activated and the server runs in the background, then reports the URL to the user.

## Usage

```bash
openclaw skill run comfyui-start
```

The command will:
1. Execute `/home/jagones/Desktop/QUICK COMMANDS/start_comfy.sh`.
2. Wait a few seconds for the server to start.
3. Return the address `http://127.0.0.1:8188` (or the configured port).

## Implementation Details

- The skill runs the start script via `bash`.
- It checks the process list for `python main.py` to confirm the server is up.
- If the server fails to start, it returns the last few log lines for troubleshooting.

## Files

- `run.sh` – wrapper script executed by the skill.

## Example

```bash
# From any terminal
openclaw skill run comfyui-start
```

You’ll see a message like:
```
✅ ComfyUI started – open http://127.0.0.1:8188 in your browser.
```