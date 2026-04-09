import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src/geoshield')

from typing import Dict, Any
from models import GeoShieldAction, GeoReward


def _clamp(score: float) -> float:
    """Score must be strictly between 0 and 1"""
    score = round(score, 3)
    if score <= 0.0:
        return 0.01
    if score >= 1.0:
        return 0.99
    return score


# ── Task 1 Grader ─────────────────────────────────────────────────────────────

TASK1_CORRECT = {
    "ignore": "ignore",
    "flag_for_review": "flag_for_review",
}

def grade_task1(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold = case.get("gold_action", "")
    agent = action.action.strip().lower()

    if agent == gold:
        score = 0.99
        feedback = f"Correct! '{agent}' matches gold action."
    else:
        score = 0.01
        feedback = f"Incorrect. You chose '{agent}', gold was '{gold}'."

    return GeoReward(
        score=_clamp(score),
        feedback=feedback,
        breakdown={
            "gold_action": gold,
            "agent_action": agent,
            "difficulty": case.get("difficulty", "easy"),
        }
    )


# ── Task 2 Grader ─────────────────────────────────────────────────────────────

CLASSIFICATION_PROXIMITY = {
    "troop_movement":        {"troop_movement": 0.99, "weapons_cache": 0.5, "unauthorized_aircraft": 0.3, "illegal_construction": 0.1, "civilian_activity": 0.01},
    "illegal_construction":  {"illegal_construction": 0.99, "civilian_activity": 0.4, "weapons_cache": 0.2, "troop_movement": 0.1, "unauthorized_aircraft": 0.01},
    "unauthorized_aircraft": {"unauthorized_aircraft": 0.99, "troop_movement": 0.4, "weapons_cache": 0.2, "illegal_construction": 0.1, "civilian_activity": 0.01},
    "weapons_cache":         {"weapons_cache": 0.99, "troop_movement": 0.5, "illegal_construction": 0.2, "unauthorized_aircraft": 0.2, "civilian_activity": 0.01},
    "civilian_activity":     {"civilian_activity": 0.99, "illegal_construction": 0.3, "troop_movement": 0.01, "unauthorized_aircraft": 0.01, "weapons_cache": 0.01},
}

def grade_task2(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_class = case.get("gold_action", "")
    gold_level = int(case.get("gold_threat_level", 5))
    agent_class = action.action.strip().lower()
    agent_level = action.threat_level or 5

    # Classification score (0.5 weight)
    class_score = CLASSIFICATION_PROXIMITY.get(gold_class, {}).get(agent_class, 0.01)

    # Threat level score (0.5 weight) — closer to gold = higher score
    level_diff = abs(agent_level - gold_level)
    if level_diff == 0:
        level_score = 0.99
    elif level_diff == 1:
        level_score = 0.8
    elif level_diff == 2:
        level_score = 0.6
    elif level_diff == 3:
        level_score = 0.4
    elif level_diff <= 5:
        level_score = 0.2
    else:
        level_score = 0.01

    # Combined score
    combined = (class_score * 0.5) + (level_score * 0.5)

    feedback = (
        f"Classification: '{agent_class}' vs gold '{gold_class}' (score: {class_score:.2f}). "
        f"Threat level: {agent_level} vs gold {gold_level} (score: {level_score:.2f})."
    )

    return GeoReward(
        score=_clamp(combined),
        feedback=feedback,
        breakdown={
            "gold_action": gold_class,
            "agent_action": agent_class,
            "gold_threat_level": gold_level,
            "agent_threat_level": agent_level,
            "classification_score": class_score,
            "level_score": level_score,
            "difficulty": case.get("difficulty", "easy"),
        }
    )


# ── Task 3 Grader ─────────────────────────────────────────────────────────────

def grade_task3(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_sector = case.get("gold_action", "")
    agent_sector = action.target_sector or action.action.strip().lower()
    reasoning = action.reasoning or ""

    # Sector selection score (0.5 weight)
    if agent_sector == gold_sector:
        sector_score = 0.5
        sector_feedback = f"Correct sector '{agent_sector}'."
    else:
        # Partial credit if second-best sector
        second_best = case.get("second_best_sector", "")
        if agent_sector == second_best:
            sector_score = 0.25
            sector_feedback = f"Second-best sector. Gold was '{gold_sector}'."
        else:
            sector_score = 0.01
            sector_feedback = f"Wrong sector '{agent_sector}'. Gold was '{gold_sector}'."

    # Reasoning score (0.5 weight)
    reasoning_score = 0.01
    if len(reasoning.strip()) > 20:
        reasoning_score += 0.1
    if len(reasoning.strip()) > 80:
        reasoning_score += 0.1
    if len(reasoning.strip()) > 150:
        reasoning_score += 0.1

    # Keyword bonus
    keywords = [
        "threat", "priority", "sector", "critical", "intelligence",
        "deploy", "risk", "anomaly", "military", "hostile",
        "construction", "movement", "aircraft", "convoy", "bunker"
    ]
    matches = sum(1 for kw in keywords if kw in reasoning.lower())
    if matches >= 3:
        reasoning_score += 0.1
    if matches >= 5:
        reasoning_score += 0.1

    reasoning_score = min(0.5, reasoning_score)

    combined = sector_score + reasoning_score

    feedback = (
        f"{sector_feedback} "
        f"Reasoning score: {reasoning_score:.2f} "
        f"(length: {len(reasoning)} chars, keywords: {matches})."
    )

    return GeoReward(
        score=_clamp(combined),
        feedback=feedback,
        breakdown={
            "gold_sector": gold_sector,
            "agent_sector": agent_sector,
            "sector_score": sector_score,
            "reasoning_score": reasoning_score,
            "reasoning_length": len(reasoning),
            "keyword_matches": matches,
            "difficulty": case.get("difficulty", "easy"),
        }
    )


GRADERS = {
    1: grade_task1,
    2: grade_task2,
    3: grade_task3,
}