import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

def event(stage, **data):
    row = json.dumps({"time": time.time(), "stage": stage, **data})
    with (RESULTS / "events.jsonl").open("a") as stream:
        stream.write(row + "\n")
    print(row, flush=True)
