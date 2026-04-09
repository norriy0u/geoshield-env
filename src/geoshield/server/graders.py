from typing import Dict, Any
from src.geoshield.models import GeoShieldAction, GeoReward
from src.geoshield.constants import STRATEGIC_KEYWORDS


# ── Task 1 grader ─────────────────────────────────────────────────────────────

def grade_task1(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold = case.get("gold_action")
    correct = action.action == gold

    if correct:
        return GeoReward(
            score=0.99,
            feedback=f"Correct! '{action.action}' matches gold action.",
            breakdown={"action_score": 0.99}
        )
    return GeoReward(
        score=0.01,
        feedback=f"Incorrect. Expected '{gold}', got '{action.action}'.",
        breakdown={"action_score": 0.01}
    )


# ── Task 2 grader ─────────────────────────────────────────────────────────────

RELATED_THREATS = {
    "troop_movement": ["weapons_cache", "illegal_construction"],
    "weapons_cache": ["troop_movement", "illegal_construction"],
    "illegal_construction": ["troop_movement", "unauthorized_aircraft"],
    "unauthorized_aircraft": ["illegal_construction", "weapons_cache"],
    "civilian_activity": [],
}

def grade_task2(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action")
    gold_level = case.get("gold_threat_level", 5)
    predicted_level = action.threat_level or 5

    # Classification score
    if action.action == gold_action:
        class_score = 0.99
    elif action.action in RELATED_THREATS.get(gold_action, []):
        class_score = 0.45
    else:
        class_score = 0.01

    # Threat level score
    diff = abs(predicted_level - gold_level)
    if diff == 0:
        level_score = 0.99
    elif diff == 1:
        level_score = 0.80
    elif diff == 2:
        level_score = 0.60
    elif diff == 3:
        level_score = 0.40
    else:
        level_score = 0.10

    final = round(0.5 * class_score + 0.5 * level_score, 3)
    final = max(0.01, min(0.99, final))

    return GeoReward(
        score=final,
        feedback=(
            f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} "
            f"(expected '{gold_action}'). "
            f"Threat level: {predicted_level} vs gold {gold_level} (diff={diff})."
        ),
        breakdown={
            "classification_score": class_score,
            "threat_level_score": level_score,
            "final_score": final,
        }
    )


# ── Task 3 grader ─────────────────────────────────────────────────────────────

def grade_task3(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action")
    second_best = case.get("second_best_sector", "")

    # Handle investigate actions
    if action.action.startswith("investigate_"):
        sector = action.action.replace("investigate_", "")
        gold_sector = gold_action.replace("deploy_to_", "")
        if sector == gold_sector:
            return GeoReward(
                score=0.55,
                feedback=f"Good — investigating the right sector ({sector}). Now deploy.",
                breakdown={"investigate_score": 0.55}
            )
        else:
            return GeoReward(
                score=0.25,
                feedback=f"Investigating {sector} — not the highest priority sector.",
                breakdown={"investigate_score": 0.25}
            )

    # Sector selection score
    if action.action == gold_action:
        sector_score = 0.99
    elif action.action == second_best:
        sector_score = 0.55
    else:
        sector_score = 0.01

    # Reasoning score
    reasoning = action.reasoning or ""
    reasoning_score = 0.10

    if len(reasoning) > 20:
        reasoning_score += 0.10
    if len(reasoning) > 80:
        reasoning_score += 0.10
    if len(reasoning) > 150:
        reasoning_score += 0.10

    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if kw.lower() in reasoning.lower())
    if keyword_hits >= 3:
        reasoning_score += 0.10
    if keyword_hits >= 5:
        reasoning_score += 0.10
    if keyword_hits >= 8:
        reasoning_score += 0.10

    reasoning_score = min(reasoning_score, 0.99)

    final = round(0.5 * sector_score + 0.5 * reasoning_score, 3)
    final = max(0.01, min(0.99, final))

    return GeoReward(
        score=final,
        feedback=(
            f"Sector: {'correct' if sector_score > 0.5 else 'incorrect'} "
            f"(expected '{gold_action}'). "
            f"Reasoning: {len(reasoning)} chars, {keyword_hits} keywords."
        ),
        breakdown={
            "sector_score": sector_score,
            "reasoning_score": reasoning_score,
            "keyword_hits": keyword_hits,
            "final_score": final,
        }
    )


# ── Task 4 grader ─────────────────────────────────────────────────────────────

DECEPTION_TYPES = {
    "civilian_military": "Military assets disguised as civilian infrastructure",
    "commercial_weapons": "Weapons development hidden inside commercial facilities",
    "construction_fortification": "Military fortification disguised as construction",
    "logistics_supply": "Military supply chain disguised as commercial logistics",
    "research_weapons": "Weapons research disguised as civilian research facility",
}

def grade_task4(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action")
    gold_cover = case.get("gold_cover_story", "")
    gold_deception = case.get("gold_deception_type", "")

    # Primary classification score
    if action.action == gold_action:
        class_score = 0.99
    elif action.action == "request_verification" and gold_action == "covert_operation":
        class_score = 0.50  # partial credit for cautious approach
    else:
        class_score = 0.01

    # Cover story identification score
    cover_score = 0.01
    identified_cover = (action.cover_story_identified or "").lower()
    gold_cover_lower = gold_cover.lower()

    cover_keywords = gold_cover_lower.split()
    hits = sum(1 for kw in cover_keywords if len(kw) > 4 and kw in identified_cover)
    if hits >= 3:
        cover_score = 0.99
    elif hits >= 2:
        cover_score = 0.70
    elif hits >= 1:
        cover_score = 0.40

    # Deception type score
    deception_score = 0.01
    if action.deception_type and gold_deception:
        if action.deception_type == gold_deception:
            deception_score = 0.99
        elif action.deception_type in DECEPTION_TYPES:
            deception_score = 0.30

    # Reasoning score
    reasoning = action.reasoning or ""
    reasoning_score = 0.10
    if len(reasoning) > 50:
        reasoning_score += 0.10
    if len(reasoning) > 150:
        reasoning_score += 0.15
    if len(reasoning) > 300:
        reasoning_score += 0.15
    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if kw.lower() in reasoning.lower())
    if keyword_hits >= 5:
        reasoning_score += 0.10
    if keyword_hits >= 8:
        reasoning_score += 0.15
    reasoning_score = min(reasoning_score, 0.99)

    # Weighted final
    final = round(
        0.40 * class_score +
        0.25 * cover_score +
        0.15 * deception_score +
        0.20 * reasoning_score,
        3
    )
    final = max(0.01, min(0.99, final))

    return GeoReward(
        score=final,
        feedback=(
            f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} "
            f"(expected '{gold_action}'). "
            f"Cover story: {hits} keyword matches. "
            f"Deception type: {'correct' if deception_score > 0.5 else 'incorrect'}. "
            f"Reasoning: {len(reasoning)} chars."
        ),
        breakdown={
            "classification_score": class_score,
            "cover_story_score": cover_score,
            "deception_type_score": deception_score,
            "reasoning_score": reasoning_score,
            "final_score": final,
        }
    )


# ── Registry ──────────────────────────────────────────────────────────────────

GRADERS = {
    1: grade_task1,
    2: grade_task2,
    3: grade_task3,
    4: grade_task4,
}