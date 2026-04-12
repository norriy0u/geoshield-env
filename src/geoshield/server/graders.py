"""
GeoShield Graders — Deterministic heuristic graders for Tasks 1–4.

All scoring is done via proximity matrices, keyword heuristics, structural
analysis, and Levenshtein similarity. Zero-LLM — fully reproducible.

Design Philosophy:
  • Score ceilings per difficulty ensure genuine progression
  • Negation filtering prevents trivial keyword gaming
  • Report-reference scoring rewards specificity over boilerplate
  • Levenshtein distance for cover story matching (Task 4)
  • Intel-gathering bonuses reward multi-step decision making
  • Rewards clamped strictly to (0.02, 0.98) for OpenEnv compliance
"""
from typing import Dict, Any, Optional
from src.geoshield.models import GeoShieldAction, GeoReward
from src.geoshield.constants import STRATEGIC_KEYWORDS


def _clamp(score: float) -> float:
    """Clamp score to (0.02, 0.98) — never hitting exact boundaries."""
    try:
        return round(max(0.02, min(0.98, float(score))), 4)
    except Exception:
        return 0.02


# ── Score Ceilings ─────────────────────────────────────────────────────────────
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
    "neither ", "without ", "lacks ", "absence of ",
]


def _keyword_hit(keyword: str, text: str) -> bool:
    """Check keyword presence while filtering out negated mentions."""
    text_lower = text.lower()
    if keyword.lower() not in text_lower:
        return False
    idx = text_lower.find(keyword.lower())
    prefix = text_lower[max(0, idx - 30):idx]
    for neg in NEGATION_PREFIXES:
        if neg in prefix:
            return False
    return True


# ── Levenshtein Distance ──────────────────────────────────────────────────────
def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            ins = prev_row[j + 1] + 1
            dele = curr_row[j] + 1
            sub = prev_row[j] + (c1 != c2)
            curr_row.append(min(ins, dele, sub))
        prev_row = curr_row
    return prev_row[-1]


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Compute normalized Levenshtein similarity (0.0 to 1.0)."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    s1_lower = s1.lower().strip()
    s2_lower = s2.lower().strip()
    dist = _levenshtein_distance(s1_lower, s2_lower)
    max_len = max(len(s1_lower), len(s2_lower))
    return 1.0 - (dist / max_len) if max_len > 0 else 0.0


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
# REASONING SCORING (improved)
# ═══════════════════════════════════════════════════════════════════════════════

