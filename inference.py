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

# ── Config ─────────────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY", "")
ENV_URL      = os.getenv("ENV_URL", "https://norriy0u-geoshield-env.hf.space")

MAX_STEPS = 3
TASKS     = [1, 2, 3, 4]
SEED      = 42

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
)

# ── Prompts ────────────────────────────────────────────────────────────────────

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


# ── LLM call ───────────────────────────────────────────────────────────────────

def call_llm(user_prompt: str) -> dict:
    try:
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
    except json.JSONDecodeError:
        return {"action": "ignore", "reasoning": "parse error"}
    except Exception as e:
        print(f"[LLM ERROR] {e}", file=sys.stderr)
        return {"action": "ignore", "reasoning": str(e)}


# ── Env helpers ────────────────────────────────────────────────────────────────

def env_reset(task_id: int, seed: int = SEED) -> dict:
    r = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id, "seed": seed}, timeout=30)
    r.raise_for_status()
    return r.json()


def env_step(session_id: str, action: dict) -> dict:
    payload = {"session_id": session_id, **action}
    r = requests.post(f"{ENV_URL}/step", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Run one episode ────────────────────────────────────────────────────────────

def run_episode(task_id: int, seed: int = SEED) -> float:
    reset_data   = env_reset(task_id, seed)
    session_id   = reset_data["session_id"]
    obs          = reset_data["observation"]
    case_id      = reset_data["info"]["case_id"]
    difficulty   = reset_data["info"]["difficulty"]

    print(json.dumps({
        "event":      "[START]",
        "task_id":    task_id,
        "case_id":    case_id,
        "session_id": session_id,
        "difficulty": difficulty,
        "seed":       seed,
    }))

    total_reward = 0.0
    done         = False
    step_num     = 0

    while not done and step_num < MAX_STEPS:
        step_num += 1
        user_prompt = build_user_prompt(obs)
        action      = call_llm(user_prompt)

        step_data = env_step(session_id, action)
        reward    = step_data.get("reward", 0.0)
        done      = step_data.get("done", True)
        info      = step_data.get("info", {})
        obs       = step_data.get("observation", obs)
        total_reward = info.get("total_score", reward)

        print(json.dumps({
            "event":    "[STEP]",
            "task_id":  task_id,
            "step":     step_num,
            "action":   action,
            "reward":   reward,
            "done":     done,
            "feedback": info.get("feedback", ""),
        }))

        if not done:
            time.sleep(0.5)

    print(json.dumps({
        "event":        "[END]",
        "task_id":      task_id,
        "case_id":      case_id,
        "total_reward": total_reward,
        "steps":        step_num,
    }))

    return total_reward


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(json.dumps({
        "event":   "[START]",
        "run":     "geoshield_baseline",
        "model":   MODEL_NAME,
        "env_url": ENV_URL,
        "tasks":   TASKS,
    }))

    results = {}
    for task_id in TASKS:
        try:
            score = run_episode(task_id, seed=SEED)
            results[f"task_{task_id}"] = round(score, 4)
        except Exception as e:
            print(f"[ERROR] Task {task_id} failed: {e}", file=sys.stderr)
            results[f"task_{task_id}"] = 0.0
        time.sleep(1)

    overall = round(sum(results.values()) / len(results), 4)
    results["overall"] = overall

    print(json.dumps({
        "event":   "[END]",
        "run":     "geoshield_baseline",
        "results": results,
        "status":  "complete",
    }))


if __name__ == "__main__":
    main()