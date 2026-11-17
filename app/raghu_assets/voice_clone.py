"""Synthesize Hindi narrator lines on the existing Vast worker."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from chatterbox.models.tokenizers.tokenizer import ChineseCangjieConverter
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from huggingface_hub import snapshot_download

from common import ROOT, event


def main():
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reference = ROOT / manifest["reference"]
    output = ROOT / "results" / manifest["output"]
    output.mkdir(exist_ok=True)
    missing = [line for line in manifest["lines"]
               if not (output / f"narration-{line['id']}.wav").is_file()]
    if not missing:
        return

    # Hindi never uses the Chinese segmenter in this pinned multilingual build.
    ChineseCangjieConverter._init_segmenter = lambda self: setattr(self, "segmenter", None)
    repo = "ResembleAI/chatterbox"
    start = time.monotonic()
    weights = snapshot_download(
        repo,
        revision="5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18",
        allow_patterns=["ve.pt", "t3_mtl23ls_v3.safetensors", "s3gen.pt",
                        "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"],
    )
    event("narrator_model_ready", repo=repo, seconds=time.monotonic() - start)
    model = ChatterboxMultilingualTTS.from_local(weights, device="cuda", t3_model="v3")
    for line in missing:
        ident = line["id"]
        torch.manual_seed(4291 + int(ident))
        start = time.monotonic()
        wav = model.generate(line["text"], language_id="hi", audio_prompt_path=str(reference),
                             exaggeration=.46, cfg_weight=.45, temperature=.6).squeeze().cpu().numpy()
        active = np.flatnonzero(np.abs(wav) > .008)
        if not len(active):
            raise ValueError(f"Narrator returned silence for shot {ident}.")
        margin = int(.1 * model.sr)
        wav = wav[max(0, active[0] - margin):min(len(wav), active[-1] + margin)]
        target = output / f"narration-{ident}.wav"
        partial = target.with_suffix(".partial.wav")
        sf.write(partial, wav, model.sr)
        partial.replace(target)
        event("narrator_line_ready", id=ident, seconds=time.monotonic() - start,
              duration=len(wav) / model.sr)


if __name__ == "__main__":
    main()
