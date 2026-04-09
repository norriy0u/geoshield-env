import os
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

from src.geoshield.server.environment import GeoShieldEnvironment

app = FastAPI(
    title="GeoShield Environment API",
    description="OpenEnv-compliant satellite intelligence triage environment for RL agent training.",
    version="2.0.0",
)
from fastapi import Request
from fastapi.responses import JSONResponse
import json

def deep_clamp(obj):
    if isinstance(obj, dict):
        return {k: (round(max(0.01, min(0.99, float(v))), 4)
                    if k in ("score","reward","total_score","final_score") and isinstance(v, (int,float))
                    else deep_clamp(v))
                for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_clamp(i) for i in obj]
    return obj

@app.middleware("http")
async def clamp_scores_middleware(request: Request, call_next):
    response = await call_next(request)
    if response.headers.get("content-type","").startswith("application/json"):
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            data = json.loads(body)
            data = deep_clamp(data)
            return JSONResponse(content=data, status_code=response.status_code)
        except Exception:
            pass
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0", "tasks": [1, 2, 3, 4]}


@app.get("/info")
def info():
    return {
        "name": "GeoShield",
        "description": "Satellite intelligence triage OpenEnv environment",
        "version": "2.0.0",
        "tasks": {
            "1": {"name": "false_alarm_detection", "difficulty": "easy", "actions": ["ignore", "flag_for_review"]},
            "2": {"name": "threat_classification", "difficulty": "medium", "actions": ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity"]},
            "3": {"name": "drone_allocation", "difficulty": "hard", "actions": ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c", "investigate_sector_a", "investigate_sector_b", "investigate_sector_c"]},
            "4": {"name": "covert_operation_detection", "difficulty": "ultra", "actions": ["covert_operation", "legitimate_activity", "request_verification"]},
        },
        "reward_range": [0.01, 0.99],
        "splits": ["train", "eval"],
    }


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "task_id": 1,
                "name": "False Alarm Detection",
                "difficulty": "easy",
                "description": "Classify satellite reports as genuine threats or false alarms.",
                "actions": ["ignore", "flag_for_review"],
                "cases": 30,
            },
            {
                "task_id": 2,
                "name": "Threat Classification",
                "difficulty": "medium",
                "description": "Identify threat type and rate severity on a 1-10 scale.",
                "actions": ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity"],
                "cases": 30,
            },
            {
                "task_id": 3,
                "name": "Multi-Zone Drone Allocation",
                "difficulty": "hard",
                "description": "Analyze multiple sectors and deploy surveillance drone to highest priority threat. May investigate one sector before deploying.",
                "actions": ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c", "investigate_sector_a", "investigate_sector_b", "investigate_sector_c"],
                "cases": 30,
            },
            {
                "task_id": 4,
                "name": "Covert Operation Detection",
                "difficulty": "ultra",
                "description": "Identify facilities using civilian cover stories to hide military or weapons activity. Unmask the deception type and cover story.",
                "actions": ["covert_operation", "legitimate_activity", "request_verification"],
                "cases": 30,
            },
        ]
    }


@app.post("/reset")
def reset(req: Optional[ResetRequest] = None):
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

@app.post("/step")
def step(req: StepRequest):
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

    # Hard clamp at API boundary — validator requires strictly (0, 1)
    def _c(v):
        try: return round(max(0.01, min(0.99, float(v))), 4)
        except: return 0.01

    result["reward"] = _c(result.get("reward", 0.01))
    if "info" in result:
        if "total_score" in result["info"]:
            result["info"]["total_score"] = _c(result["info"]["total_score"])
    if "state" in result:
        if "total_score" in result.get("state", {}):
            result["state"]["total_score"] = _c(result["state"]["total_score"])

    return result

    result = env.step(action_input)
    result["session_id"] = req.session_id
    return result


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
    return {
        "name": "GeoShield",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "info": "/info",
        "tasks": "/tasks",
    }


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()