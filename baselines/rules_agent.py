"""
Rules-Based Agent Baseline
Uses keyword matching heuristics to make decisions.
Much better than random but worse than LLM.
Run: python baselines/rules_agent.py
"""

import requests
import time
from typing import List, Dict, Any

ENV_URL = "http://localhost:7860"

TASK_NAMES = {
    1: "false_alarm_detection",
    2: "threat_classification",
    3: "drone_allocation",
    4: "covert_operation_detection",
}

MAX_STEPS = 8

FALSE_ALARM_KEYWORDS = [
    "wildlife", "herbivore", "grazing", "animal",
    "weather", "sandstorm", "flooding", "wildfire",
    "registered", "valid permit", "permit on record",
    "civilian", "school", "hospital", "festival",
    "maintenance", "contractor", "utility",
    "livestock", "farming", "agricultural", "harvest",
    "marathon", "sports", "ceremony", "market",
    "fishing", "solar", "wind turbine", "pipeline inspection",
]

REAL_THREAT_KEYWORDS = [
    "unregistered", "no permit", "no civilian permit", "no permits",
    "armored", "military", "convoy", "tactical",
    "camouflage", "night operation", "unmarked vehicle",
    "underground", "bunker", "tunnel", "excavation",
    "weapons", "ammunition", "explosive", "artillery",
    "drone swarm", "no transponder", "stealth",
    "border crossing", "subsidence", "radiation",
    "0300", "nighttime", "pre-dawn",
]

THREAT_TYPE_KEYWORDS = {
    "troop_movement": [
        "convoy", "armored", "battalion", "infantry", "soldiers",
        "military vehicle", "troop", "platoon", "brigade", "column",
        "personnel carrier", "tank", "apc", "infiltration",
        "tactical", "formation", "advancing",
    ],
    "illegal_construction": [
        "concrete", "foundation", "bunker", "tunnel", "airstrip",
        "construction", "drilling", "fortif", "observation post",
        "antenna", "radar installation", "pontoon bridge",
        "deforestation", "clearing", "watchtower", "trench",
        "cable conduit", "submarine pen",
    ],
    "unauthorized_aircraft": [
        "aircraft", "drone", "uav", "balloon", "helicopter",
        "no transponder", "no flight plan", "no flight notification",
        "restricted airspace", "unregistered", "low altitude",
        "passes over", "hovering",
    ],
    "weapons_cache": [
        "weapon", "cache", "ammunition", "explosive", "rpg",
        "mortar", "ordnance", "missile", "artillery shell",
        "radiation shielding", "military lock", "chemical",
        "detonator", "sniper", "gun port", "armor plating",
    ],
    "civilian_activity": [
        "school", "hospital", "mosque", "church", "stadium",
        "community", "garden", "residential", "apartment",
        "fishing", "logging", "solar", "wind turbine",
        "market", "road repair", "municipal",
        "ngo", "refugee", "valid permit",
    ],
}

THREAT_LEVELS = {
    "troop_movement":       {"keywords": {"battalion": 10, "brigade": 10, "armored column": 9, "offensive": 9, "special forces": 8, "infiltration": 8, "patrol": 2, "routine": 2}, "default": 7},
    "illegal_construction": {"keywords": {"missile": 10, "anti-aircraft": 10, "submarine": 9, "airstrip": 9, "bunker": 9, "tunnel": 8, "radar": 8, "fortif": 8, "observation post": 7}, "default": 7},
    "unauthorized_aircraft":{"keywords": {"stealth": 9, "classified": 9, "swarm": 8, "helicopter": 8, "restricted airspace": 7, "no flight plan": 6, "balloon": 5}, "default": 6},
    "weapons_cache":        {"keywords": {"missile": 10, "radiation": 10, "chemical": 9, "explosive": 9, "rpg": 8, "mortar": 8, "artillery": 8, "ammunition": 7}, "default": 7},
    "civilian_activity":    {"keywords": {}, "default": 1},
}

SECTOR_PRIORITY = {
    "troop_movement": 5, "weapons_cache": 4, "illegal_construction": 3,
    "unauthorized_aircraft": 2, "civilian": 1, "wildfire": 1, "wildlife": 0,
}