def _score_reasoning(reasoning: str, case: Optional[Dict[str, Any]] = None) -> float:
    """Score reasoning quality with report-reference and coherence checks.

    Improvements over basic keyword counting:
      1. Report-reference scoring: rewards mentioning specific case details
      2. Coherence scoring: checks for logical flow structure
      3. Diversity penalty: detects boilerplate/copy-paste
      4. Specificity bonus: specific details > generic strategic language
    """
    if not reasoning:
        return 0.05

    score = 0.05
    r = reasoning.strip()

    # ── Length bonuses ─────────────────────────────────────────────────────
    if len(r) > 20:
        score += 0.08
    if len(r) > 80:
        score += 0.08
    if len(r) > 150:
        score += 0.07

    # ── Strategic keyword hits (negation-filtered) ────────────────────────
    keyword_hits = sum(1 for kw in STRATEGIC_KEYWORDS if _keyword_hit(kw, r))
    if keyword_hits >= 3:
        score += 0.08
    if keyword_hits >= 5:
        score += 0.07
    if keyword_hits >= 8:
        score += 0.05

    # ── Structural: multiple distinct sentences ──────────────────────────
    sentences = [s.strip() for s in r.replace("!", ".").replace("?", ".").split(".") if len(s.strip()) > 10]
    if len(sentences) >= 3:
        score += 0.05
    if len(sentences) >= 5:
        score += 0.05

    # ── Causal language (demonstrates genuine analysis) ──────────────────
    causal_terms = ["because", "due to", "therefore", "indicates", "confirms",
                    "based on", "given that", "as a result", "suggesting",
                    "evidence shows", "analysis confirms", "consistent with"]
    causal_hits = sum(1 for term in causal_terms if _keyword_hit(term, r))
    if causal_hits >= 2:
        score += 0.08
    if causal_hits >= 4:
        score += 0.05

    # ── Report-reference scoring (NEW) ────────────────────────────────────
    # Reward reasoning that references specific details from the case report/observation
    if case:
        report_text = (case.get("report", "") + " " + case.get("context", "")).lower()
        report_words = set(w for w in report_text.split() if len(w) > 5)
        r_lower = r.lower()
        reference_hits = sum(1 for w in report_words if w in r_lower)
        if reference_hits >= 3:
            score += 0.05
        if reference_hits >= 6:
            score += 0.05
        if reference_hits >= 10:
            score += 0.05

        # Check for specific coordinate/sector/name references
        coords = case.get("coordinates", "")
        if coords and any(part in r for part in coords.split(",") if len(part.strip()) > 3):
            score += 0.03

    # ── Diversity penalty: detect exact phrase repetitions ────────────────
    words = r.lower().split()
    if len(words) >= 10:
        trigrams = [" ".join(words[i:i+3]) for i in range(len(words) - 2)]
        unique_ratio = len(set(trigrams)) / len(trigrams) if trigrams else 1.0
        if unique_ratio < 0.5:
            score *= 0.70  # Penalty for highly repetitive text

    return min(score, 0.98)


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 1 — False Alarm Detection (Easy)
# ═══════════════════════════════════════════════════════════════════════════════

TASK1_PROXIMITY = {
    "ignore":          {"ignore": 0.98, "flag_for_review": 0.20},
    "flag_for_review":  {"flag_for_review": 0.98, "ignore": 0.15},
}


def grade_task1(action: GeoShieldAction, case: Dict[str, Any], context: Optional[Dict] = None) -> GeoReward:
    gold = case.get("gold_action", "ignore")
    agent = action.action.strip().lower()
    difficulty = case.get("difficulty", "easy")
    ctx = context or {}

    proximity = TASK1_PROXIMITY.get(gold, {})
    score = proximity.get(agent, 0.02)

    # Difficulty modifier: medium/hard cases give partial credit for cautious flagging
    if difficulty == "medium" and agent == "flag_for_review" and gold == "ignore":
        score = max(score, 0.35)
    if difficulty == "hard" and agent == "flag_for_review" and gold == "ignore":
        score = max(score, 0.40)

    # Intel-gathering bonus: agents that request context before deciding get a bonus
    if ctx.get("context_requested") and score >= 0.80:
        score = min(score + 0.03, 0.98)

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
            "context_requested": ctx.get("context_requested", False),
            "score": _clamp(score),
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Threat Classification & Severity (Medium)
# ═══════════════════════════════════════════════════════════════════════════════

