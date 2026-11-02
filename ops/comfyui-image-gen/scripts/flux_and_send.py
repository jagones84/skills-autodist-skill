#!/usr/bin/env python3
"""
ComfyUI Flux Unchained NSFW generator.

Loads AIGEN_NSFW_FLUX_LONG_api.json, injects the user prompt into node 7
(prompts can be up to ~2000 chars / ~600 tokens thanks to T5-XXL FP8),
submits to ComfyUI, waits for completion, copies the result into the
openclaw workspace and prints READY_TO_SEND:.

Usage:
    python3 flux_and_send.py "<prompt>" <width> <height> <output_name>
    python3 flux_and_send.py --file /path/to/prompt.txt 1024 1024 out.png

Optional flags:
    --negative "<text>"   Override negative prompt
    --seed 12345         Force a specific seed
    --steps 28           Override step count
    --workflow /abs/path/to/AIGEN_NSFW_FLUX_LONG_api.json
    --skip-free          Skip the /free VRAM call before submission
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.request

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_OUTPUT = "/home/jagones/ComfyUI/output"
WORKSPACE_DIR = "/home/jagones/.openclaw/workspace"

DEFAULT_WORKFLOW = "/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/AIGEN_NSFW_FLUX_LONG_api.json"

PROMPT_NODE_ID = "7"        # positive CLIPTextEncode
NEGATIVE_NODE_ID = "8"      # negative CLIPTextEncode
SAMPLER_NODE_ID = "10"      # KSampler
LATENT_NODE_ID = "9"        # EmptyLatentImage

MAX_PROMPT_CHARS = 2000     # ~600 tokens, safe for T5-XXL FP8
WARN_PROMPT_CHARS = 1500

MEDIA_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def log(msg):
    print(msg, flush=True)


def free_vram():
    """Tell ComfyUI to unload models before a heavy Flux run."""
    payload = json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/free",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        time.sleep(2)
        log("VRAM freed.")
    except Exception as exc:
        log(f"  /free failed (ignored): {exc}")


def post_json(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get_json(path):
    with urllib.request.urlopen(f"{COMFYUI_URL}{path}", timeout=30) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def load_workflow(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def estimate_tokens(text):
    """Rough token estimate: 1 token ~ 4 chars for English/danbooru-tag text."""
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def check_prompt_length(prompt):
    n_chars = len(prompt)
    n_tok = estimate_tokens(prompt)
    if n_chars > MAX_PROMPT_CHARS:
        log(f"  WARNING: prompt is {n_chars} chars (~{n_tok} tok).")
        log(f"  Hard cap is {MAX_PROMPT_CHARS} chars. Trimming to fit.")
        return prompt[:MAX_PROMPT_CHARS]
    if n_chars > WARN_PROMPT_CHARS:
        log(f"  NOTE: prompt is {n_chars} chars (~{n_tok} tok) - approaching the 2000 char cap.")
    else:
        log(f"  prompt length OK: {n_chars} chars (~{n_tok} tok).")
    return prompt


def inject_prompt(workflow, prompt, negative=None, seed=None, steps=None,
                  width=None, height=None):
    if PROMPT_NODE_ID in workflow:
        workflow[PROMPT_NODE_ID]["inputs"]["text"] = prompt
    else:
        raise RuntimeError(f"Workflow missing node {PROMPT_NODE_ID} (CLIPTextEncode)")

    if negative is not None and NEGATIVE_NODE_ID in workflow:
        workflow[NEGATIVE_NODE_ID]["inputs"]["text"] = negative

    if seed is not None and SAMPLER_NODE_ID in workflow:
        workflow[SAMPLER_NODE_ID]["inputs"]["seed"] = int(seed)
    if steps is not None and SAMPLER_NODE_ID in workflow:
        workflow[SAMPLER_NODE_ID]["inputs"]["steps"] = int(steps)

    if width is not None and LATENT_NODE_ID in workflow:
        workflow[LATENT_NODE_ID]["inputs"]["width"] = int(width)
    if height is not None and LATENT_NODE_ID in workflow:
        workflow[LATENT_NODE_ID]["inputs"]["height"] = int(height)

    return workflow


def wait_for_completion(prompt_id, max_wait=900, poll=5):
    log("Waiting for Flux generation to complete (this can take 2-4 min)...")
    start = time.time()
    while time.time() - start < max_wait:
        try:
            h = get_json(f"/history/{prompt_id}")
            entry = h.get(prompt_id) or {}
            if entry.get("outputs"):
                return True
            if entry.get("status", {}).get("status_str") == "error":
                log(f"  ComfyUI reported error: {entry['status']}")
                return False
        except Exception as exc:
            log(f"  poll error: {exc}")
        time.sleep(poll)
        elapsed = int(time.time() - start)
        if elapsed % 30 < poll:
            log(f"  ...still waiting ({elapsed}s)")
    return False


def resolve_output(prompt_id):
    h = get_json(f"/history/{prompt_id}")
    entry = h.get(prompt_id) or {}
    outputs = entry.get("outputs", {})
    for node_out in outputs.values():
        for image in node_out.get("images", []):
            sub = image.get("subfolder", "")
            fn = image.get("filename", "")
            if not fn:
                continue
            candidate = os.path.join(COMFYUI_OUTPUT, sub, fn) if sub else os.path.join(COMFYUI_OUTPUT, fn)
            candidate = candidate.rstrip("/")
            if os.path.exists(candidate):
                return candidate
    return None


def sanitize_output_name(raw):
    name = os.path.basename(raw.strip()) if raw else "generated_flux.png"
    if not name:
        name = "generated_flux.png"
    if not name.lower().endswith(MEDIA_EXTENSIONS):
        name += ".png"
    return name


def read_prompt_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def main():
    parser = argparse.ArgumentParser(
        description="Flux Unchained NSFW generator (openclaw skill)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  flux_and_send.py --prompt "slptp, ..." 1024 1024 out.png\n'
            '  flux_and_send.py --prompt "slptp, ..." --steps 30 --seed 42 1024 1024 out.png\n'
            '  flux_and_send.py --file /home/jagones/.openclaw/workspace/prompt.txt 1024 1024 out.png\n'
        ),
    )
    parser.add_argument("width", nargs="?", default=1024, type=int,
                        help="Image width (default 1024)")
    parser.add_argument("height", nargs="?", default=1024, type=int,
                        help="Image height (default 1024)")
    parser.add_argument("output_name", nargs="?", default="generated_flux.png",
                        help="Output filename inside /home/jagones/.openclaw/workspace/ (default generated_flux.png)")
    parser.add_argument("--prompt", default=None,
                        help="Positive prompt text. Wrap in quotes. Use this OR --file.")
    parser.add_argument("--file", default=None,
                        help="Read the prompt from a text file (best for long prompts >1500 chars).")
    parser.add_argument("--negative", default=None, help="Override the negative prompt")
    parser.add_argument("--seed", default=None, type=int)
    parser.add_argument("--steps", default=None, type=int)
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW,
                        help=f"Path to the Flux workflow JSON (default: {DEFAULT_WORKFLOW})")
    parser.add_argument("--skip-free", action="store_true",
                        help="Skip the ComfyUI /free call before submission")
    args = parser.parse_args()

    if args.file and args.prompt:
        log("Use either --prompt or --file, not both.", file=sys.stderr)
        sys.exit(1)

    if args.file:
        if not os.path.exists(args.file):
            log(f"Prompt file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        prompt = read_prompt_from_file(args.file)
    else:
        prompt = args.prompt

    if not prompt:
        log("No prompt provided. Use --prompt \"<text>\" or --file /path/to/prompt.txt", file=sys.stderr)
        sys.exit(1)

    prompt = check_prompt_length(prompt)

    if not os.path.exists(args.workflow):
        log(f"Workflow not found: {args.workflow}", file=sys.stderr)
        sys.exit(1)

    if not args.skip_free:
        free_vram()

    workflow = load_workflow(args.workflow)
    workflow = inject_prompt(
        workflow,
        prompt,
        negative=args.negative,
        seed=args.seed,
        steps=args.steps,
        width=args.width,
        height=args.height,
    )

    log("Submitting Flux Unchained generation...")
    log(f"  workflow: {args.workflow}")
    log(f"  size: {args.width}x{args.height}")
    if args.seed is not None:
        log(f"  seed: {args.seed}")
    if args.steps is not None:
        log(f"  steps: {args.steps}")

    client_id = f"openclaw-flux-{int(time.time())}"
    try:
        response = post_json("/prompt", {"prompt": workflow, "client_id": client_id})
    except Exception as exc:
        log(f"Submit failed: {exc}", file=sys.stderr)
        sys.exit(1)

    prompt_id = response.get("prompt_id")
    if not prompt_id:
        log(f"No prompt_id returned: {response}", file=sys.stderr)
        sys.exit(1)

    log(f"Queued with ID: {prompt_id}")

    if not wait_for_completion(prompt_id):
        log("Timeout waiting for Flux generation.", file=sys.stderr)
        sys.exit(1)

    source = resolve_output(prompt_id)
    if not source or not os.path.exists(source):
        log("Could not locate generated image.", file=sys.stderr)
        sys.exit(1)

    out_name = sanitize_output_name(args.output_name)
    dest = os.path.join(WORKSPACE_DIR, out_name)
    shutil.copy2(source, dest)

    log(f"SOURCE_IMAGE: {source}")
    log(f"WORKSPACE_IMAGE: {dest}")
    log(f"READY_TO_SEND: {dest}")


if __name__ == "__main__":
    main()
