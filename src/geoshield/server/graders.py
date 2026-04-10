from typing import Dict, Any
from src.geoshield.models import GeoShieldAction, GeoReward
from src.geoshield.constants import STRATEGIC_KEYWORDS


def _clamp(score: float) -> float:
    try:
        return round(max(0.02, min(0.98, float(score))), 4)
    except Exception:
        return 0.02


RELATED_THREATS = {
    "troop_movement":        ["weapons_cache", "illegal_construction"],
    "weapons_cache":         ["troop_movement", "illegal_construction"],
    "illegal_construction":  ["troop_movement", "unauthorized_aircraft"],
    "unauthorized_aircraft": ["illegal_construction", "weapons_cache"],
    "civilian_activity":     [],
}

DECEPTION_TYPES = {
    "civilian_military":         "Military assets disguised as civilian infrastructure",
    "commercial_weapons":        "Weapons development hidden inside commercial facilities",
    "construction_fortification":"Military fortification disguised as construction",
    "logistics_supply":          "Military supply chain disguised as commercial logistics",
    "research_weapons":          "Weapons research disguised as civilian research facility",
}

# Safe score constants — never 0.0 or 1.0
SCORE_HIGH   = 0.95
SCORE_MED    = 0.55
SCORE_LOW    = 0.25
SCORE_MIN    = 0.03