def grade_task2(action: GeoShieldAction, case: Dict[str, Any], context: Optional[Dict] = None) -> GeoReward:
    gold_action = case.get("gold_action", "civilian_activity")
    gold_level = int(case.get("gold_threat_level", 5))
    predicted_level = action.threat_level or 5
    difficulty = case.get("difficulty", "medium")
    ctx = context or {}

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

    # Intel-gathering bonus
    if ctx.get("analysis_requested") and final >= 0.60:
        final = min(final + 0.03, 0.98)

    final = _apply_ceiling(final, difficulty)

    return GeoReward(
        score=_clamp(final),
        feedback=f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Level: {predicted_level} vs {gold_level} (diff={diff}).",
        breakdown={
            "classification_score": round(class_score, 4),
            "threat_level_score": round(level_score, 4),
            "difficulty": difficulty,
            "analysis_requested": ctx.get("analysis_requested", False),
            "final_score": _clamp(final),
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 3 — Multi-Zone Drone Allocation (Hard)
# ═══════════════════════════════════════════════════════════════════════════════

def grade_task3(action: GeoShieldAction, case: Dict[str, Any], context: Optional[Dict] = None) -> GeoReward:
    gold_action = case.get("gold_action", "deploy_to_sector_a")
    second_best = case.get("second_best_sector", "")
    difficulty = case.get("difficulty", "hard")
    ctx = context or {}

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

    reasoning_score = _score_reasoning(action.reasoning or "", case)

    final = 0.5 * sector_score + 0.5 * reasoning_score

    # If sector is totally wrong, cap regardless of reasoning quality
    if sector_score < 0.10:
        final = min(final, 0.40)

    # Minimum response length for full credit
    reasoning_len = len((action.reasoning or "").strip())
    if reasoning_len < 20:
        final = min(final, 0.35)

    # Intel-gathering bonus: investigation before deployment
    if ctx.get("investigation_used") and sector_score > 0.50:
        final = min(final + 0.03, 0.98)

    final = _apply_ceiling(final, difficulty)

    return GeoReward(
        score=_clamp(final),
        feedback=f"Sector: {'correct' if sector_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Reasoning: {reasoning_len} chars, quality={reasoning_score:.2f}.",
        breakdown={
            "sector_score": round(sector_score, 4),
            "reasoning_score": round(reasoning_score, 4),
            "difficulty": difficulty,
            "investigation_used": ctx.get("investigation_used", False),
            "final_score": _clamp(final),
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 4 — Covert Operation Detection (Ultra)
# ═══════════════════════════════════════════════════════════════════════════════

def grade_task4(action: GeoShieldAction, case: Dict[str, Any], context: Optional[Dict] = None) -> GeoReward:
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

    # ── Cover Story Identification (25%) — Levenshtein + keyword hybrid ──
    identified_cover = (action.cover_story_identified or "").lower().strip()

    if gold_cover and identified_cover:
        # Primary: Levenshtein similarity
        lev_sim = _levenshtein_similarity(identified_cover, gold_cover)

        # Secondary: keyword overlap
        cover_keywords = [kw for kw in gold_cover.lower().split() if len(kw) > 4]
        hits = sum(1 for kw in cover_keywords if _keyword_hit(kw, identified_cover))
        kw_score = 0.02
        if hits >= 3:
            kw_score = 0.98
        elif hits >= 2:
            kw_score = 0.70
        elif hits >= 1:
            kw_score = 0.40

        # Weighted combination: 60% Levenshtein + 40% keyword
        cover_score = 0.6 * lev_sim + 0.4 * kw_score
    elif not gold_cover and not identified_cover:
        cover_score = 0.80  # Both empty = correct for legitimate
    elif gold_action == "legitimate_activity":
        if not identified_cover or identified_cover in ["", "none", "n/a"]:
            cover_score = 0.80
        else:
            cover_score = 0.40  # Identified a cover story when there isn't one
    else:
        cover_score = 0.02

    # ── Deception Type (15%) ──────────────────────────────────────────────
    deception_score = 0.02
    if action.deception_type and gold_deception:
        if action.deception_type == gold_deception:
            deception_score = 0.98
        elif action.deception_type in DECEPTION_TYPES:
            deception_score = 0.30  # Valid type but wrong one
    if gold_action == "legitimate_activity":
        if not action.deception_type or action.deception_type in ["", "none"]:
            deception_score = 0.80

    # ── Reasoning (20%) ───────────────────────────────────────────────────
    reasoning_score = _score_reasoning(action.reasoning or "", case)

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

    # False positive penalty: calling legitimate_activity "covert_operation"
    if gold_action == "legitimate_activity" and agent == "covert_operation":
        final = min(final, 0.25)  # Harsh penalty for false positive

    final = _apply_ceiling(final, difficulty)

    return GeoReward(
        score=_clamp(final),
        feedback=f"Classification: {'correct' if class_score > 0.5 else 'incorrect'} (expected '{gold_action}'). Cover: sim={cover_score:.2f}. Deception: {'correct' if deception_score > 0.5 else 'incorrect'}. Reasoning: {reasoning_len} chars.",
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
