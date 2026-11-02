#!/usr/bin/env python3
"""Descrive/captions a local image with Qwen3-VL-4B-Instruct on the DGX.

When the active chat model has no vision endpoint (vision_analyze 404s with
'No endpoints found that support image input'), run THIS as your eyes.

Usage:
  /home/jagones/ComfyUI/venv/bin/python caption_local.py <image> [known-model-path]

Uses the EXPLICIT Qwen3VLForConditionalGeneration class (AutoModelForCausalLM
does NOT register Qwen3VL in the ComfyUI venv's transformers 5.1.0) and sdpa
attention (flash_attn is not installed). Run as a one-shot process so VRAM
(~7 GB) frees on exit before a long video chain starts.

Output: caption between CAPTION_START / CAPTION_END markers.
"""
import sys
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from PIL import Image
import torch

img_path = sys.argv[1]
mdl = (sys.argv[2] if len(sys.argv) > 2
       else "/home/jagones/ComfyUI/models/LLM/Qwen-VL/Qwen3-VL-4B-Instruct")

print(f"loading {mdl}...", flush=True)
proc = AutoProcessor.from_pretrained(mdl)
model = Qwen3VLForConditionalGeneration.from_pretrained(
    mdl, torch_dtype=torch.bfloat16, device_map="auto",
    attn_implementation="sdpa",
)
image = Image.open(img_path).convert("RGB")
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": (
                "Describe this image in detail for a video generation engine. "
                "Identify: (1) the main subject and what it is doing, (2) the setting/location, "
                "(3) the implied motion/direction, (4) key visual elements and composition. "
                "Write a dense cinematic caption in English, 80-120 words."
            )},
        ],
    }
]
text = proc.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = proc(text=[text], images=[image], return_tensors="pt").to(model.device, torch.bfloat16)
with torch.inference_mode():
    out = model.generate(**inputs, max_new_tokens=256, do_sample=False)
caption = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
print("CAPTION_START")
print(caption)
print("CAPTION_END")
