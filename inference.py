"""
GeoShield — Inference Script
Runs an LLM agent against all 3 GeoShield tasks and emits structured stdout logs.

Required env vars:
    API_BASE_URL   The API endpoint for the LLM
    MODEL_NAME     The model identifier
    HF_TOKEN       Your Hugging Face / API key

Stdout format (mandatory):
    [START] task=<task_name> env=geoshield model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...>
"""

import os
import json
import time
import requests
from typing import List, Optional
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

BENCHMARK = "geoshield"
MAX_STEPS = 8
TEMPERATURE = 0.2
MAX_TOKENS = 512
SUCCESS_THRESHOLD = 0.5

TASK_NAMES = {
    1: "false_alarm_detection",
    2: "threat_classification",
    3: "drone_allocation",
}

# ── Logging ───────────────────────────────────────────────────────────────────

def log_start(task: str, model: str) -> None:
    print(f"[START] task={task} env={BENCHMARK} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # clean action string — no spaces or newlines
    action_clean = action.replace("\n", " ").replace("\r", "").strip()[:80]
    print(
        f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )

# ── Environment client ────────────────────────────────────────────────────────

def env_reset(task_id: int, seed: int = 42) -> dict:
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

# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_T1 = """You are a Defense Zone Commander AI analyzing satellite intelligence reports.

Your task: Classify each report as a FALSE ALARM or REAL THREAT.

Output ONLY a JSON object with this exact format:
{"action": "ignore"}
or
{"action": "flag_for_review"}

Rules:
- "ignore" = false alarm (wildlife, weather, registered civilian activity, valid permits)
- "flag_for_review" = real threat (unregistered convoys, illegal construction, suspicious activity)
- Output ONLY the JSON. No explanation. No markdown. No extra text."""

SYSTEM_PROMPT_T2 = """You are a Defense Zone Commander AI analyzing confirmed anomaly reports.

Your task: Classify the threat type AND assign a severity level 1-10.

Output ONLY a JSON object with this exact format:
{"action": "troop_movement", "threat_level": 8}

Valid action values:
- "troop_movement" — military personnel or vehicles moving
- "illegal_construction" — unauthorized building, bunkers, tunnels, airstrips
- "unauthorized_aircraft" — unregistered drones, planes, balloons
- "weapons_cache" — hidden weapons, ammunition, explosives
- "civilian_activity" — confirmed non-threatening civilian activity

Threat level guide:
1-2: No real threat (civilian)
3-4: Minor concern
5-6: Moderate threat, needs monitoring
7-8: Serious threat, immediate attention
9-10: Critical threat, imminent danger

Output ONLY the JSON. No explanation. No markdown. No extra text."""

SYSTEM_PROMPT_T3 = """You are a Defense Zone Commander AI with ONE reconnaissance drone to deploy.

Your task: Analyze 3 simultaneous sector reports and deploy the drone to the HIGHEST PRIORITY sector.

Output ONLY a JSON object with this exact format:
{"action": "deploy_to_sector_b", "target_sector": "sector_b", "reasoning": "Sector B has an unregistered armored convoy indicating imminent military threat requiring immediate reconnaissance before the window closes."}

Valid action values:
- "deploy_to_sector_a"
- "deploy_to_sector_b"  
- "deploy_to_sector_c"

Priority rules (highest to lowest):
1. Active military movement (troop_movement with high confidence)
2. Weapons cache or explosive threat
3. Illegal construction with strategic value (bunkers, missile sites, tunnels)
4. Unauthorized aircraft over critical infrastructure
5. Illegal construction (general)
6. Civilian activity (lowest priority)

The "reasoning" field must be at least 100 words explaining your strategic decision.
Output ONLY the JSON. No explanation outside JSON. No markdown."""

SYSTEM_PROMPTS = {
    1: SYSTEM_PROMPT_T1,
    2: SYSTEM_PROMPT_T2,
    3: SYSTEM_PROMPT_T3,
}

# ── Observation formatter ─────────────────────────────────────────────────────

def format_observation(obs: dict, task_id: int) -> str:
    if task_id == 1:
        return (
            f"SATELLITE INTELLIGENCE REPORT\n"
            f"{'='*50}\n"
            f"Report: {obs.get('report', 'N/A')}\n"
            f"Context: {obs.get('context', 'N/A')}\n"
            f"Difficulty: {obs.get('difficulty', 'N/A')}\n"
            f"{'='*50}\n"
            f"Classify as: ignore OR flag_for_review"
        )
    elif task_id == 2:
        return (
            f"CONFIRMED ANOMALY REPORT\n"
            f"{'='*50}\n"
            f"Report: {obs.get('report', 'N/A')}\n"
            f"Context: {obs.get('context', 'N/A')}\n"
            f"Difficulty: {obs.get('difficulty', 'N/A')}\n"
            f"{'='*50}\n"
            f"Classify threat type and assign severity 1-10."
        )
    elif task_id == 3:
        sectors = obs.get("sectors", [])
        sector_text = ""
        for s in sectors:
            sector_text += (
                f"\n  [{s.get('sector_id', '?').upper()}]\n"
                f"  Summary: {s.get('summary', 'N/A')}\n"
                f"  Anomaly Type: {s.get('anomaly_type', 'unknown')}\n"
                f"  Confidence: {s.get('confidence', 0):.0%}\n"
                f"  Coordinates: {s.get('coordinates', 'N/A')}\n"
                f"  Timestamp: {s.get('timestamp', 'N/A')}\n"
            )
        return (
            f"MULTI-SECTOR INTELLIGENCE BRIEFING\n"
            f"{'='*50}\n"
            f"Available Assets: {obs.get('available_assets', '1 reconnaissance drone')}\n"
            f"SECTOR REPORTS:{sector_text}"
            f"{'='*50}\n"
            f"Deploy your ONE drone to the highest priority sector."
        )
    return str(obs)

# ── Action parser ─────────────────────────────────────────────────────────────

def parse_action(text: str, task_id: int) -> dict:
    """Parse LLM output into action dict. Handles messy JSON."""
    text = text.strip()

    # Strip markdown fences
    if "```" in text:
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
    except Exception:
        # Fallback defaults
        if task_id == 1:
            return {"action": "ignore"}
        elif task_id == 2:
            return {"action": "civilian_activity", "threat_level": 1}
        else:
            return {
                "action": "deploy_to_sector_a",
                "target_sector": "sector_a",
                "reasoning": "Defaulting to sector_a due to parse error.",
            }

    # Ensure required fields
    if task_id == 2 and "threat_level" not in data:
        data["threat_level"] = 5
    if task_id == 3:
        if "target_sector" not in data:
            action = data.get("action", "deploy_to_sector_a")
            data["target_sector"] = action.replace("deploy_to_", "")
        if "reasoning" not in data:
            data["reasoning"] = "No reasoning provided."

    return data

# ── LLM call ──────────────────────────────────────────────────────────────────

def call_llm(client: OpenAI, task_id: int, obs: dict) -> str:
    system_prompt = SYSTEM_PROMPTS[task_id]
    user_prompt = format_observation(obs, task_id)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[DEBUG] LLM call failed: {e}", flush=True)
        return "{}"

# ── Run one task episode ──────────────────────────────────────────────────────

def run_episode(client: OpenAI, task_id: int, seed: int) -> float:
    task_name = TASK_NAMES[task_id]

    log_start(task=task_name, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    session_id = None

    try:
        # Reset
        reset_result = env_reset(task_id=task_id, seed=seed)
        session_id = reset_result.get("session_id", "default")
        obs = reset_result.get("observation", {})
        done = reset_result.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            # Get LLM response
            raw_text = call_llm(client, task_id, obs)
            action_data = parse_action(raw_text, task_id)

            # Step environment
            result = env_step(action_data, session_id)
            reward = float(result.get("reward", 0.0))
            done = result.get("done", False)
            info = result.get("info", {})
            error = info.get("error", None)
            obs = result.get("observation", obs) or obs

            rewards.append(reward)
            steps_taken = step

            # Action string for logging
            action_str = action_data.get("action", "unknown")
            if task_id == 2:
                action_str += f"|threat={action_data.get('threat_level', '?')}"
            elif task_id == 3:
                action_str += f"|sector={action_data.get('target_sector', '?')}"

            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=str(error) if error else None,
            )

            if done:
                break

            time.sleep(0.5)  # rate limit safety

        # Score = average reward across steps
        score = sum(rewards) / len(rewards) if rewards else 0.0
        score = round(min(max(score, 0.0), 1.0), 3)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", flush=True)
        score = 0.0
        success = False

    finally:
        log_end(
            success=success,
            steps=steps_taken,
            score=score,
            rewards=rewards,
        )

    return score

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN,
    )

    print(f"[DEBUG] ENV_URL={ENV_URL}", flush=True)
    print(f"[DEBUG] MODEL={MODEL_NAME}", flush=True)
    print(f"[DEBUG] API_BASE={API_BASE_URL}", flush=True)

    all_scores = []

    for task_id in [1, 2, 3]:
        print(f"\n[DEBUG] ── Running Task {task_id}: {TASK_NAMES[task_id]} ──", flush=True)
        score = run_episode(client, task_id=task_id, seed=42)
        all_scores.append(score)
        print(f"[DEBUG] Task {task_id} score: {score:.3f}", flush=True)
        time.sleep(1)

    overall = sum(all_scores) / len(all_scores)
    print(f"\n[DEBUG] ── Overall Score: {overall:.3f} ──", flush=True)
    print(f"[DEBUG] Task scores: T1={all_scores[0]:.3f} T2={all_scores[1]:.3f} T3={all_scores[2]:.3f}", flush=True)

if __name__ == "__main__":
    main()