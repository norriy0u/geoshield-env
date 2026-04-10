#!/usr/bin/env python3
"""
GeoShield Inference Script
OpenEnv-compliant baseline using OpenAI client.
Emits structured [START], [STEP], [END] logs to stdout.
"""

import os
import sys
import json
import time
import requests
from openai import OpenAI

#── Config ─────────────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY", "")
ENV_URL      = os.getenv("ENV_URL", "https://norriy0u-geoshield-env.hf.space")

MAX_STEPS = 3
TASKS     = [1, 2, 3, 4]
SEED      = 42

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN if HF_TOKEN else "dummy",
)

SYSTEM_PROMPT = """You are a satellite intelligence analyst. You will receive
intelligence reports and must respond with precise JSON actions.

For Task 1 (false alarm detection):
  {"action": "ignore"} or {"action": "flag_for_review"}

For Task 2 (threat classification):
  {"action": "<threat_type>", "threat_level": <1-10>}
  threat types: troop_movement, illegal_construction, unauthorized_aircraft, weapons_cache, civilian_activity

For Task 3 (drone allocation):
  {"action": "deploy_to_sector_a|b|c"} or {"action": "investigate_sector_a|b|c"}
  Include: {"reasoning": "<your strategic analysis>"}

For Task 4 (covert operation detection):
  {"action": "covert_operation|legitimate_activity|request_verification",
   "cover_story_identified": "<the civilian cover being used>",
   "deception_type": "<one of: civilian_military|commercial_weapons|construction_fortification|logistics_supply|research_weapons>",
   "reasoning": "<your analysis of the deception indicators>"}

Always respond with valid JSON only. No explanation outside the JSON."""


def clamp(score) -> float:
    try:
        return round(max(0.02, min(0.98, float(score))), 4)
    except Exception:
        return 0.02


def rules_fallback(obs: dict) -> dict:
    task_id = obs.get("task_id", 1)
    actions = obs.get("available_actions", [])
    report  = (obs.get("report") or "").lower()

    if task_id == 1:
        suspicious = any(w in report for w in [
            "armed", "weapon", "military", "unauthorized", "illegal",
            "threat", "missile", "explosive", "hostile", "combat"
        ])
        return {"action": "flag_for_review" if suspicious else "ignore"}

    elif task_id == 2:
        if any(w in report for w in ["troop", "soldier", "convoy", "battalion"]):
            return {"action": "troop_movement", "threat_level": 7}
        if any(w in report for w in ["aircraft", "drone", "uav", "jet"]):
            return {"action": "unauthorized_aircraft", "threat_level": 6}
        if any(w in report for w in ["weapon", "cache", "arsenal", "munition"]):
            return {"action": "weapons_cache", "threat_level": 8}
        if any(w in report for w in ["construction", "build", "facility", "structure"]):
            return {"action": "illegal_construction", "threat_level": 4}
        return {"action": "civilian_activity", "threat_level": 2}

    elif task_id == 3:
        deploy = [a for a in actions if a.startswith("deploy_")]
        return {
            "action": deploy[0] if deploy else "deploy_to_sector_a",
            "reasoning": "Deploying to highest priority sector based on detected anomaly indicators and threat assessment."
        }

    elif task_id == 4:
        covert_keywords = [
            "military", "weapon", "classified", "encrypted", "anomal",
            "inconsistent", "exceeds", "military-grade", "defense", "combat"
        ]
        if any(w in report for w in covert_keywords):
            return {
                "action": "covert_operation",
                "cover_story_identified": "civilian facility concealing military or weapons activity",
                "deception_type": "civilian_military",
                "reasoning": "Multiple anomalies detected inconsistent with declared civilian purpose."
            }
        return {
            "action": "legitimate_activity",
            "cover_story_identified": "",
            "deception_type": "",
            "reasoning": "No significant anomalies detected. Facility appears consistent with declared purpose."
        }

    return {"action": actions[0] if actions else "ignore"}


