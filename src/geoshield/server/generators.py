import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src/geoshield')

import json
import random
import pathlib
from typing import Dict, Any, List


def load_cases(task_id: int, split: str = "train") -> List[Dict[str, Any]]:
    possible_paths = [
        pathlib.Path(f"/app/data/task{task_id}_{split}.jsonl"),
        pathlib.Path(f"data/task{task_id}_{split}.jsonl"),
        pathlib.Path(__file__).parent.parent.parent.parent / "data" / f"task{task_id}_{split}.jsonl",
    ]

    path = None
    for p in possible_paths:
        if p.exists():
            path = p
            break

    if path is None:
        return [_fallback_case(task_id)]

    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return cases if cases else [_fallback_case(task_id)]


def sample_case(task_id: int, seed: int = None, split: str = "train") -> Dict[str, Any]:
    cases = load_cases(task_id, split)
    rng = random.Random(seed)
    return rng.choice(cases)


def _fallback_case(task_id: int) -> Dict[str, Any]:
    if task_id == 1:
        return {
            "id": "t1_fallback",
            "task": 1,
            "report": "Satellite scan — Sector 4: Movement detected. 3 large thermal signatures.",
            "context": "Border region, daytime, clear weather",
            "gold_action": "ignore",
            "difficulty": "easy",
            "category": "false_alarm"
        }
    elif task_id == 2:
        return {
            "id": "t2_fallback",
            "task": 2,
            "report": "Anomaly Report — Sector 9: Rapid concrete foundation laying detected near Border Alpha.",
            "context": "Remote area, no civilian permits on record",
            "gold_action": "illegal_construction",
            "gold_threat_level": 6,
            "difficulty": "easy",
            "category": "construction"
        }
    else:
        return {
            "id": "t3_fallback",
            "task": 3,
            "sectors": [
                {"sector_id": "sector_a", "summary": "3 thermal signatures, possibly animals", "confidence": 0.3},
                {"sector_id": "sector_b", "summary": "Unregistered convoy of 4 armored trucks", "confidence": 0.9},
                {"sector_id": "sector_c", "summary": "Civilian farming activity", "confidence": 0.8},
            ],
            "gold_action": "deploy_to_sector_b",
            "second_best_sector": "deploy_to_sector_a",
            "available_assets": "1 reconnaissance drone",
            "difficulty": "easy",
            "category": "allocation"
        }