"""
GeoShield Graders — Deterministic heuristic graders for Tasks 1–4.

All scoring is done via proximity matrices, keyword heuristics, and
structural analysis. Zero-LLM — fully reproducible and auditable.

Design Philosophy:
  • Score ceilings per difficulty ensure genuine progression
  • Negation filtering prevents trivial keyword gaming
  • Positional/structural checks on reasoning (Task 3, 4) reward depth
  • Rewards clamped strictly to (0.02, 0.98) for OpenEnv compliance
"""
from typing import Dict, Any
from src.geoshield.models import GeoShieldAction, GeoReward
from src.geoshield.constants import STRATEGIC_KEYWORDS


def _clamp(score: float) -> float:
    """Clamp score to (0.02, 0.98) — never hitting exact boundaries."""
    try:
        return round(max(0.02, min(0.98, float(score))), 4)
    except Exception:
        return 0.02


# ── Score Ceilings ─────────────────────────────────────────────────────────────
# Each difficulty tier has a max achievable score, ensuring easy < medium < hard.
# Inspired by best-practice OpenEnv designs that prevent artificial score inflation.
SCORE_CEILINGS = {
    "easy": 0.95,
    "medium": 0.85,
    "hard": 0.80,
    "ultra": 0.75,
}


def _apply_ceiling(score: float, difficulty: str) -> float:
    """Cap the score at the difficulty-tier ceiling."""
    ceiling = SCORE_CEILINGS.get(difficulty, 0.98)
    return min(score, ceiling)


# ── Negation Filter ────────────────────────────────────────────────────────────
NEGATION_PREFIXES = [
    "not ", "no ", "isn't ", "aren't ", "wasn't ", "weren't ",
    "don't ", "doesn't ", "didn't ", "cannot ", "can't ",
    "neither ", "without ",
]


def _keyword_hit(keyword: str, text: str) -> bool:
    """Check keyword presence while filtering out negated mentions."""
    text_lower = text.lower()
    if keyword.lower() not in text_lower:
        return False
    # Check for negation within 30 chars before the keyword
    idx = text_lower.find(keyword.lower())
    prefix = text_lower[max(0, idx - 30):idx]
    for neg in NEGATION_PREFIXES:
        if neg in prefix:
            return False
    return True


# ── Related Threat Categories ──────────────────────────────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 1 — False Alarm Detection (Easy)
# ═══════════════════════════════════════════════════════════════════════════════

TASK1_PROXIMITY = {
    "ignore":          {"ignore": 0.98, "flag_for_review": 0.20},
    "flag_for_review":  {"flag_for_review": 0.98, "ignore": 0.15},
}