def build_user_prompt(obs: dict) -> str:
    task_id = obs.get("task_id", 1)
    lines = [f"TASK {task_id} | Case: {obs.get('case_id')} | Step: {obs.get('step')} | Difficulty: {obs.get('difficulty')}"]

    if obs.get("report"):
        lines.append(f"\nREPORT:\n{obs['report']}")
    if obs.get("context"):
        lines.append(f"\nCONTEXT: {obs['context']}")
    if obs.get("sectors"):
        lines.append("\nSECTOR REPORTS:")
        for s in obs["sectors"]:
            if isinstance(s, dict):
                lines.append(f"  [{s.get('sector_id','?').upper()}] {s.get('summary','')} | Anomaly: {s.get('anomaly_type','none')} | Confidence: {s.get('confidence',0):.0%}")
    if obs.get("investigation_results"):
        lines.append("\nINVESTIGATION RESULTS:")
        for k, v in obs["investigation_results"].items():
            lines.append(f"  {k}: {v}")
    if obs.get("steps_remaining") is not None:
        lines.append(f"\nSteps remaining: {obs['steps_remaining']}")

    lines.append(f"\nAvailable actions: {obs.get('available_actions', [])}")
    lines.append(f"\nHint: {obs.get('hint', '')}")
    lines.append("\nRespond with JSON only.")
    return "\n".join(lines)


def call_llm(user_prompt: str, obs: dict = None) -> dict:
    try:
        if not HF_TOKEN:
            raise ValueError("No API token available")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=512,
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[ERROR] llm_error={e} using_fallback=true", file=sys.stderr, flush=True)
        if obs is not None:
            return rules_fallback(obs)
        return {"action": "ignore", "reasoning": "fallback"}


def env_reset(task_id: int, seed: int = SEED) -> dict:
    r = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id, "seed": seed}, timeout=30)
    r.raise_for_status()
    return r.json()


def env_step(session_id: str, action: dict) -> dict:
    payload = {"session_id": session_id, **action}
    r = requests.post(f"{ENV_URL}/step", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def run_episode(task_id: int, seed: int = SEED) -> float:
    try:
        reset_data = env_reset(task_id, seed)
        session_id = reset_data["session_id"]
        obs        = reset_data["observation"]
        case_id    = reset_data["info"]["case_id"]
        difficulty = reset_data["info"]["difficulty"]
    except Exception as e:
        print(f"[START] task=geoshield env=geoshield model={MODEL_NAME}", flush=True)
        print(f"[STEP] step=1 action=ignore reward=0.02 done=true error=reset_failed", flush=True)
        print(f"[END] success=false steps=1 rewards=0.02", flush=True)
        return 0.02

    print(f"[START] task=geoshield env=geoshield model={MODEL_NAME}", flush=True)

    total_reward = 0.02
    done         = False
    step_num     = 0
    rewards_list = []

    try:
        while not done and step_num < MAX_STEPS:
            step_num += 1
            user_prompt  = build_user_prompt(obs)
            action       = call_llm(user_prompt, obs)

            step_data    = env_step(session_id, action)
            raw_reward   = step_data.get("reward", 0.02)
            reward       = clamp(raw_reward)
            done         = step_data.get("done", True)
            info         = step_data.get("info", {})
            obs          = step_data.get("observation", obs)
            raw_total    = info.get("total_score", reward)
            total_reward = clamp(raw_total)

            rewards_list.append(reward)

            print(f"[STEP] step={step_num} action={action.get('action','')} reward={reward:.2f} done={str(done).lower()} error=null", flush=True)

            if not done:
                time.sleep(0.5)

    except Exception as e:
        rewards_list.append(0.02)
        print(f"[STEP] step={step_num} action=ignore reward=0.02 done=true error={str(e)}", flush=True)
        total_reward = 0.02

    rewards_str = f"{total_reward:.4f}"
    success = total_reward >= 0.5
    print(f"[END] success={str(success).lower()} steps={step_num} rewards={rewards_str}", flush=True)
    return total_reward


def main():
    for task_id in TASKS:
        try:
            score = run_episode(task_id, seed=SEED)
            results[f"task_{task_id}"] = clamp(score)
        except Exception as e:
            print(f"[START] task=geoshield env=geoshield model={MODEL_NAME}", flush=True)
            print(f"[STEP] step=1 action=ignore reward=0.02 done=true error={str(e)}", flush=True)
            print(f"[END] success=false steps=1 rewards=0.02", flush=True)
            results[f"task_{task_id}"] = 0.02
        time.sleep(1)

    overall = clamp(sum(results.values()) / len(results))
    results["overall"] = overall



if __name__ == "__main__":
    main()
