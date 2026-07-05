from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import pandas as pd

STORE_PATH = Path("data/scenario_history.jsonl")


def save_scenario(params: dict, result: pd.DataFrame) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    summary = result.to_dict(orient="records")

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "params": params,
        "summary": summary,
    }

    with open(STORE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_scenarios() -> list[dict]:
    if not STORE_PATH.exists():
        return []

    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f.readlines()]