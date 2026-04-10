from typing import Dict, Any
from src.geoshield.models import GeoShieldAction, GeoReward
from src.geoshield.constants import STRATEGIC_KEYWORDS


def _clamp(score: float) -> float:
    try:
        return round(max(0.02, min(0.98, float(score))), 4)
    except Exception:
        return 0.02


RELATED_THREATS = {
    "troop_movement": ["weapons_cache", "illegal_construction"],
    "weapons_cache": ["troop_movement", "illegal_construction"],
    "illegal_construction": ["troop_movement", "unauthorized_aircraft"],
    "unauthorized_aircraft": ["illegal_construction", "weapons_cache"],
    "civilian_activity": [],
}

DECEPTION_TYPES = {
    "civilian_military": "Military assets disguised as civilian infrastructure",
    "commercial_weapons": "Weapons development hidden inside commercial facilities",
    "construction_fortification": "Military fortification disguised as construction",
    "logistics_supply": "Military supply chain disguised as commercial logistics",
    "research_weapons": "Weapons research disguised as civilian research facility",
}


def grade_task1(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold = case.get("gold_action")
    if action.action == gold:
        return GeoReward(score=_clamp(0.98), feedback=f"Correct! '{action.action}' matches gold.", breakdown={"action_score": 0.98})
    return GeoReward(score=_clamp(0.02), feedback=f"Incorrect. Expected '{gold}', got '{action.action}'.", breakdown={"action_score": 0.02})


def grade_task2(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action")
    gold_level = case.get("gold_threat_level", 5)
    predicted_level = action.threat_level or 5

    if action.action == gold_action:
        class_score = 0.98
    elif action.action in RELATED_THREATS.get(gold_action, []):
        class_score = 0.45
    else:
        class_score = 0.02

    diff = abs(predicted_level - gold_level)
    if diff == 0:   level_score = 0.98
    elif diff == 1: level_score = 0.80
    elif diff == 2: level_score = 0.60
    elif diff == 3: level_score = 0.40
    else:           level_score = 0.10

    final = _clamp(0.5 * class_score + 0.5 * level_score)
    return GeoReward(
        score=final,
        feedback=f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Level: {predicted_level} vs {gold_level} (diff={diff}).",
        breakdown={"classification_score": class_score, "threat_level_score": level_score, "final_score": final}
    )


def grade_task3(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action")
    second_best = case.get("second_best_sector", "")

    if action.action.startswith("investigate_"):
        sector = action.action.replace("investigate_", "")
        gold_sector = gold_action.replace("deploy_to_", "")
        if sector == gold_sector:
            return GeoReward(score=_clamp(0.55), feedback=f"Good - investigating right sector ({sector}).", breakdown={"investigate_score": 0.55})
        return GeoReward(score=_clamp(0.25), feedback=f"Investigating {sector} - not highest priority.", breakdown={"investigate_score": 0.25})

    if action.action == gold_action:
        sector_score = 0.98
    elif action.action == second_best:
        sector_score = 0.55
    else:
        sector_score = 0.02

    reasoning = action.reasoning or ""
    reasoning_score = 0.10
    if len(reasoning) > 20:  reasoning_score += 0.10
    if len(reasoning) > 80:  reasoning_score += 0.10
    if len(reasoning) > 150: reasoning_score += 0.10

    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if kw.lower() in reasoning.lower())
    if keyword_hits >= 3: reasoning_score += 0.10
    if keyword_hits >= 5: reasoning_score += 0.10
    if keyword_hits >= 8: reasoning_score += 0.10
    reasoning_score = min(reasoning_score, 0.98)

    final = _clamp(0.5 * sector_score + 0.5 * reasoning_score)
    return GeoReward(
        score=final,
        feedback=f"Sector: {'correct' if sector_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Reasoning: {len(reasoning)} chars, {keyword_hits} keywords.",
        breakdown={"sector_score": sector_score, "reasoning_score": reasoning_score, "final_score": final}
    )


def grade_task4(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action")
    gold_cover = case.get("gold_cover_story", "")
    gold_deception = case.get("gold_deception_type", "")

    if action.action == gold_action:
        class_score = 0.98
    elif action.action == "request_verification" and gold_action == "covert_operation":
        class_score = 0.50
    else:
        class_score = 0.02

    identified_cover = (action.cover_story_identified or "").lower()
    cover_keywords = gold_cover.lower().split()
    hits = sum(1 for kw in cover_keywords if len(kw) > 4 and kw in identified_cover)
    if hits >= 3:   cover_score = 0.98
    elif hits >= 2: cover_score = 0.70
    elif hits >= 1: cover_score = 0.40
    else:           cover_score = 0.02

    deception_score = 0.02
    if action.deception_type and gold_deception:
        if action.deception_type == gold_deception:
            deception_score = 0.98
        elif action.deception_type in DECEPTION_TYPES:
            deception_score = 0.30

    reasoning = action.reasoning or ""
    reasoning_score = 0.10
    if len(reasoning) > 50:  reasoning_score += 0.10
    if len(reasoning) > 150: reasoning_score += 0.15
    if len(reasoning) > 300: reasoning_score += 0.15
    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if kw.lower() in reasoning.lower())
    if keyword_hits >= 5: reasoning_score += 0.10
    if keyword_hits >= 8: reasoning_score += 0.15
    reasoning_score = min(reasoning_score, 0.98)

    final = _clamp(0.40 * class_score + 0.25 * cover_score + 0.15 * deception_score + 0.20 * reasoning_score)
    return GeoReward(
        score=final,
        feedback=f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Cover: {hits} hits. Deception: {'correct' if deception_score > 0.5 else 'incorrect'}. Reasoning: {len(reasoning)} chars.",
        breakdown={"classification_score": class_score, "cover_story_score": cover_score, "deception_type_score": deception_score, "reasoning_score": reasoning_score, "final_score": final}
    )


GRADERS = {
    1: grade_task1,
    2: grade_task2,
    3: grade_task3,
    4: grade_task4,
}
