#!/usr/bin/env python3
"""
ComfyUI /home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/ universal launcher.

Single command to run ANY validated workflow in
/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/.

Auto-detects the prompt node (CLIPTextEncode.text OR TextEncodeQwenImageEditPlus.prompt)
and the image node (LoadImage.image) and injects user inputs before submit.

Usage:
    python3 run_wf.py <wf_short_name> "<prompt>" [width] [height] [out.png]
    python3 run_wf.py <wf_short_name> --file /path/prompt.txt [width] [height] [out.png]
    python3 run_wf.py <wf_short_name> --image /path/source.png "<prompt>" [width] [height] [out.png]
    python3 run_wf.py list                                # print all known wf

Optional flags:
    --seed N           Force seed (default: random)
    --steps N          Override steps
    --cfg N            Override CFG
    --denoise N        Override denoise
    --negative "..."   Override negative prompt (Flux Long node 8)
    --workflow /abs/path.json   Use a custom path instead of the mapping
    --skip-free        Skip /free VRAM call

Mapping (short_name -> file in /home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/):
    flux_long                -> AIGEN_NSFW_FLUX_LONG_api.json
    nsfw_community_h         -> img2img_nsfw_community_cfg1_d085_shift3_api.json   (WINNER)
    nsfw_l_d100              -> img2img_nsfw_lightning4_2511_d100_api.json
    nsfw_l_d055              -> img2img_nsfw_lightning4_2511_d055_api.json
    sfw_aio_v11              -> img2img_sfwclad_aio_v11.json
    nsfw_gfix_l10d60c2       -> _recovered_AIGEN_gfix_l10d60c2.json
    nsfw_gfix2               -> _recovered_AIGEN_gfix2.json
    nsfw_l_d100_recovered    -> _recovered_AIGEN_LIGHTNING4_NSFW.json
    nsfw_community_qw        -> _recovered_AIGEN_QW_COMMUNITY_NSFW.json
    sfw_aio_recovered        -> _recovered_AIGEN_QWEN_SFW_AIO.json
    txt2img_perfect_delib    -> txt2img_perfect_deliberate.json
    util_resize              -> img2img_resize.json
    util_removebg            -> img2img_removebg.json
    util_upscale             -> img2img_upscale.json
"""

import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
import uuid

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_OUTPUT = "/home/jagones/ComfyUI/output"
WORKSPACE_DIR = "/home/jagones/.openclaw/workspace"
WF_DIR = "/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs"

WF_MAP = {
    "flux_long": "AIGEN_NSFW_FLUX_LONG_api.json",
    "nsfw_community_h": "img2img_nsfw_community_cfg1_d085_shift3_api.json",
    "nsfw_l_d100": "img2img_nsfw_lightning4_2511_d100_api.json",
    "nsfw_l_d055": "img2img_nsfw_lightning4_2511_d055_api.json",
    "sfw_aio_v11": "img2img_sfwclad_aio_v11.json",
    "nsfw_gfix_l10d60c2": "_recovered_AIGEN_gfix_l10d60c2.json",
    "nsfw_gfix2": "_recovered_AIGEN_gfix2.json",
    "nsfw_l_d100_recovered": "_recovered_AIGEN_LIGHTNING4_NSFW.json",
    "nsfw_community_qw": "_recovered_AIGEN_QW_COMMUNITY_NSFW.json",
    "sfw_aio_recovered": "_recovered_AIGEN_QWEN_SFW_AIO.json",
    "txt2img_perfect_delib": "txt2img_perfect_deliberate.json",
    "util_resize": "img2img_resize.json",
    "util_removebg": "img2img_removebg.json",
    "util_upscale": "img2img_upscale.json",
}

IMG2IMG_WFS = {
    "nsfw_community_h", "nsfw_l_d100", "nsfw_l_d055", "sfw_aio_v11",
    "nsfw_gfix_l10d60c2", "nsfw_gfix2", "nsfw_l_d100_recovered",
    "nsfw_community_qw", "sfw_aio_recovered",
    "util_resize", "util_removebg", "util_upscale",
}

