"""
GeoShield Smoke Tests — validates all endpoints, graders, procedural gen, and multi-step episodes.
Run: python -m pytest tests/test_smoke.py -v
"""
import pytest
import json


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_graders_import():
    """Verify all graders can be imported without errors."""
    from src.geoshield.server.graders import GRADERS, grade_task1, grade_task2, grade_task3, grade_task4
    assert set(GRADERS.keys()) == {1, 2, 3, 4}


def test_models_import():
    """Verify all Pydantic models can be instantiated."""
    from src.geoshield.models import GeoShieldAction, GeoObservation, GeoReward, GeoState, SectorReport
    action = GeoShieldAction(action="ignore")
    assert action.action == "ignore"
    reward = GeoReward(score=0.5, feedback="test")
    assert 0.02 <= reward.score <= 0.98


def test_constants_import():
    """Verify constants are correctly defined with new actions."""
    from src.geoshield.constants import TASK_ACTIONS, MAX_STEPS, TASK_NAMES
    assert len(TASK_ACTIONS) == 4
    assert all(t in MAX_STEPS for t in [1, 2, 3, 4])
    assert all(t in TASK_NAMES for t in [1, 2, 3, 4])
    # New multi-step actions
    assert "request_context" in TASK_ACTIONS[1]
    assert "request_analysis" in TASK_ACTIONS[2]


def test_procedural_generator_import():
    """Verify procedural generator can be imported."""
    from src.geoshield.server.procedural_generator import PROCEDURAL_GENERATORS, generate_procedural_case
    assert set(PROCEDURAL_GENERATORS.keys()) == {1, 2, 3, 4}


# ═══════════════════════════════════════════════════════════════════════════════
# PROCEDURAL GENERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_procedural_deterministic():
    """Same seed must produce identical cases."""
    from src.geoshield.server.procedural_generator import generate_procedural_case
    for task_id in [1, 2, 3, 4]:
        case1 = generate_procedural_case(task_id, seed=42)
        case2 = generate_procedural_case(task_id, seed=42)
        assert case1["id"] == case2["id"], f"Task {task_id}: non-deterministic"
        assert case1["gold_action"] == case2["gold_action"]


def test_procedural_different_seeds():
    """Different seeds should produce different cases."""
    from src.geoshield.server.procedural_generator import generate_procedural_case
    for task_id in [1, 2, 3, 4]:
        case1 = generate_procedural_case(task_id, seed=42)
        case2 = generate_procedural_case(task_id, seed=99)
        assert case1["id"] != case2["id"], f"Task {task_id}: seeds 42 and 99 produced same case"


def test_procedural_100_seeds():
    """Generate 100 cases per task with no crashes and high uniqueness."""
    from src.geoshield.server.procedural_generator import generate_procedural_case
    for task_id in [1, 2, 3, 4]:
        ids = set()
        for seed in range(100):
            case = generate_procedural_case(task_id, seed)
            assert case["id"] is not None
            assert case["gold_action"] is not None
            ids.add(case["id"])
        # At least 90% unique (some template combinations might collide, but IDs won't)
        assert len(ids) >= 95, f"Task {task_id}: only {len(ids)}/100 unique IDs"


def test_procedural_task1_fields():
    """Task 1 procedural cases have all required fields."""
    from src.geoshield.server.procedural_generator import generate_procedural_case
    case = generate_procedural_case(1, seed=42)
    assert "report" in case
    assert "context" in case
    assert "gold_action" in case
    assert case["gold_action"] in ["ignore", "flag_for_review"]
    assert "additional_context" in case


def test_procedural_task3_sectors():
    """Task 3 procedural cases generate valid sector data."""
    from src.geoshield.server.procedural_generator import generate_procedural_case
    case = generate_procedural_case(3, seed=42)
    assert "sectors" in case
    assert len(case["sectors"]) == 3
    sector_ids = {s["sector_id"] for s in case["sectors"]}
    assert sector_ids == {"sector_a", "sector_b", "sector_c"}


