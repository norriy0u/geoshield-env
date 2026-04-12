"""
GeoShield Case Generators — Hybrid static + procedural case sampling.

Supports two modes:
  1. Static: Load cases from pre-authored JSONL data files
  2. Procedural: Generate unlimited cases from parameterized templates

The procedural system is the default and produces deterministic cases
from seed values, guaranteeing reproducibility while eliminating
memorization risk from a fixed dataset.
"""

import json
import random
import os
from typing import Dict, Any, List

from src.geoshield.server.procedural_generator import generate_procedural_case

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')


def load_cases(task_id: int, split: str = "train") -> List[Dict[str, Any]]:
    """Load static cases from JSONL data files."""
    path = os.path.join(DATA_DIR, f"task{task_id}_{split}.jsonl")
    cases = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        cases.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        pass
    return cases


def _validate_case(case: Dict[str, Any], task_id: int) -> Dict[str, Any]:
    """Ensure all required fields exist with safe defaults so graders never receive None."""
    from src.geoshield.constants import VALID_GOLD_ACTIONS, DEFAULT_GOLD_ACTIONS

    # Ensure gold_action is valid
    gold = case.get("gold_action", "")
    valid = VALID_GOLD_ACTIONS.get(task_id, [])
    if gold not in valid:
        case["gold_action"] = DEFAULT_GOLD_ACTIONS.get(task_id, "ignore")

    # Task-specific field defaults
    if task_id == 1:
        case.setdefault("difficulty", "easy")
        case.setdefault("report", "No activity detected in monitored zone.")
        case.setdefault("context", "Routine patrol sector.")
        case.setdefault("additional_context", "No additional intelligence available for this sector.")

    elif task_id == 2:
        case.setdefault("difficulty", "medium")
        case.setdefault("report", "Unidentified activity detected.")
        case.setdefault("context", "Border zone monitoring.")
        case.setdefault("analysis_detail", "Sensor analysis pending. No additional data available.")
        # gold_threat_level must be int 1-10
        raw = case.get("gold_threat_level", 5)
        try:
            level = int(raw)
            case["gold_threat_level"] = max(1, min(10, level))
        except (TypeError, ValueError):
            case["gold_threat_level"] = 5

    elif task_id == 3:
        case.setdefault("difficulty", "hard")
        case.setdefault("available_assets", "1 surveillance drone")
        # Ensure sectors list exists and has valid structure
        sectors = case.get("sectors", [])
        if not sectors or not isinstance(sectors, list):
            case["sectors"] = [
                {"sector_id": "sector_a", "summary": "No activity.", "anomaly_type": "none", "confidence": 0.3, "coordinates": "0.0N,0.0E", "timestamp": "00:00Z"},
                {"sector_id": "sector_b", "summary": "Suspicious movement.", "anomaly_type": "troop_movement", "confidence": 0.7, "coordinates": "1.0N,1.0E", "timestamp": "01:00Z"},
                {"sector_id": "sector_c", "summary": "No activity.", "anomaly_type": "none", "confidence": 0.2, "coordinates": "2.0N,2.0E", "timestamp": "02:00Z"},
            ]
            if case["gold_action"] == DEFAULT_GOLD_ACTIONS[3]:
                case["gold_action"] = "deploy_to_sector_b"
        # Ensure second_best_sector exists
        case.setdefault("second_best_sector", "")

    elif task_id == 4:
        case.setdefault("difficulty", "ultra")
        case.setdefault("report", "Facility under observation.")
        case.setdefault("context", "Intelligence assessment required.")
        case.setdefault("gold_cover_story", "")
        case.setdefault("gold_deception_type", "")
        case.setdefault("deception_indicators", [])

    case.setdefault("id", f"t{task_id}_case_{random.randint(1000,9999)}")
    case.setdefault("hint", "")
    return case


def sample_case(task_id: int, seed: int = 42, split: str = "train") -> Dict[str, Any]:
    """Sample a case using procedural generation (primary) or static data (fallback).

    The procedural generator is used by default, producing deterministic cases
    from seed values. This guarantees reproducibility while providing virtually
    unlimited unique cases (no memorization risk).

    Static JSONL data files are used as fallback if procedural generation fails.
    """
    # Primary: procedural generation
    try:
        case = generate_procedural_case(task_id, seed)
        return _validate_case(case, task_id)
    except Exception:
        pass

    # Fallback: static data files
    cases = load_cases(task_id, split)
    if not cases:
        case = _make_fallback_case(task_id)
    else:
        rng = random.Random(seed)
        case = dict(rng.choice(cases))  # copy so we don't mutate the list

    return _validate_case(case, task_id)


def _make_fallback_case(task_id: int) -> Dict[str, Any]:
    """Returns a minimal valid case when both procedural and data files fail."""
    if task_id == 1:
        return {"id": "t1_fallback", "gold_action": "ignore", "difficulty": "easy",
                "report": "Routine satellite pass. No anomalies detected.", "context": "Standard monitoring.",
                "additional_context": "Historical data confirms no prior activity in this zone."}
    elif task_id == 2:
        return {"id": "t2_fallback", "gold_action": "civilian_activity", "gold_threat_level": 2,
                "difficulty": "medium", "report": "Agricultural vehicles observed near border.", "context": "Farming region.",
                "analysis_detail": "Spectral analysis confirms agricultural equipment signatures only."}
    elif task_id == 3:
        return {
            "id": "t3_fallback", "gold_action": "deploy_to_sector_b",
            "second_best_sector": "deploy_to_sector_a", "difficulty": "hard",
            "available_assets": "1 surveillance drone",
            "sectors": [
                {"sector_id": "sector_a", "summary": "Minimal activity.", "anomaly_type": "civilian_activity", "confidence": 0.4, "coordinates": "10.0N,20.0E", "timestamp": "06:00Z"},
                {"sector_id": "sector_b", "summary": "Armed convoy detected moving toward border.", "anomaly_type": "troop_movement", "confidence": 0.9, "coordinates": "11.0N,21.0E", "timestamp": "06:15Z"},
                {"sector_id": "sector_c", "summary": "Agricultural equipment.", "anomaly_type": "civilian_activity", "confidence": 0.2, "coordinates": "12.0N,22.0E", "timestamp": "06:30Z"},
            ]
        }
    else:
        return {"id": "t4_fallback", "gold_action": "covert_operation",
                "gold_cover_story": "agricultural research facility",
                "gold_deception_type": "research_weapons", "difficulty": "ultra",
                "report": "Facility declared as agricultural research. Satellite shows reinforced structures inconsistent with farming.",
                "context": "Border region.", "deception_indicators": ["reinforced perimeter", "military vehicles", "encrypted communications"]}
