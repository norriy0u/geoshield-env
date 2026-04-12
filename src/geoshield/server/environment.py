"""
GeoShield Environment — Core OpenEnv environment with multi-step episodes.

Architecture:
  • Tasks 1-2: Two-phase episodes (gather intel → decide)
  • Task 3: Multi-turn with investigation before deployment
  • Task 4: Multi-turn with verification before classification
  • Episode reward = terminal graded step score (not averaged)
  • Investigation/verification steps scored separately
"""

import random
from typing import Dict, Any, Optional
from src.geoshield.models import GeoObservation, GeoShieldAction, GeoReward, GeoState, SectorReport
from src.geoshield.constants import TASK_ACTIONS, MAX_STEPS, TASK_NAMES
from src.geoshield.server.generators import sample_case
from src.geoshield.server.graders import GRADERS


def _clamp(score) -> float:
    try:
        return round(max(0.02, min(0.98, float(score))), 4)
    except Exception:
        return 0.02


class GeoShieldEnvironment:
    def __init__(self):
        self.task_id: int = 1
        self.seed: int = 42
        self.split: str = "train"
        self.case: Dict[str, Any] = {}
        self.step_count: int = 0
        self.done: bool = False
        self.rewards: list = []
        self.total_score: float = 0.02
        self.episode_reward: float = 0.02       # Terminal graded score
        self.cumulative_reward: float = 0.0     # Sum of all step rewards
        self.investigation_results: Dict[str, str] = {}
        self.drone_deployed: bool = False
        self.case_id: str = ""
        self.context_requested: bool = False    # Task 1: extra context gathered
        self.analysis_requested: bool = False   # Task 2: extra analysis gathered

    # ── reset ──────────────────────────────────────────────────────────────────

    def reset(self, task_id: int = 1, seed: int = 42, split: str = "train") -> Dict[str, Any]:
        self.task_id = task_id
        self.seed = seed
        self.split = split
        self.step_count = 0
        self.done = False
        self.rewards = []
        self.total_score = 0.02
        self.episode_reward = 0.02
        self.cumulative_reward = 0.0
        self.investigation_results = {}
        self.drone_deployed = False
        self.context_requested = False
        self.analysis_requested = False

        self.case = sample_case(task_id, seed, split)
        self.case_id = self.case.get("id", f"t{task_id}_unknown")

        obs = self._build_observation()
        return {
            "observation": obs.model_dump(),
            "state": self._build_state().model_dump(),
            "done": False,
            "info": {
                "task_id": self.task_id,
                "case_id": self.case_id,
                "difficulty": self.case.get("difficulty", "easy"),
                "split": split,
                "seed": seed,
                "procedural": self.case_id.startswith("t") and "_proc_" in self.case_id,
            }
        }

    # ── step ───────────────────────────────────────────────────────────────────

    def step(self, action_input: Dict[str, Any]) -> Dict[str, Any]:
        if self.done:
            obs = self._build_observation()
            return {
                "observation": obs.model_dump(),
                "reward": 0.02,
                "done": True,
                "info": {"feedback": "Episode already completed."},
                "session_id": None,
            }

        action = GeoShieldAction(**action_input) if isinstance(action_input, dict) else action_input
        self.step_count += 1
        max_steps = MAX_STEPS.get(self.task_id, 3)

        # ── Task 1: handle request_context (multi-step intelligence gathering) ─
        if self.task_id == 1 and action.action == "request_context":
            self.context_requested = True
            additional = self.case.get("additional_context", "No additional intelligence available.")
            obs = self._build_observation(extra_hint=f"ADDITIONAL INTELLIGENCE: {additional}")
            reward_val = _clamp(0.15)  # Small reward for gathering intel
            self.rewards.append(reward_val)
            self.cumulative_reward += reward_val
            if self.step_count >= max_steps:
                self.done = True
            return {
                "observation": obs.model_dump(),
                "reward": reward_val,
                "done": self.done,
                "info": {
                    "feedback": f"Context requested. Additional intelligence: {additional}",
                    "step": self.step_count,
                    "total_score": self.total_score,
                },
            }

        # ── Task 2: handle request_analysis (multi-step sensor analysis) ──────
        if self.task_id == 2 and action.action == "request_analysis":
            self.analysis_requested = True
            analysis = self.case.get("analysis_detail", "Sensor analysis pending.")
            obs = self._build_observation(extra_hint=f"SENSOR ANALYSIS: {analysis}")
            reward_val = _clamp(0.15)  # Small reward for gathering intel
            self.rewards.append(reward_val)
            self.cumulative_reward += reward_val
            if self.step_count >= max_steps:
                self.done = True
            return {
                "observation": obs.model_dump(),
                "reward": reward_val,
                "done": self.done,
                "info": {
                    "feedback": f"Analysis requested. Sensor data: {analysis}",
                    "step": self.step_count,
                    "total_score": self.total_score,
                },
            }

        # ── Task 3: handle investigate actions (multi-turn) ───────────────────
        if self.task_id == 3 and action.action.startswith("investigate_"):
            result = self._handle_investigation(action.action)
            self.investigation_results[action.action] = result
            obs = self._build_observation()
            reward_val = _clamp(0.30 if action.action.replace("investigate_", "deploy_to_") == self.case.get("gold_action") else 0.10)
            self.rewards.append(reward_val)
            self.cumulative_reward += reward_val
            if self.step_count >= max_steps:
                self.done = True
            return {
                "observation": obs.model_dump(),
                "reward": reward_val,
                "done": self.done,
                "info": {
                    "feedback": f"Investigation complete: {result}",
                    "step": self.step_count,
                    "total_score": self.total_score,
                },
            }

        # ── Task 4: handle request_verification ───────────────────────────────
        if self.task_id == 4 and action.action == "request_verification":
            verification = self._handle_verification()
            obs = self._build_observation(extra_hint=verification)
            reward_val = _clamp(0.35)
            self.rewards.append(reward_val)
            self.cumulative_reward += reward_val
            if self.step_count >= max_steps:
                self.done = True
            return {
                "observation": obs.model_dump(),
                "reward": reward_val,
                "done": self.done,
                "info": {
                    "feedback": f"Verification requested. Additional intel: {verification}",
                    "step": self.step_count,
                    "total_score": self.total_score,
                },
            }

        # ── Standard graded step (terminal) ───────────────────────────────────
        grader = GRADERS.get(self.task_id)
        if grader is None:
            raise ValueError(f"No grader for task {self.task_id}")

        # Pass context flags to grader for bonus scoring
        grader_context = {
            "context_requested": self.context_requested,
            "analysis_requested": self.analysis_requested,
            "investigation_used": bool(self.investigation_results),
        }

        reward: GeoReward = grader(action, self.case, grader_context)
        clamped = _clamp(reward.score)
        reward.score = clamped
        self.rewards.append(clamped)
        self.cumulative_reward += clamped

        # Episode reward = terminal graded step score (NOT average of all steps)
        self.episode_reward = clamped
        self.total_score = clamped
        self.done = True

        obs = self._build_observation()
        return {
            "observation": obs.model_dump(),
            "reward": clamped,
            "done": True,
            "info": {
                "feedback": reward.feedback,
                "breakdown": reward.breakdown,
                "step": self.step_count,
                "total_score": self.total_score,
                "episode_reward": self.episode_reward,
                "cumulative_reward": _clamp(self.cumulative_reward),
                "completed": True,
                "intel_gathered": self.context_requested or self.analysis_requested or bool(self.investigation_results),
            },
        }

    # ── state ──────────────────────────────────────────────────────────────────

    def state(self) -> Dict[str, Any]:
        return self._build_state().model_dump()

    # ── internal helpers ───────────────────────────────────────────────────────

    def _build_observation(self, extra_hint: Optional[str] = None) -> GeoObservation:
        task_id = self.task_id
        case = self.case
        actions = TASK_ACTIONS.get(task_id, [])
        max_steps = MAX_STEPS.get(task_id, 3)

        hint = extra_hint or case.get("hint", self._default_hint())

        # Add context/analysis availability to hint
        if task_id == 1 and not self.context_requested and self.step_count == 0:
            hint += " TIP: Use 'request_context' to gather additional intelligence before deciding."
        if task_id == 2 and not self.analysis_requested and self.step_count == 0:
            hint += " TIP: Use 'request_analysis' for detailed sensor data before classifying."

        if task_id == 1:
            return GeoObservation(
                task_id=task_id,
                case_id=self.case_id,
                step=self.step_count,
                difficulty=case.get("difficulty", "easy"),
                report=case.get("report", ""),
                context=case.get("context", ""),
                available_actions=actions,
                hint=hint,
                steps_remaining=max_steps - self.step_count,
            )

        if task_id == 2:
            return GeoObservation(
                task_id=task_id,
                case_id=self.case_id,
                step=self.step_count,
                difficulty=case.get("difficulty", "medium"),
                report=case.get("report", ""),
                context=case.get("context", ""),
                available_actions=actions,
                hint=hint,
                steps_remaining=max_steps - self.step_count,
            )

        if task_id == 3:
            sectors_raw = case.get("sectors", [])
            sectors = []
            for s in sectors_raw:
                sectors.append(SectorReport(
                    sector_id=s.get("sector_id", ""),
                    summary=s.get("summary", ""),
                    anomaly_type=s.get("anomaly_type"),
                    confidence=s.get("confidence", 0.5),
                    coordinates=s.get("coordinates"),
                    timestamp=s.get("timestamp", "00:00Z"),
                ))

            inv_hint = ""
            if self.investigation_results:
                inv_hint = " | Investigations: " + "; ".join(
                    f"{k.replace('investigate_', '').upper()}: {v}"
                    for k, v in self.investigation_results.items()
                )

            return GeoObservation(
                task_id=task_id,
                case_id=self.case_id,
                step=self.step_count,
                difficulty=case.get("difficulty", "hard"),
                sectors=sectors,
                available_actions=actions,
                available_assets=case.get("available_assets", "1 surveillance drone"),
                hint=hint + inv_hint,
                investigation_results=self.investigation_results if self.investigation_results else None,
                steps_remaining=max_steps - self.step_count,
            )

        if task_id == 4:
            indicators = case.get("deception_indicators", [])
            indicators_text = ""
            if indicators:
                indicators_text = " Anomalies detected: " + "; ".join(indicators[:2])

            return GeoObservation(
                task_id=task_id,
                case_id=self.case_id,
                step=self.step_count,
                difficulty=case.get("difficulty", "hard"),
                report=case.get("report", "") + indicators_text,
                context=case.get("context", ""),
                available_actions=actions,
                hint=hint,
                steps_remaining=max_steps - self.step_count,
            )

        return GeoObservation(
            task_id=task_id,
            case_id=self.case_id,
            step=self.step_count,
            difficulty="easy",
            report=case.get("report", ""),
            available_actions=actions,
        )

    def _build_state(self) -> GeoState:
        return GeoState(
            task_id=self.task_id,
            case_id=self.case_id,
            completed=self.done,
            step=self.step_count,
            rewards=self.rewards,
            total_score=self.total_score,
            difficulty=self.case.get("difficulty", "easy"),
            current_observation=str(self._build_observation().model_dump()),
            investigation_used=bool(self.investigation_results),
            drone_deployed=self.drone_deployed,
        )

    def _default_hint(self) -> str:
        hints = {
            1: "Classify this satellite report as 'ignore' or 'flag_for_review'. You may 'request_context' for additional intelligence first.",
            2: "Identify the threat type and rate its severity (1-10). You may 'request_analysis' for detailed sensor data first.",
            3: "Analyze all sectors and deploy your drone to the highest priority threat. You may investigate one sector first.",
            4: "Determine if this facility is a covert operation or legitimate activity. Identify the cover story and deception type if applicable. You may 'request_verification' for additional SIGINT.",
        }
        return hints.get(self.task_id, "Analyze and respond.")

    def _handle_investigation(self, action: str) -> str:
        sector = action.replace("investigate_", "").upper()
        sectors_raw = self.case.get("sectors", [])
        gold_action = self.case.get("gold_action", "")
        gold_sector = gold_action.replace("deploy_to_", "").upper()

        for s in sectors_raw:
            if s.get("sector_id", "").upper() == sector:
                anomaly = s.get("anomaly_type", "no anomaly")
                confidence = s.get("confidence", 0.5)
                if sector == gold_sector:
                    return f"PRIORITY CONFIRMED — {anomaly} detected, confidence {confidence:.0%}. Immediate drone deployment recommended."
                else:
                    return f"Low priority — {anomaly or 'no significant activity'}, confidence {confidence:.0%}. Consider other sectors."

        return f"Sector {sector}: No detailed data available."

    def _handle_verification(self) -> str:
        indicators = self.case.get("deception_indicators", [])
        if not indicators:
            return "Secondary analysis confirms no suspicious activity. Facility appears legitimate."
        hidden = indicators[2:] if len(indicators) > 2 else indicators
        if hidden:
            return f"SIGINT confirms anomaly: {hidden[0]}. Classification confidence elevated."
        return "Additional analysis inconclusive. Proceed with available evidence."
