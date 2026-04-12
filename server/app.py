import os
import traceback
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
import json

from src.geoshield.server.environment import GeoShieldEnvironment

app = FastAPI(
    title="GeoShield Environment API",
    description="OpenEnv-compliant satellite intelligence triage environment for RL agent training. Features procedural case generation, multi-step episodes, and deterministic heuristic grading.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Session store ──────────────────────────────────────────────────────────────
_sessions: Dict[str, GeoShieldEnvironment] = {}


def get_env(session_id: str) -> GeoShieldEnvironment:
    if session_id not in _sessions:
        _sessions[session_id] = GeoShieldEnvironment()
    return _sessions[session_id]

# ── Request models ─────────────────────────────────────────────────────────────
class ResetRequest(BaseModel):
    task_id: Optional[int] = 1
    seed: Optional[int] = 42
    split: Optional[str] = "train"
    session_id: Optional[str] = None

    class Config:
        extra = "allow"


class StepRequest(BaseModel):
    action: str
    threat_level: Optional[int] = None
    target_sector: Optional[str] = None
    reasoning: Optional[str] = None
    cover_story_identified: Optional[str] = None
    deception_type: Optional[str] = None
    session_id: Optional[str] = None


class StateRequest(BaseModel):
    session_id: str

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0", "tasks": [1, 2, 3, 4], "features": ["procedural_generation", "multi_step_episodes", "levenshtein_grading"]}


@app.get("/info")
def info():
    return {
        "name": "GeoShield",
        "description": "Satellite intelligence triage OpenEnv environment with procedural case generation, multi-step episodes, and deterministic heuristic grading.",
        "version": "2.0.0",
        "tasks": {
            "1": {"name": "false_alarm_detection", "difficulty": "easy", "actions": ["ignore", "flag_for_review", "request_context"], "multi_step": True},
            "2": {"name": "threat_classification", "difficulty": "medium", "actions": ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity", "request_analysis"], "multi_step": True},
            "3": {"name": "drone_allocation", "difficulty": "hard", "actions": ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c", "investigate_sector_a", "investigate_sector_b", "investigate_sector_c"], "multi_step": True},
            "4": {"name": "covert_operation_detection", "difficulty": "ultra", "actions": ["covert_operation", "legitimate_activity", "request_verification"], "multi_step": True},
        },
        "reward_range": [0.02, 0.98],
        "splits": ["train", "eval"],
        "features": {
            "procedural_generation": "Unlimited seed-deterministic cases via template-based synthesis",
            "multi_step_episodes": "All tasks support intel gathering before terminal decision",
            "levenshtein_grading": "Cover story matching uses Levenshtein similarity",
            "negation_filtering": "Keywords in negated context are filtered from scoring",
            "report_reference_scoring": "Reasoning that references case-specific details scores higher",
            "false_positive_penalty": "Classifying legitimate as covert is penalized heavily",
            "intel_gathering_bonus": "Agents that gather intel before deciding get a score bonus",
        },
    }


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {"task_id": 1, "name": "False Alarm Detection", "difficulty": "easy", "description": "Classify satellite reports as genuine threats or false alarms. Use 'request_context' for additional intel before deciding.", "actions": ["ignore", "flag_for_review", "request_context"], "cases": "procedural", "multi_step": True},
            {"task_id": 2, "name": "Threat Classification", "difficulty": "medium", "description": "Identify threat type and rate severity on a 1-10 scale. Use 'request_analysis' for detailed sensor data first.", "actions": ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity", "request_analysis"], "cases": "procedural", "multi_step": True},
            {"task_id": 3, "name": "Multi-Zone Drone Allocation", "difficulty": "hard", "description": "Analyze multiple sectors and deploy surveillance drone to highest priority threat. Investigate sectors before committing.", "actions": ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c", "investigate_sector_a", "investigate_sector_b", "investigate_sector_c"], "cases": "procedural", "multi_step": True},
            {"task_id": 4, "name": "Covert Operation Detection", "difficulty": "ultra", "description": "Identify facilities using civilian cover stories to hide military activity. Includes red-herring cases. Use 'request_verification' for SIGINT.", "actions": ["covert_operation", "legitimate_activity", "request_verification"], "cases": "procedural", "multi_step": True},
        ]
    }


@app.post("/reset")
def reset(req: Optional[ResetRequest] = None):
    try:
        if req is None:
            req = ResetRequest()
        session_id = req.session_id or str(uuid.uuid4())
        env = get_env(session_id)
        result = env.reset(
            task_id=req.task_id,
            seed=req.seed,
            split=req.split,
        )
        result["session_id"] = session_id
        return result
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] /reset failed: {e}\n{tb}", flush=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "traceback": tb}
        )


@app.post("/step")
def step(req: StepRequest):
    try:
        if not req.session_id or req.session_id not in _sessions:
            raise HTTPException(status_code=400, detail="Invalid or missing session_id. Call /reset first.")

        env = get_env(req.session_id)

        action_input = {
            "action": req.action,
            "threat_level": req.threat_level,
            "target_sector": req.target_sector,
            "reasoning": req.reasoning,
            "cover_story_identified": req.cover_story_identified,
            "deception_type": req.deception_type,
        }

        result = env.step(action_input)
        result["session_id"] = req.session_id
        return result
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] /step failed: {e}\n{tb}", flush=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "traceback": tb}
        )


@app.get("/state")
def state(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=400, detail="Invalid session_id. Call /reset first.")
    env = get_env(session_id)
    return env.state()


@app.post("/state")
def state_post(req: StateRequest):
    if req.session_id not in _sessions:
        raise HTTPException(status_code=400, detail="Invalid session_id. Call /reset first.")
    env = get_env(req.session_id)
    return env.state()


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
        return {"deleted": True, "session_id": session_id}
    return {"deleted": False, "session_id": session_id}


@app.get("/")
def root():
    return FileResponse("static/landing.html")

@app.get("/dashboard")
def dashboard():
    return FileResponse("static/index.html")


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