# Task 4 — covert operation keyword sets
COVERT_KEYWORDS = [
    "military", "weapon", "classified", "encrypted", "anomal",
    "inconsistent", "exceeds", "military-grade", "defense", "combat",
    "blast-proof", "military spec", "military frequency", "sigint",
    "fortif", "bunker", "underground", "radiation", "explosive",
    "no civilian", "seismic", "camouflage",
]

DECEPTION_TYPE_MAP = {
    "pharmaceutical": "research_weapons",
    "medical":        "research_weapons",
    "laboratory":     "research_weapons",
    "research":       "research_weapons",
    "agricultural":   "logistics_supply",
    "logistics":      "logistics_supply",
    "cold storage":   "logistics_supply",
    "warehouse":      "logistics_supply",
    "construction":   "construction_fortification",
    "contractor":     "construction_fortification",
    "solar":          "civilian_military",
    "energy":         "civilian_military",
    "infrastructure": "civilian_military",
    "commercial":     "commercial_weapons",
    "factory":        "commercial_weapons",
    "manufacturing":  "commercial_weapons",
}


def env_reset(task_id: int, seed: int = None) -> dict:
    resp = requests.post(
        f"{ENV_URL}/reset",
        json={"task_id": task_id, "seed": seed, "split": "eval"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def env_step(action_data: dict, session_id: str) -> dict:
    action_data["session_id"] = session_id
    resp = requests.post(f"{ENV_URL}/step", json=action_data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def rules_task1(obs: Dict[str, Any]) -> dict:
    report = (obs.get("report", "") + " " + obs.get("context", "")).lower()
    threat_score = sum(1 for kw in REAL_THREAT_KEYWORDS if kw in report)
    false_score  = sum(1 for kw in FALSE_ALARM_KEYWORDS if kw in report)
    return {"action": "flag_for_review" if threat_score > false_score else "ignore"}


def rules_task2(obs: Dict[str, Any]) -> dict:
    report = (obs.get("report", "") + " " + obs.get("context", "")).lower()
    type_scores: Dict[str, int] = {
        t: sum(1 for kw in kws if kw in report)
        for t, kws in THREAT_TYPE_KEYWORDS.items()
    }
    best_type    = max(type_scores, key=lambda t: type_scores[t])
    level_info   = THREAT_LEVELS.get(best_type, {"keywords": {}, "default": 5})
    threat_level = level_info["default"]
    for kw, level in level_info["keywords"].items():
        if kw in report:
            threat_level = max(threat_level, level)
    return {"action": best_type, "threat_level": threat_level}


def rules_task3(obs: Dict[str, Any]) -> dict:
    sectors      = obs.get("sectors", [])
    best_sector  = None
    best_priority = -1
    best_sector_id = "sector_a"

    for sector in sectors:
        anomaly_type = sector.get("anomaly_type", "civilian")
        confidence   = sector.get("confidence", 0.5)
        priority     = SECTOR_PRIORITY.get(anomaly_type, 0) * confidence
        if priority > best_priority:
            best_priority  = priority
            best_sector    = sector
            best_sector_id = sector.get("sector_id", "sector_a")

    anomaly    = best_sector.get("anomaly_type", "unknown") if best_sector else "unknown"
    summary    = best_sector.get("summary", "N/A") if best_sector else "N/A"
    confidence = best_sector.get("confidence", 0) if best_sector else 0
    reasoning  = (
        f"Rules-based analysis selected {best_sector_id.upper()} as highest priority sector. "
        f"Detected anomaly type: {anomaly} with confidence {confidence:.0%}. "
        f"Sector summary: {summary}. "
        f"Priority scoring assigned {anomaly} a threat weight of {SECTOR_PRIORITY.get(anomaly, 0)}, "
        f"which ranked highest among all sectors after weighting by detection confidence. "
        f"Deploying reconnaissance drone to {best_sector_id.upper()} for immediate intelligence gathering."
    )
    return {"action": f"deploy_to_{best_sector_id}", "target_sector": best_sector_id, "reasoning": reasoning}


def rules_task4(obs: Dict[str, Any]) -> dict:
    report = (obs.get("report", "") + " " + obs.get("context", "")).lower()
    indicators = obs.get("deception_indicators") or []

    covert_hits = sum(1 for kw in COVERT_KEYWORDS if kw in report)

    # Determine deception type from report keywords
    deception_type = "civilian_military"
    for kw, dtype in DECEPTION_TYPE_MAP.items():
        if kw in report:
            deception_type = dtype
            break

    # Extract cover story hint from report (first sentence)
    report_raw = obs.get("report", "")
    cover_story = report_raw.split(".")[0].strip() if report_raw else "civilian facility"

    if covert_hits >= 2 or len(indicators) >= 2:
        reasoning = (
            f"Rules-based analysis detected {covert_hits} covert indicators in the report. "
            f"Anomalies present: {'; '.join(indicators[:3]) if indicators else 'multiple inconsistencies detected'}. "
            f"Cover story appears to be civilian facade concealing military or weapons activity. "
            f"Deception pattern matches {deception_type} category based on facility type and keyword analysis. "
            f"Classifying as covert operation."
        )
        return {
            "action": "covert_operation",
            "cover_story_identified": cover_story,
            "deception_type": deception_type,
            "reasoning": reasoning,
        }

    reasoning = (
        f"Rules-based analysis found only {covert_hits} covert indicators. "
        f"No strong anomalies detected. Facility appears consistent with declared civilian purpose. "
        f"Classifying as legitimate activity."
    )
    return {
        "action": "legitimate_activity",
        "cover_story_identified": "",
        "deception_type": "",
        "reasoning": reasoning,
    }


RULE_FUNCTIONS = {
    1: rules_task1,
    2: rules_task2,
    3: rules_task3,
    4: rules_task4,
}


def run_episode(task_id: int, seed: int) -> float:
    print(f"\n[Rules Agent] Task {task_id}: {TASK_NAMES[task_id]}", flush=True)

    result     = env_reset(task_id=task_id, seed=seed)
    session_id = result.get("session_id", "default")
    obs        = result.get("observation", {})
    done       = result.get("done", False)
    rewards: List[float] = []
    rule_fn    = RULE_FUNCTIONS[task_id]

    for step in range(1, MAX_STEPS + 1):
        if done:
            break
        action_data = rule_fn(obs)
        result      = env_step(action_data, session_id)
        reward      = float(result.get("reward", 0.0))
        done        = result.get("done", False)
        info        = result.get("info", {})
        obs         = result.get("observation", obs) or obs
        rewards.append(reward)

        print(f"  Step {step}: action={action_data['action']} reward={reward:.3f} done={done}", flush=True)
        print(f"  Feedback: {info.get('feedback', 'N/A')}", flush=True)

        if done:
            break
        time.sleep(0.2)

    score = sum(rewards) / len(rewards) if rewards else 0.0
    print(f"[Rules Agent] Task {task_id} score: {score:.3f}", flush=True)
    return score


def main():
    print("=" * 50)
    print("GeoShield — Rules-Based Agent Baseline")
    print("=" * 50)

    scores = []
    for task_id in [1, 2, 3, 4]:
        score = run_episode(task_id=task_id, seed=42)
        scores.append(score)
        time.sleep(0.5)

    overall = sum(scores) / len(scores)
    print("\n" + "=" * 50)
    print("Rules Agent Results:")
    print(f"  Task 1 (false_alarm_detection):     {scores[0]:.3f}")
    print(f"  Task 2 (threat_classification):     {scores[1]:.3f}")
    print(f"  Task 3 (drone_allocation):          {scores[2]:.3f}")
    print(f"  Task 4 (covert_operation_detection):{scores[3]:.3f}")
    print(f"  Overall:                            {overall:.3f}")
    print("=" * 50)
    print("Expected rules scores:")
    print("  Task 1: ~0.75  (keyword matching works well)")
    print("  Task 2: ~0.55  (classification ok, threat level rough)")
    print("  Task 3: ~0.55  (priority matrix works, reasoning generic)")
    print("  Task 4: ~0.40  (covert detection reasonable, cover/deception partial)")
    print("=" * 50)


if __name__ == "__main__":
    main()
