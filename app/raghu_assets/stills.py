import json
import sys
import time
import torch
from diffusers import Flux2KleinPipeline
from huggingface_hub import snapshot_download
from PIL import Image
from common import ROOT, RESULTS, event

tasks = json.loads((ROOT / sys.argv[1]).read_text(encoding="utf-8"))
path = snapshot_download("black-forest-labs/FLUX.2-klein-4B",
    revision="e7b7dc27f91deacad38e78976d1f2b499d76a294", local_dir=ROOT / "models/image",
    token=False, allow_patterns=["model_index.json", "scheduler/*", "tokenizer/*",
        "text_encoder/*", "transformer/*", "vae/*"], max_workers=2)
pipe = Flux2KleinPipeline.from_pretrained(path, torch_dtype=torch.bfloat16).to("cuda")
output_dir = RESULTS / sys.argv[2] if len(sys.argv) > 2 else RESULTS
output_dir.mkdir(exist_ok=True)
for task in tasks:
    start = time.monotonic()
    refs = []
    for filename in task.get("generation_refs", task["refs"]):
        with Image.open(ROOT / filename) as image:
            refs.append(image.convert("RGB"))
    with torch.inference_mode():
        result = pipe(prompt=task["prompt"], image=refs or None, width=1536, height=864,
                      num_inference_steps=4, guidance_scale=1.0,
                      generator=torch.Generator("cuda").manual_seed(task["seed"])).images[0]
    out = output_dir / task["file"]
    temp = out.with_suffix(".partial.png")
    result.save(temp)
    temp.replace(out)
    event("still_done", name=out.name, seconds=time.monotonic() - start)