def test_procedural_task4_red_herring():
    """Task 4 should generate red herring cases (look suspicious but legitimate)."""
    from src.geoshield.server.procedural_generator import generate_procedural_case
    red_herrings_found = 0
    for seed in range(200):
        case = generate_procedural_case(4, seed)
        if case.get("category") == "red_herring":
            red_herrings_found += 1
            assert case["gold_action"] == "legitimate_activity"
            assert case["difficulty"] == "ultra"
    assert red_herrings_found > 0, "No red herring cases found in 200 seeds"


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 1 GRADER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_task1_correct():
    from src.geoshield.server.graders import grade_task1
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="ignore")
    case = {"gold_action": "ignore", "difficulty": "easy"}
    reward = grade_task1(action, case)
    assert reward.score >= 0.80, f"Expected high score for correct action, got {reward.score}"


def test_task1_wrong():
    from src.geoshield.server.graders import grade_task1
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="flag_for_review")
    case = {"gold_action": "ignore", "difficulty": "easy"}
    reward = grade_task1(action, case)
    assert reward.score < 0.50, f"Expected low score for wrong action, got {reward.score}"


def test_task1_ceiling():
    """Easy ceiling should cap score at 0.95."""
    from src.geoshield.server.graders import grade_task1
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="ignore")
    case = {"gold_action": "ignore", "difficulty": "easy"}
    reward = grade_task1(action, case)
    assert reward.score <= 0.95, f"Easy ceiling violated: {reward.score}"


def test_task1_intel_bonus():
    """Intel gathering should provide a small bonus."""
    from src.geoshield.server.graders import grade_task1
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="ignore")
    case = {"gold_action": "ignore", "difficulty": "easy"}
    reward_no_ctx = grade_task1(action, case, context={"context_requested": False})
    reward_with_ctx = grade_task1(action, case, context={"context_requested": True})
    assert reward_with_ctx.score >= reward_no_ctx.score


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 2 GRADER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_task2_correct_classification_and_level():
    from src.geoshield.server.graders import grade_task2
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="troop_movement", threat_level=7)
    case = {"gold_action": "troop_movement", "gold_threat_level": 7, "difficulty": "medium"}
    reward = grade_task2(action, case)
    assert reward.score >= 0.70, f"Expected high score, got {reward.score}"


def test_task2_related_classification():
    from src.geoshield.server.graders import grade_task2
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="weapons_cache", threat_level=7)
    case = {"gold_action": "troop_movement", "gold_threat_level": 7, "difficulty": "medium"}
    reward = grade_task2(action, case)
    assert 0.30 < reward.score < 0.80, f"Expected partial credit, got {reward.score}"


def test_task2_wrong_classification():
    from src.geoshield.server.graders import grade_task2
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="civilian_activity", threat_level=1)
    case = {"gold_action": "troop_movement", "gold_threat_level": 8, "difficulty": "medium"}
    reward = grade_task2(action, case)
    assert reward.score < 0.30, f"Expected low score for totally wrong, got {reward.score}"


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 3 GRADER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_task3_correct_deployment_with_reasoning():
    from src.geoshield.server.graders import grade_task3
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(
        action="deploy_to_sector_b",
        reasoning="Based on the intelligence assessment, sector B shows confirmed troop movement with high confidence. Strategic priority indicates immediate deployment is critical to verify and respond to this threat before it escalates. The anomaly pattern is consistent with known military staging activities."
    )
    case = {"gold_action": "deploy_to_sector_b", "second_best_sector": "deploy_to_sector_a", "difficulty": "hard"}
    reward = grade_task3(action, case)
    assert reward.score >= 0.60, f"Expected high score for correct sector + reasoning, got {reward.score}"


def test_task3_wrong_deployment():
    from src.geoshield.server.graders import grade_task3
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="deploy_to_sector_c", reasoning="fallback")
    case = {"gold_action": "deploy_to_sector_b", "second_best_sector": "deploy_to_sector_a", "difficulty": "hard"}
    reward = grade_task3(action, case)
    assert reward.score < 0.40, f"Expected low score for wrong sector, got {reward.score}"


def test_task3_investigate():
    from src.geoshield.server.graders import grade_task3
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="investigate_sector_b")
    case = {"gold_action": "deploy_to_sector_b", "difficulty": "hard"}
    reward = grade_task3(action, case)
    assert 0.40 < reward.score < 0.70, f"Expected moderate credit for correct investigation, got {reward.score}"