def grade_task1(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold = case.get("gold_action", "ignore")
    agent = action.action.strip().lower()
    difficulty = case.get("difficulty", "easy")

    proximity = TASK1_PROXIMITY.get(gold, {})
    score = proximity.get(agent, 0.02)

    # Difficulty modifier: medium/hard false alarm cases give partial credit
    # for cautious over-flagging (flag_for_review when gold=ignore)
    if difficulty == "medium" and agent == "flag_for_review" and gold == "ignore":
        score = max(score, 0.35)  # Cautious is better than reckless
    if difficulty == "hard" and agent == "flag_for_review" and gold == "ignore":
        score = max(score, 0.40)

    score = _apply_ceiling(score, difficulty)

    if score >= 0.9:
        feedback = f"Correct. Gold: {gold}."
    elif score >= 0.3:
        feedback = f"Partial credit ({score:.2f}). You chose '{agent}', gold was '{gold}'."
    else:
        feedback = f"Incorrect. You chose '{agent}', gold was '{gold}'."

    return GeoReward(
        score=_clamp(score),
        feedback=feedback,
        breakdown={
            "gold_action": gold,
            "agent_action": agent,
            "difficulty": difficulty,
            "score": _clamp(score),
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Threat Classification & Severity (Medium)
# ═══════════════════════════════════════════════════════════════════════════════

def grade_task2(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action", "civilian_activity")
    gold_level = int(case.get("gold_threat_level", 5))
    predicted_level = action.threat_level or 5
    difficulty = case.get("difficulty", "medium")

    # Classification scoring
    agent = action.action.strip().lower()
    if agent == gold_action:
        class_score = 0.98
    elif agent in RELATED_THREATS.get(gold_action, []):
        class_score = 0.45
    else:
        class_score = 0.02

    # Threat level proximity scoring
    diff = abs(predicted_level - gold_level)
    if diff == 0:
        level_score = 0.98
    elif diff == 1:
        level_score = 0.80
    elif diff == 2:
        level_score = 0.60
    elif diff == 3:
        level_score = 0.40
    else:
        level_score = 0.10

    final = 0.5 * class_score + 0.5 * level_score

    # If classification is totally wrong, cap total score
    if class_score < 0.10:
        final = min(final, 0.30)

    final = _apply_ceiling(final, difficulty)

    return GeoReward(
        score=_clamp(final),
        feedback=f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Level: {predicted_level} vs {gold_level} (diff={diff}).",
        breakdown={
            "classification_score": round(class_score, 4),
            "threat_level_score": round(level_score, 4),
            "difficulty": difficulty,
            "final_score": _clamp(final),
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 3 — Multi-Zone Drone Allocation (Hard)
# ═══════════════════════════════════════════════════════════════════════════════

def _score_reasoning(reasoning: str) -> float:
    """Score the quality of strategic reasoning with negation filtering."""
    if not reasoning:
        return 0.05

    score = 0.05
    r = reasoning.strip()

    # Length bonuses
    if len(r) > 20:
        score += 0.10
    if len(r) > 80:
        score += 0.10
    if len(r) > 150:
        score += 0.10

    # Strategic keyword hits (with negation filtering)
    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if _keyword_hit(kw, r))
    if keyword_hits >= 3:
        score += 0.10
    if keyword_hits >= 5:
        score += 0.10
    if keyword_hits >= 8:
        score += 0.10

    # Structural bonus: does the reasoning have multiple sentences?
    sentences = [s.strip() for s in r.replace("!", ".").replace("?", ".").split(".") if len(s.strip()) > 10]
    if len(sentences) >= 3:
        score += 0.05
    if len(sentences) >= 5:
        score += 0.05

    # Causal language bonus (demonstrates genuine analysis)
    causal_terms = ["because", "due to", "therefore", "indicates", "confirms",
                    "based on", "given that", "as a result", "suggesting"]
    causal_hits = sum(1 for term in causal_terms if _keyword_hit(term, r))
    if causal_hits >= 2:
        score += 0.10

    return min(score, 0.98)


def grade_task3(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action", "deploy_to_sector_a")
    second_best = case.get("second_best_sector", "")
    difficulty = case.get("difficulty", "hard")

    # Investigation actions get partial credit
    if action.action.startswith("investigate_"):
        sector = action.action.replace("investigate_", "")
        gold_sector = gold_action.replace("deploy_to_", "")
        if sector == gold_sector:
            score = 0.55
            feedback = f"Good — investigating the right sector ({sector})."
        else:
            score = 0.20
            feedback = f"Investigating {sector} — not highest priority."
        return GeoReward(
            score=_clamp(score),
            feedback=feedback,
            breakdown={"investigate_score": round(score, 4)}
        )

    # Deployment grading
    agent = action.action.strip().lower()
    if agent == gold_action:
        sector_score = 0.98
    elif agent == second_best:
        sector_score = 0.50
    else:
        sector_score = 0.02

    reasoning_score = _score_reasoning(action.reasoning or "")

    final = 0.5 * sector_score + 0.5 * reasoning_score

    # If sector is totally wrong, cap regardless of reasoning quality
    if sector_score < 0.10:
        final = min(final, 0.40)

    # Minimum response length for full credit
    reasoning_len = len((action.reasoning or "").strip())
    if reasoning_len < 20:
        final = min(final, 0.35)

    final = _apply_ceiling(final, difficulty)

    return GeoReward(
        score=_clamp(final),
        feedback=f"Sector: {'correct' if sector_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Reasoning: {reasoning_len} chars, quality={reasoning_score:.2f}.",
        breakdown={
            "sector_score": round(sector_score, 4),
            "reasoning_score": round(reasoning_score, 4),
            "difficulty": difficulty,
            "final_score": _clamp(final),
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 4 — Covert Operation Detection (Ultra)
# ═══════════════════════════════════════════════════════════════════════════════

def grade_task4(action: GeoShieldAction, case: Dict[str, Any]) -> GeoReward:
    gold_action = case.get("gold_action", "legitimate_activity")
    gold_cover = case.get("gold_cover_story", "")
    gold_deception = case.get("gold_deception_type", "")
    difficulty = case.get("difficulty", "ultra")

    # ── Classification (40%) ──────────────────────────────────────────────
    agent = action.action.strip().lower()
    if agent == gold_action:
        class_score = 0.98
    elif agent == "request_verification" and gold_action == "covert_operation":
        class_score = 0.50  # Cautious — partial credit
    elif agent == "request_verification" and gold_action == "legitimate_activity":
        class_score = 0.30  # Unnecessary caution — less credit
    else:
        class_score = 0.02

    # ── Cover Story Identification (25%) ──────────────────────────────────
    identified_cover = (action.cover_story_identified or "").lower()
    cover_keywords = [kw for kw in gold_cover.lower().split() if len(kw) > 4]

    # Use negation-aware matching
    hits = sum(1 for kw in cover_keywords if _keyword_hit(kw, identified_cover))
    if hits >= 3:
        cover_score = 0.98
    elif hits >= 2:
        cover_score = 0.70
    elif hits >= 1:
        cover_score = 0.40
    else:
        cover_score = 0.02

    # For legitimate facilities, cover story N/A — give baseline score
    if gold_action == "legitimate_activity":
        if not identified_cover or identified_cover in ["", "none", "n/a"]:
            cover_score = 0.80  # Correctly not identifying a cover story

    # ── Deception Type (15%) ──────────────────────────────────────────────
    deception_score = 0.02
    if action.deception_type and gold_deception:
        if action.deception_type == gold_deception:
            deception_score = 0.98
        elif action.deception_type in DECEPTION_TYPES:
            deception_score = 0.30  # Valid type but wrong one

    # For legitimate facilities, deception type N/A
    if gold_action == "legitimate_activity":
        if not action.deception_type or action.deception_type in ["", "none"]:
            deception_score = 0.80

    # ── Reasoning (20%) ───────────────────────────────────────────────────
    reasoning_score = _score_reasoning(action.reasoning or "")

    # ── Final composite ───────────────────────────────────────────────────
    final = (0.40 * class_score +
             0.25 * cover_score +
             0.15 * deception_score +
             0.20 * reasoning_score)

    # If classification is totally wrong, cap hard
    if class_score < 0.10:
        final = min(final, 0.30)

    # Minimum reasoning length for ultra tier
    reasoning_len = len((action.reasoning or "").strip())
    if reasoning_len < 30:
        final = min(final, 0.40)

    final = _apply_ceiling(final, difficulty)

    return GeoReward(
        score=_clamp(final),
        feedback=f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Cover: {hits} hits. Deception: {'correct' if deception_score > 0.5 else 'incorrect'}. Reasoning: {reasoning_len} chars.",
        breakdown={
            "classification_score": round(class_score, 4),
            "cover_story_score": round(cover_score, 4),
            "deception_type_score": round(deception_score, 4),
            "reasoning_score": round(reasoning_score, 4),
            "difficulty": difficulty,
            "final_score": _clamp(final),
        }
    )


GRADERS = {
    1: grade_task1,
    2: grade_task2,
    3: grade_task3,
    4: grade_task4,
}
