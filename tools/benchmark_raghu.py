"""Benchmark existing, approved starting images on one rented Vast GPU."""
import argparse
import json
import shutil
import shlex
import statistics
import uuid
from pathlib import Path

from app import store
from app.raghu_vast import rent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("stills", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--offload", choices=("cpu", "none"), default="cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    plan = store.read(args.plan)
    for shot in plan["shots"]:
        if not shot.get("ending_image_file") or shot.get("ending_frame") != shot["frames"] - 1:
            parser.error("Each benchmark shot requires an ending image at frames - 1.")
    inputs = sorted({shot[key] for shot in plan["shots"] for key in ("starting_image_file", "ending_image_file")})
    for name in inputs:
        if Path(name).name != name:
            raise ValueError("The approved fixture must contain simple file names.")
        shutil.copyfile(args.stills / name, args.output / name)
    store.save(args.output / "render-plan.json", plan)
    ident = "benchmark-" + uuid.uuid4().hex[:12]
    with rent(args.output, ident, lambda: None) as remote:
        remote.push([args.output / name for name in [*inputs, "render-plan.json"]])
        remote.phase("mv -- " + " ".join(map(shlex.quote, inputs)) + " results/", 60)
        try:
            remote.phase(f"LTX_OFFLOAD={args.offload} bash worker.sh motion >results/motion.log 2>&1", 3600)
            remote.pull([f"shot-{shot['id']}.mp4" for shot in plan["shots"]], args.output)
        finally:
            try:
                remote.pull(["motion.log", "events.jsonl"], args.output)
            except (RuntimeError, TimeoutError):
                pass
    results = [json.loads(line) for line in (args.output / "events.jsonl").read_text().splitlines()]
    times = [r["seconds"] for r in results if r["stage"] == "video_done"]
    if len(times) != len(plan["shots"]):
        raise RuntimeError("The benchmark did not render every shot.")
    metrics = {"seconds": times, "mean": statistics.mean(times),
               "warm_mean": statistics.mean(times[1:]) if len(times) > 1 else times[0]}
    store.save(args.output / "benchmark.json", metrics)
    print(json.dumps(metrics))

if __name__ == "__main__":
    main()