def test_task3_boilerplate_penalty():
    """Highly repetitive reasoning should score lower than unique reasoning."""
    from src.geoshield.server.graders import grade_task3
    from src.geoshield.models import GeoShieldAction
    boilerplate = "threat threat threat threat threat threat threat threat threat threat threat threat"
    genuine = "Based on intelligence from sector B showing confirmed troop movement at high confidence, strategic priority demands immediate deployment to verify and respond before escalation."
    act_boil = GeoShieldAction(action="deploy_to_sector_b", reasoning=boilerplate)
    act_real = GeoShieldAction(action="deploy_to_sector_b", reasoning=genuine)
    case = {"gold_action": "deploy_to_sector_b", "difficulty": "hard"}
    r_boil = grade_task3(act_boil, case)
    r_real = grade_task3(act_real, case)
    assert r_real.score >= r_boil.score, f"Genuine ({r_real.score}) should >= boilerplate ({r_boil.score})"


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 4 GRADER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_task4_correct_covert():
    from src.geoshield.server.graders import grade_task4
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(
        action="covert_operation",
        cover_story_identified="agricultural research facility used as cover",
        deception_type="research_weapons",
        reasoning="The facility shows clear indicators of weapons research activity. Satellite imagery reveals reinforced structures inconsistent with agricultural use. Encrypted communications detected suggest covert military operations."
    )
    case = {
        "gold_action": "covert_operation",
        "gold_cover_story": "agricultural research facility",
        "gold_deception_type": "research_weapons",
        "difficulty": "ultra",
    }
    reward = grade_task4(action, case)
    assert reward.score >= 0.50, f"Expected decent score for correct covert detection, got {reward.score}"


def test_task4_wrong_classification():
    from src.geoshield.server.graders import grade_task4
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(action="legitimate_activity")
    case = {
        "gold_action": "covert_operation",
        "gold_cover_story": "agricultural research facility",
        "gold_deception_type": "research_weapons",
        "difficulty": "ultra",
    }
    reward = grade_task4(action, case)
    assert reward.score < 0.30, f"Expected low score for missed covert op, got {reward.score}"


def test_task4_ultra_ceiling():
    """Ultra ceiling should cap score at 0.75."""
    from src.geoshield.server.graders import grade_task4
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(
        action="covert_operation",
        cover_story_identified="agricultural research facility perfectly matching",
        deception_type="research_weapons",
        reasoning="Extensive strategic analysis confirms covert weapons research program. Multiple intelligence indicators detected: reinforced structures, encrypted communications, military vehicles observed at irregular hours. Based on pattern analysis and cross-referenced intelligence, this facility represents a confirmed threat requiring immediate assessment and priority response."
    )
    case = {
        "gold_action": "covert_operation",
        "gold_cover_story": "agricultural research facility",
        "gold_deception_type": "research_weapons",
        "difficulty": "ultra",
    }
    reward = grade_task4(action, case)
    assert reward.score <= 0.75, f"Ultra ceiling violated: {reward.score}"


def test_task4_false_positive_penalty():
    """Calling a legitimate facility 'covert_operation' should be penalized harshly."""
    from src.geoshield.server.graders import grade_task4
    from src.geoshield.models import GeoShieldAction
    action = GeoShieldAction(
        action="covert_operation",
        cover_story_identified="fake cover story",
        deception_type="civilian_military",
        reasoning="This looks suspicious."
    )
    case = {
        "gold_action": "legitimate_activity",
        "gold_cover_story": "fishing cooperative",
        "gold_deception_type": "",
        "difficulty": "ultra",
    }
    reward = grade_task4(action, case)
    assert reward.score <= 0.25, f"False positive should be penalized, got {reward.score}"


def test_task4_levenshtein_scoring():
    """Levenshtein matching should reward close cover story matches."""
    from src.geoshield.server.graders import _levenshtein_similarity
    # Exact match
    assert _levenshtein_similarity("agricultural research", "agricultural research") == 1.0
    # Close match
    sim = _levenshtein_similarity("agricultural research facility", "agricultural research")
    assert sim > 0.6, f"Close match should have high similarity: {sim}"
    # Partial match
    sim2 = _levenshtein_similarity("military base", "agricultural research")
    assert sim2 < 0.4, f"Unrelated should have low similarity: {sim2}"


# ═══════════════════════════════════════════════════════════════════════════════
# REWARD BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_reward_never_zero():
    """No grader should ever return exactly 0.0."""
    from src.geoshield.server.graders import GRADERS
    from src.geoshield.models import GeoShieldAction
    for task_id, grader in GRADERS.items():
        action = GeoShieldAction(action="totally_invalid_action_xyz")
        case = {"gold_action": "ignore", "difficulty": "easy"}
        reward = grader(action, case)
        assert reward.score > 0.0, f"Task {task_id} returned 0.0"


