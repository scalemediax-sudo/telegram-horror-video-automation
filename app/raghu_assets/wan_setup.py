"""Download and cache the public ComfyUI Wan 2.2 motion weights on Vast."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time

from huggingface_hub import hf_hub_download
from common import ROOT, event


def download(item):
    group, filename, repo = item
    started = time.monotonic()
    target = ROOT / "ComfyUI" / "models" / group / filename
    if not target.is_file():
        cache = Path(hf_hub_download("Comfy-Org/" + repo, f"split_files/{group}/{filename}",
                                     local_dir=ROOT / "wan-downloads", token=False))
        target.parent.mkdir(parents=True, exist_ok=True)
        cache.replace(target)
    event("model_download", file=filename, bytes=target.stat().st_size, seconds=time.monotonic() - started)


files = [
    ("diffusion_models", "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "Wan_2.2_ComfyUI_Repackaged"),
    ("diffusion_models", "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "Wan_2.2_ComfyUI_Repackaged"),
    ("text_encoders", "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "Wan_2.1_ComfyUI_repackaged"),
    ("vae", "wan_2.1_vae.safetensors", "Wan_2.2_ComfyUI_Repackaged"),
]
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(download, files))
event("downloads_finished")
