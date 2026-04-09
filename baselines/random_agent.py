"""
Random Agent Baseline
Randomly selects from valid actions for each task.
Run: python baselines/random_agent.py
"""

import random
import requests
import time
from typing import List

ENV_URL = "http://localhost:7860"

TASK_ACTIONS = {
    1: ["ignore", "flag_for_review"],
    2: ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity"],
    3: ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c"],
}

TASK_NAMES = {
    1: "false_alarm_detection",
    2: "threat_classification",
    3: "drone_allocation",
}

MAX_STEPS = 8


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
    resp = requests.post(
        f"{ENV_URL}/step",
        json=action_data,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def random_action(task_id: int) -> dict:
    action = random.choice(TASK_ACTIONS[task_id])

    if task_id == 2:
        return {
            "action": action,
            "threat_level": random.randint(1, 10),
        }
    elif task_id == 3:
        sector = action.replace("deploy_to_", "")
        return {
            "action": action,
            "target_sector": sector,
            "reasoning": (
                f"Randomly selected {sector} based on uniform distribution "
                f"across all available sectors. No strategic reasoning applied. "
                f"This is a random baseline agent with no intelligence or "
                f"pattern recognition capabilities whatsoever."
            ),
        }
    return {"action": action}


def run_episode(task_id: int, seed: int) -> float:
    print(f"\n[Random Agent] Task {task_id}: {TASK_NAMES[task_id]}", flush=True)

    result = env_reset(task_id=task_id, seed=seed)
    session_id = result.get("session_id", "default")
    done = result.get("done", False)

    rewards: List[float] = []
    steps = 0

    for step in range(1, MAX_STEPS + 1):
        if done:
            break

        action_data = random_action(task_id)
        result = env_step(action_data, session_id)

        reward = float(result.get("reward", 0.0))
        done = result.get("done", False)
        info = result.get("info", {})

        rewards.append(reward)
        steps += 1

        print(
            f"  Step {step}: action={action_data['action']} "
            f"reward={reward:.3f} done={done}",
            flush=True,
        )
        print(f"  Feedback: {info.get('feedback', 'N/A')}", flush=True)

        if done:
            break

        time.sleep(0.2)

    score = sum(rewards) / len(rewards) if rewards else 0.0
    print(f"[Random Agent] Task {task_id} score: {score:.3f} ({steps} steps)", flush=True)
    return score


def main():
    random.seed(99)
    print("=" * 50)
    print("GeoShield — Random Agent Baseline")
    print("=" * 50)

    scores = []
    for task_id in [1, 2, 3]:
        score = run_episode(task_id=task_id, seed=99)
        scores.append(score)
        time.sleep(0.5)

    overall = sum(scores) / len(scores)
    print("\n" + "=" * 50)
    print(f"Random Agent Results:")
    print(f"  Task 1 (false_alarm_detection): {scores[0]:.3f}")
    print(f"  Task 2 (threat_classification): {scores[1]:.3f}")
    print(f"  Task 3 (drone_allocation):      {scores[2]:.3f}")
    print(f"  Overall:                        {overall:.3f}")
    print("=" * 50)
    print("Expected random scores:")
    print("  Task 1: ~0.50 (binary, 50% chance)")
    print("  Task 2: ~0.30 (5 classes + threat level)")
    print("  Task 3: ~0.25 (3 sectors + poor reasoning)")
    print("=" * 50)


if __name__ == "__main__":
    main()