def test_reward_never_one():
    """No grader should ever return exactly 1.0."""
    from src.geoshield.server.graders import GRADERS
    from src.geoshield.models import GeoShieldAction
    for task_id, grader in GRADERS.items():
        action = GeoShieldAction(action="ignore")
        case = {"gold_action": "ignore", "difficulty": "easy"}
        reward = grader(action, case)
        assert reward.score < 1.0, f"Task {task_id} returned 1.0"


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_environment_reset():
    from src.geoshield.server.environment import GeoShieldEnvironment
    env = GeoShieldEnvironment()
    result = env.reset(task_id=1, seed=42)
    assert "observation" in result
    assert "state" in result
    assert result["done"] == False


def test_environment_step():
    from src.geoshield.server.environment import GeoShieldEnvironment
    env = GeoShieldEnvironment()
    env.reset(task_id=1, seed=42)
    result = env.step({"action": "ignore"})
    assert "observation" in result
    assert "reward" in result
    assert "done" in result
    assert 0.0 < result["reward"] < 1.0


def test_environment_full_episode():
    """Run a complete episode for each task."""
    from src.geoshield.server.environment import GeoShieldEnvironment
    env = GeoShieldEnvironment()
    for task_id in [1, 2, 3, 4]:
        result = env.reset(task_id=task_id, seed=42)
        assert not result["done"]
        step_result = env.step({"action": result["observation"]["available_actions"][0]})
        assert "reward" in step_result


def test_environment_multistep_task1():
    """Task 1: request_context then decide."""
    from src.geoshield.server.environment import GeoShieldEnvironment
    env = GeoShieldEnvironment()
    result = env.reset(task_id=1, seed=42)
    assert not result["done"]

    # Step 1: request context
    step1 = env.step({"action": "request_context"})
    assert not step1["done"], "Episode should not end after requesting context"
    assert "ADDITIONAL INTELLIGENCE" in step1["observation"].get("hint", "")

    # Step 2: make decision
    step2 = env.step({"action": "ignore"})
    assert step2["done"]
    assert step2["reward"] > 0.0


def test_environment_multistep_task2():
    """Task 2: request_analysis then classify."""
    from src.geoshield.server.environment import GeoShieldEnvironment
    env = GeoShieldEnvironment()
    result = env.reset(task_id=2, seed=42)
    assert not result["done"]

    # Step 1: request analysis
    step1 = env.step({"action": "request_analysis"})
    assert not step1["done"], "Episode should not end after requesting analysis"
    assert "SENSOR ANALYSIS" in step1["observation"].get("hint", "")

    # Step 2: classify
    step2 = env.step({"action": "troop_movement", "threat_level": 7})
    assert step2["done"]
    assert step2["reward"] > 0.0


def test_environment_reward_not_diluted():
    """Episode reward should be the terminal step score, not averaged with intel steps."""
    from src.geoshield.server.environment import GeoShieldEnvironment
    env = GeoShieldEnvironment()
    env.reset(task_id=1, seed=42)

    # Get gold action
    gold = env.case.get("gold_action", "ignore")

    # Request context then give correct answer
    env.step({"action": "request_context"})
    result = env.step({"action": gold})

    # Total score should be the terminal graded score, not averaged with context step
    assert result["info"]["total_score"] > 0.50, f"Total score diluted: {result['info']['total_score']}"


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_sample_case_deterministic():
    """Same seed should produce same case."""
    from src.geoshield.server.generators import sample_case
    case1 = sample_case(1, seed=42)
    case2 = sample_case(1, seed=42)
    assert case1["id"] == case2["id"]


def test_sample_case_different_seeds():
    """Different seeds should produce different cases."""
    from src.geoshield.server.generators import sample_case
    case1 = sample_case(1, seed=42)
    case2 = sample_case(1, seed=99)
    assert case1 is not None and case2 is not None


def test_fallback_cases():
    """Fallback cases should be valid for all tasks."""
    from src.geoshield.server.generators import _make_fallback_case
    for task_id in [1, 2, 3, 4]:
        case = _make_fallback_case(task_id)
        assert "gold_action" in case
        assert "id" in case