TEXT_WFS = {
    "flux_long", "nsfw_community_h", "nsfw_l_d100", "nsfw_l_d055", "sfw_aio_v11",
    "nsfw_gfix_l10d60c2", "nsfw_gfix2", "nsfw_l_d100_recovered",
    "nsfw_community_qw", "sfw_aio_recovered", "txt2img_perfect_delib",
}

PROMPT_NODE_KEYS = ("text", "prompt")
PROMPT_NODE_TYPES = ("CLIPTextEncode", "TextEncodeQwenImageEditPlus")


def log(msg: str) -> None:
    print(msg, flush=True)


def free_vram() -> None:
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
        log("[run_wf] VRAM freed.")
    except Exception as exc:
        log(f"[run_wf] /free failed (ignored): {exc}")


def post_json(path: str, data: dict):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get_json(path: str):
    with urllib.request.urlopen(f"{COMFYUI_URL}{path}", timeout=30) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def upload_image(local_path: str) -> str:
    boundary = f"----OpenClawBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(local_path)
    with open(local_path, "rb") as f:
        file_bytes = f.read()
    lines = [
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode("utf-8"),
        b"Content-Type: application/octet-stream\r\n\r\n",
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(lines)
    req = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        result = json.loads(r.read().decode("utf-8"))
    if not result.get("name"):
        raise RuntimeError(f"Upload failed: {result}")
    return result["name"]


def find_prompt_node(workflow: dict):
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") not in PROMPT_NODE_TYPES:
            continue
        inputs = node.get("inputs", {})
        for key in PROMPT_NODE_KEYS:
            if key in inputs:
                return node_id, key
    return None, None


def find_image_node(workflow: dict):
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == "LoadImage":
            return node_id
    return None


def find_ksampler(workflow: dict):
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == "KSampler":
            return node_id
    return None


def load_workflow(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_queue_idle() -> bool:
    try:
        data = get_json("/queue")
        return len(data.get("queue_running", [])) == 0 and len(data.get("queue_pending", [])) == 0
    except Exception:
        return False


def wait_for_completion(max_wait: int = 600, poll_seconds: int = 5) -> bool:
    log("[run_wf] Waiting for completion...")
    waited = 0
    while waited < max_wait:
        if check_queue_idle():
            log("[run_wf] Done.")
            return True
        time.sleep(poll_seconds)
        waited += poll_seconds
        if waited % 30 == 0:
            log(f"[run_wf] ...still waiting ({waited}s)")
    return False


def resolve_output(prompt_id: str):
    try:
        history = get_json(f"/history/{prompt_id}")
    except Exception as exc:
        log(f"[run_wf] /history error: {exc}")
        history = {}
    if history and prompt_id in history:
        for node_output in history[prompt_id].get("outputs", {}).values():
            for image in node_output.get("images", []):
                candidate = os.path.join(
                    COMFYUI_OUTPUT,
                    image.get("subfolder", ""),
                    image.get("filename", ""),
                ).rstrip("/")
                if candidate and os.path.exists(candidate):
                    return candidate
    return None


def copy_to_workspace(src_path: str, out_name: str) -> str:
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    dst = os.path.join(WORKSPACE_DIR, out_name)
    shutil.copy2(src_path, dst)
    return dst


def print_listing() -> None:
    log("Available wf short names (use as first arg):")
    for k in sorted(WF_MAP):
        flags = []
        if k in IMG2IMG_WFS:
            flags.append("img2img")
        if k in TEXT_WFS:
            flags.append("text")
        flag_str = "[" + ",".join(flags) + "]" if flags else "[util]"
        log(f"  {k:30s}  {flag_str:18s}  {WF_MAP[k]}")


def main() -> int:
    p = argparse.ArgumentParser(description="ComfyUI /home/jagones/Repositories/comfyui-mcp/workflow_files/graphs universal launcher")
    p.add_argument("wf", help="wf short name (or 'list')")
    p.add_argument("prompt", nargs="?", default=None)
    p.add_argument("width", nargs="?", default="1024")
    p.add_argument("height", nargs="?", default="1024")
    p.add_argument("out_name", nargs="?", default="generated.png")
    p.add_argument("--file", help="Read prompt from file")
    p.add_argument("--image", help="Source image for img2img / utility")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--denoise", type=float, default=None)
    p.add_argument("--negative", help="Override negative prompt")
    p.add_argument("--workflow", help="Override wf path (skip mapping)")
    p.add_argument("--skip-free", action="store_true")
    args = p.parse_args()

    if args.wf == "list":
        print_listing()
        return 0

    if args.workflow:
        wf_path = args.workflow
        wf_name = os.path.basename(wf_path)
    else:
        if args.wf not in WF_MAP:
            log(f"ERROR: unknown wf '{args.wf}'. Run with 'list' to see options.")
            return 1
        wf_name = WF_MAP[args.wf]
        wf_path = os.path.join(WF_DIR, wf_name)

    if not os.path.exists(wf_path):
        log(f"ERROR: workflow not found: {wf_path}")
        return 1

    log(f"[run_wf] Loading {wf_name} from {wf_path}")
    workflow = load_workflow(wf_path)

    if args.wf in TEXT_WFS:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                prompt_text = f.read().strip()
        elif args.prompt:
            prompt_text = args.prompt
        else:
            log("ERROR: this wf requires a prompt (or --file).")
            return 1
        node_id, key = find_prompt_node(workflow)
        if not node_id:
            log("ERROR: no prompt node found in workflow.")
            return 1
        workflow[node_id]["inputs"][key] = prompt_text
        log(f"[run_wf] Injected prompt into node {node_id} (key={key}, {len(prompt_text)} chars)")
    else:
        log("[run_wf] Utility wf, no prompt needed.")

    if args.image:
        if not os.path.exists(args.image):
            log(f"ERROR: source image not found: {args.image}")
            return 1
        log(f"[run_wf] Uploading source image {args.image}...")
        uploaded = upload_image(args.image)
        node_id = find_image_node(workflow)
        if not node_id:
            log("ERROR: wf has no LoadImage node but --image was passed.")
            return 1
        workflow[node_id]["inputs"]["image"] = uploaded
        log(f"[run_wf] Injected uploaded image '{uploaded}' into node {node_id}")

    ks = find_ksampler(workflow)
    if ks:
        if args.seed is not None:
            workflow[ks]["inputs"]["seed"] = args.seed
        if args.steps is not None:
            workflow[ks]["inputs"]["steps"] = args.steps
        if args.cfg is not None:
            workflow[ks]["inputs"]["cfg"] = args.cfg
        if args.denoise is not None:
            workflow[ks]["inputs"]["denoise"] = args.denoise

    if args.negative:
        neg_nodes = [nid for nid, n in workflow.items()
                     if isinstance(n, dict) and n.get("class_type") == "CLIPTextEncode"]
        if len(neg_nodes) >= 2:
            workflow[neg_nodes[1]]["inputs"]["text"] = args.negative
            log(f"[run_wf] Injected negative prompt into node {neg_nodes[1]}")

    if not args.skip_free:
        free_vram()

    log(f"[run_wf] Submitting to {COMFYUI_URL}/prompt ...")
    try:
        result = post_json("/prompt", {"prompt": workflow})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        log(f"ERROR: submit HTTP {exc.code}: {body[:1000]}")
        return 2
    prompt_id = result.get("prompt_id")
    if not prompt_id:
        log(f"ERROR: no prompt_id in submit response: {result}")
        return 2
    log(f"[run_wf] prompt_id = {prompt_id}")

    if not wait_for_completion():
        log("ERROR: timeout waiting for completion.")
        return 3

    out_path = resolve_output(prompt_id)
    if not out_path:
        log("ERROR: could not resolve output file.")
        return 4
    log(f"[run_wf] Output: {out_path}")

    workspace_path = copy_to_workspace(out_path, args.out_name)
    log(f"READY_TO_SEND: {workspace_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
