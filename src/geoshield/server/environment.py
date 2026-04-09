import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src/geoshield')

import uuid
import time
from typing import Dict, Any, Optional

from src.geoshield.models import GeoShieldAction, GeoObservation, GeoReward, GeoState, SectorReport
from src.geoshield.constants import TASK_ACTIONS, MAX_STEPS
from src.geoshield.server.generators import sample_case
from src.geoshield.server.graders import GRADERS


class GeoShieldEnvironment:
    def __init__(self):
        self.state: Optional[GeoState] = None
        self.current_case: Optional[Dict[str, Any]] = None
        self.task_id: int = 1
        self.split: str = "train"

    # ── reset ────────────────────────────────────────────────────────────────

    def reset(self, task_id: int = 1, seed: int = None, split: str = "train") -> Dict[str, Any]:
        self.task_id = task_id
        self.split = split

        if seed is None:
            seed = int(time.time() * 1000) % 100000

        self.current_case = sample_case(task_id, seed=seed, split=split)

        case_id = self.current_case.get("id", str(uuid.uuid4()))
        difficulty = self.current_case.get("difficulty", "easy")

        self.state = GeoState(
            task_id=task_id,
            case_id=case_id,
            completed=False,
            step=0,
            rewards=[],
            total_score=0.0,
            difficulty=difficulty,
        )

        obs = self._build_observation()
        self.state.current_observation = str(obs.dict())

        return {
            "observation": obs.dict(),
            "state": self.state.dict(),
            "done": False,
            "info": {
                "task_id": task_id,
                "case_id": case_id,
                "difficulty": difficulty,
                "split": split,
                "seed": seed,
            }
        }

    # ── step ─────────────────────────────────────────────────────────────────

    def step(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.state is None or self.current_case is None:
            return self._error_response("Environment not initialized. Call reset() first.")

        if self.state.completed:
            return self._error_response("Episode already completed. Call reset() to start a new episode.")

        # Parse action
        try:
            action = GeoShieldAction(**action_data)
        except Exception as e:
            return self._error_response(f"Invalid action format: {str(e)}")

        # Validate action
        valid_actions = TASK_ACTIONS.get(self.task_id, [])
        if action.action not in valid_actions:
            # Soft penalty — don't crash, just penalize
            reward = GeoReward(
                score=0.01,
                feedback=f"Invalid action '{action.action}'. Valid actions: {valid_actions}",
                breakdown={"error": "invalid_action"}
            )
            self.state.step += 1
            self.state.rewards.append(reward.score)
            self.state.total_score = sum(self.state.rewards) / len(self.state.rewards)

            done = self.state.step >= MAX_STEPS.get(self.task_id, 2)
            if done:
                self.state.completed = True

            return {
                "observation": self._build_observation().dict(),
                "reward": reward.score,
                "done": done,
                "info": {
                    "feedback": reward.feedback,
                    "breakdown": reward.breakdown,
                    "step": self.state.step,
                    "total_score": self.state.total_score,
                }
            }

        # Grade action
        grader = GRADERS.get(self.task_id)
        if grader is None:
            return self._error_response(f"No grader found for task {self.task_id}")

        reward = grader(action, self.current_case)

        # Update state
        self.state.step += 1
        self.state.rewards.append(reward.score)
        self.state.total_score = sum(self.state.rewards) / len(self.state.rewards)

        # Step penalty for excessive steps
        max_steps = MAX_STEPS.get(self.task_id, 2)
        if self.state.step >= max_steps:
            self.state.completed = True
            done = True
        else:
            done = reward.score >= 0.8  # early termination on high score
            if done:
                self.state.completed = True

        obs = self._build_observation()
        self.state.current_observation = str(obs.dict())

        return {
            "observation": obs.dict(),
            "reward": reward.score,
            "done": done,
            "info": {
                "feedback": reward.feedback,
                "breakdown": reward.breakdown,
                "step": self.state.step,
                "total_score": self.state.total_score,
                "completed": self.state.completed,
            }
        }

    # ── state ─────────────────────────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        if self.state is None:
            return {"error": "Environment not initialized. Call reset() first."}
        return self.state.dict()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _build_observation(self) -> GeoObservation:
        case = self.current_case
        task_id = self.task_id
        step = self.state.step if self.state else 0
        difficulty = case.get("difficulty", "easy")
        available_actions = TASK_ACTIONS.get(task_id, [])

        if task_id == 1:
            return GeoObservation(
                task_id=task_id,
                case_id=case.get("id", "unknown"),
                step=step,
                difficulty=difficulty,
                report=case.get("report", ""),
                context=case.get("context", ""),
                available_actions=available_actions,
                hint="Classify this satellite report as 'ignore' or 'flag_for_review'.",
            )

        elif task_id == 2:
            return GeoObservation(
                task_id=task_id,
                case_id=case.get("id", "unknown"),
                step=step,
                difficulty=difficulty,
                report=case.get("report", ""),
                context=case.get("context", ""),
                available_actions=available_actions,
                hint=(
                    "Classify the anomaly type and set threat_level (1-10). "
                    "Actions: troop_movement, illegal_construction, unauthorized_aircraft, weapons_cache, civilian_activity."
                ),
            )

        elif task_id == 3:
            raw_sectors = case.get("sectors", [])
            sectors = []
            for s in raw_sectors:
                sectors.append(SectorReport(
                    sector_id=s.get("sector_id", "unknown"),
                    summary=s.get("summary", ""),
                    anomaly_type=s.get("anomaly_type"),
                    confidence=s.get("confidence", 0.0),
                    coordinates=s.get("coordinates"),
                    timestamp=s.get("timestamp", "00:00Z"),
                ))

            return GeoObservation(
                task_id=task_id,
                case_id=case.get("id", "unknown"),
                step=step,
                difficulty=difficulty,
                sectors=sectors,
                available_actions=available_actions,
                available_assets=case.get("available_assets", "1 reconnaissance drone"),
                hint=(
                    "Deploy your ONE drone to the highest priority sector. "
                    "Set target_sector to your chosen sector id and provide strategic reasoning."
                ),
            )

        # fallback
        return GeoObservation(
            task_id=task_id,
            case_id=case.get("id", "unknown"),
            step=step,
            difficulty=difficulty,
            available_actions=available_actions,
        )

    def _error_response(self, message: str) -> Dict[str, Any]:
        return {
            "observation": None,
            "reward": 0.0,
            "done": True,
            "info": {"error": message}
        }
