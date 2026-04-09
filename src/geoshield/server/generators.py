import json
import random
import os
from typing import Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')


def load_cases(task_id: int, split: str = "train"):
    path = os.path.join(DATA_DIR, f"task{task_id}_{split}.jsonl")
    cases = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def sample_case(task_id: int, seed: int = 42, split: str = "train") -> Dict[str, Any]:
    cases = load_cases(task_id, split)
    rng = random.Random(seed)
    return rng.choice(cases)