def grade_task1(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold       = case.get("gold_action")
    difficulty = case.get("difficulty", "easy")

    if action.action == gold:
        action_score = SCORE_HIGH
    else:
        action_score = {"easy": SCORE_MIN, "medium": 0.20, "hard": 0.35}.get(difficulty, SCORE_MIN)

    final = _clamp(action_score)
    return GeoReward(
        score=final,
        feedback=f"{'Correct' if action.action == gold else 'Incorrect'}! "
                 f"Expected '{gold}', got '{action.action}'. ({difficulty} case)",
        breakdown={"action_score": _clamp(action_score), "final_score": final},
    )


def grade_task2(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action     = case.get("gold_action")
    gold_level      = case.get("gold_threat_level", 5)
    predicted_level = action.threat_level or 5

    if action.action == gold_action:
        class_score = SCORE_HIGH
    elif action.action in RELATED_THREATS.get(gold_action, []):
        class_score = 0.45
    else:
        class_score = SCORE_MIN

    diff = abs(predicted_level - gold_level)
    if diff == 0:   level_score = SCORE_HIGH
    elif diff == 1: level_score = 0.80
    elif diff == 2: level_score = 0.60
    elif diff == 3: level_score = 0.40
    else:           level_score = 0.12

    final = _clamp(0.5 * class_score + 0.5 * level_score)
    return GeoReward(
        score=final,
        feedback=(
            f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} "
            f"(expected '{gold_action}'). Level: {predicted_level} vs {gold_level} (diff={diff})."
        ),
        breakdown={
            "classification_score": _clamp(class_score),
            "threat_level_score":   _clamp(level_score),
            "final_score":          final,
        },
    )


def grade_task3(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action")
    second_best = case.get("second_best_sector", "")

    if action.action.startswith("investigate_"):
        sector      = action.action.replace("investigate_", "")
        gold_sector = gold_action.replace("deploy_to_", "")
        if sector == gold_sector:
            s = _clamp(0.55)
            return GeoReward(
                score=s,
                feedback=f"Good — investigating right sector ({sector}).",
                breakdown={"investigate_score": s, "final_score": s},
            )
        s = _clamp(0.25)
        return GeoReward(
            score=s,
            feedback=f"Investigating {sector} — not highest priority.",
            breakdown={"investigate_score": s, "final_score": s},
        )

    if action.action == gold_action:
        sector_score = SCORE_HIGH
    elif action.action == second_best:
        sector_score = SCORE_MED
    else:
        sector_score = SCORE_MIN

    reasoning       = action.reasoning or ""
    reasoning_score = 0.12
    if len(reasoning) > 20:  reasoning_score += 0.10
    if len(reasoning) > 80:  reasoning_score += 0.10
    if len(reasoning) > 150: reasoning_score += 0.10

    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if kw.lower() in reasoning.lower())
    if keyword_hits >= 3: reasoning_score += 0.10
    if keyword_hits >= 5: reasoning_score += 0.10
    if keyword_hits >= 8: reasoning_score += 0.10
    reasoning_score = min(reasoning_score, SCORE_HIGH)

    final = _clamp(0.5 * sector_score + 0.5 * reasoning_score)
    return GeoReward(
        score=final,
        feedback=(
            f"Sector: {'correct' if sector_score > 0.5 else 'incorrect'} "
            f"(expected '{gold_action}'). Reasoning: {len(reasoning)} chars, {keyword_hits} keywords."
        ),
        breakdown={
            "sector_score":    _clamp(sector_score),
            "reasoning_score": _clamp(reasoning_score),
            "final_score":     final,
        },
    )


def grade_task4(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action    = case.get("gold_action")
    gold_cover     = case.get("gold_cover_story", "")
    gold_deception = case.get("gold_deception_type", "")
    is_legit_case  = (gold_action == "legitimate_activity")

    if action.action == gold_action:
        class_score = SCORE_HIGH
    elif action.action == "request_verification" and gold_action == "covert_operation":
        class_score = 0.50
    else:
        class_score = SCORE_MIN

    if is_legit_case:
        cover_score     = SCORE_HIGH if action.action == "legitimate_activity" else SCORE_MIN
        deception_score = SCORE_HIGH if action.action == "legitimate_activity" else SCORE_MIN
        hits = 0
    else:
        identified_cover = (action.cover_story_identified or "").lower()
        cover_keywords   = gold_cover.lower().split()
        hits = sum(1 for kw in cover_keywords if len(kw) > 4 and kw in identified_cover)
        if hits >= 3:   cover_score = SCORE_HIGH
        elif hits >= 2: cover_score = 0.70
        elif hits >= 1: cover_score = 0.40
        else:           cover_score = SCORE_MIN

        if action.deception_type and gold_deception:
            if action.deception_type == gold_deception:
                deception_score = SCORE_HIGH
            elif action.deception_type in DECEPTION_TYPES:
                deception_score = 0.30
            else:
                deception_score = SCORE_MIN
        else:
            deception_score = SCORE_MIN

    reasoning       = action.reasoning or ""
    reasoning_score = 0.12
    if len(reasoning) > 50:  reasoning_score += 0.10
    if len(reasoning) > 150: reasoning_score += 0.15
    if len(reasoning) > 300: reasoning_score += 0.15
    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if kw.lower() in reasoning.lower())
    if keyword_hits >= 5: reasoning_score += 0.10
    if keyword_hits >= 8: reasoning_score += 0.15
    reasoning_score = min(reasoning_score, SCORE_HIGH)

    final = _clamp(
        0.40 * class_score
        + 0.25 * cover_score
        + 0.15 * deception_score
        + 0.20 * reasoning_score
    )

    class_label     = "correct" if class_score > 0.5 else "incorrect"
    deception_label = "correct" if deception_score > 0.5 else "incorrect"
    cover_detail    = (
        "Legitimate case — no cover story expected."
        if is_legit_case
        else f"Cover: {hits} hits. Deception: {deception_label}."
    )

    return GeoReward(
        score=final,
        feedback=(
            f"Classification: {class_label} "
            f"(expected '{gold_action}'). "
            f"{cover_detail} "
            f"Reasoning: {len(reasoning)} chars."
        ),
        breakdown={
            "classification_score": _clamp(class_score),
            "cover_story_score":    _clamp(cover_score),
            "deception_type_score": _clamp(deception_score),
            "reasoning_score":      _clamp(reasoning_score),
            "final_score":          final,
        },
    )


GRADERS = {
    1: grade_task1,
    2: grade_task2,
    3: grade_task3,
    4: grade_task4,
}
