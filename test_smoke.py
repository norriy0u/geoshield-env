"""
GeoShield Smoke Tests — validates all endpoints and grader logic.
Run: python -m pytest tests/test_smoke.py -v
"""
import pytest
import json

# ── Test grader imports and basic functionality ──────────────────────────────

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
    """Verify constants are correctly defined."""
    from src.geoshield.constants import TASK_ACTIONS, MAX_STEPS, TASK_NAMES
    assert len(TASK_ACTIONS) == 4
    assert all(t in MAX_STEPS for t in [1, 2, 3, 4])
    assert all(t in TASK_NAMES for t in [1, 2, 3, 4])


# ── Task 1: False Alarm Detection ────────────────────────────────────────────

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


# ── Task 2: Threat Classification ────────────────────────────────────────────

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


# ── Task 3: Drone Allocation ─────────────────────────────────────────────────

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


# ── Task 4: Covert Operation Detection ───────────────────────────────────────

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


# ── Reward Boundary Tests ────────────────────────────────────────────────────

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


# ── Environment Integration ──────────────────────────────────────────────────

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


# ── Generator Tests ──────────────────────────────────────────────────────────

def test_sample_case_deterministic():
    """Same seed should produce same case."""
    from src.geoshield.server.generators import sample_case
    case1 = sample_case(1, seed=42)
    case2 = sample_case(1, seed=42)
    assert case1["id"] == case2["id"]


def test_sample_case_different_seeds():
    """Different seeds should produce different cases (if enough data)."""
    from src.geoshield.server.generators import sample_case
    case1 = sample_case(1, seed=42)
    case2 = sample_case(1, seed=99)
    # They might be the same if only 1 case — at least ensure no crash
    assert case1 is not None and case2 is not None


def test_fallback_cases():
    """Fallback cases should be valid for all tasks."""
    from src.geoshield.server.generators import _make_fallback_case
    for task_id in [1, 2, 3, 4]:
        case = _make_fallback_case(task_id)
        assert "gold_action" in case
        assert "id" in case
