import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src/geoshield')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid

from src.geoshield.server.environment import GeoShieldEnvironment

app = FastAPI(
    title="GeoShield Environment API",
    description="OpenEnv-compliant satellite intelligence triage environment for RL agent training.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session store ─────────────────────────────────────────────────────────────
# Each session_id maps to its own environment instance
_sessions: Dict[str, GeoShieldEnvironment] = {}

def get_env(session_id: str) -> GeoShieldEnvironment:
    if session_id not in _sessions:
        _sessions[session_id] = GeoShieldEnvironment()
    return _sessions[session_id]


# ── Request / Response models ─────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: int = 1
    seed: Optional[int] = None
    split: str = "train"
    session_id: Optional[str] = None

class StepRequest(BaseModel):
    action: str
    threat_level: Optional[int] = None
    target_sector: Optional[str] = None
    reasoning: Optional[str] = None
    session_id: Optional[str] = None

class StateRequest(BaseModel):
    session_id: Optional[str] = None


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "GeoShield",
        "version": "1.0.0",
        "description": "Satellite intelligence triage OpenEnv environment",
        "endpoints": ["/reset", "/step", "/state", "/info", "/health"],
        "tasks": {
            "1": "False Alarm Detection (easy)",
            "2": "Threat Classification & Severity (medium)",
            "3": "Multi-Zone Drone Allocation (hard)",
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}


# ── OpenEnv core endpoints ────────────────────────────────────────────────────

@app.post("/reset")
def reset(req: ResetRequest = None):
    if req is None:
        req = ResetRequest()

    session_id = req.session_id or str(uuid.uuid4())
    env = get_env(session_id)

    # Validate task_id
    if req.task_id not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="task_id must be 1, 2, or 3")

    # Validate split
    if req.split not in ["train", "eval"]:
        raise HTTPException(status_code=400, detail="split must be 'train' or 'eval'")

    result = env.reset(
        task_id=req.task_id,
        seed=req.seed,
        split=req.split,
    )

    result["session_id"] = session_id
    return result


@app.post("/step")
def step(req: StepRequest):
    session_id = req.session_id or "default"
    env = get_env(session_id)

    action_data = {
        "action": req.action,
        "threat_level": req.threat_level,
        "target_sector": req.target_sector,
        "reasoning": req.reasoning,
    }

    result = env.step(action_data)
    result["session_id"] = session_id
    return result


@app.post("/state")
def state(req: StateRequest = None):
    if req is None:
        req = StateRequest()

    session_id = req.session_id or "default"
    env = get_env(session_id)
    return env.get_state()


@app.get("/state")
def state_get(session_id: str = "default"):
    env = get_env(session_id)
    return env.get_state()


# ── Info endpoint ─────────────────────────────────────────────────────────────

@app.get("/info")
def info():
    return {
        "name": "GeoShield",
        "version": "1.0.0",
        "tasks": [
            {
                "task_id": 1,
                "name": "false_alarm_detection",
                "description": "Classify satellite report as ignore or flag_for_review",
                "difficulty": "easy",
                "actions": ["ignore", "flag_for_review"],
                "max_steps": 2,
                "reward_range": [0.01, 0.99],
            },
            {
                "task_id": 2,
                "name": "threat_classification",
                "description": "Classify anomaly type and assign threat level 1-10",
                "difficulty": "medium",
                "actions": ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity"],
                "max_steps": 3,
                "reward_range": [0.01, 0.99],
            },
            {
                "task_id": 3,
                "name": "drone_allocation",
                "description": "Deploy one drone to the highest priority sector with strategic reasoning",
                "difficulty": "hard",
                "actions": ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c"],
                "max_steps": 4,
                "reward_range": [0.01, 0.99],
            },
        ],
        "observation_space": {
            "task_id": "int",
            "case_id": "str",
            "step": "int",
            "difficulty": "str (easy|medium|hard)",
            "report": "str (Task 1 & 2)",
            "context": "str (Task 1 & 2)",
            "sectors": "List[SectorReport] (Task 3)",
            "available_actions": "List[str]",
            "available_assets": "str (Task 3)",
            "hint": "str",
        },
        "action_space": {
            "action": "str (required)",
            "threat_level": "int 1-10 (Task 2 only)",
            "target_sector": "str (Task 3 only)",
            "reasoning": "str (Task 3 only, strongly recommended)",
        },
        "reward": {
            "range": "[0.01, 0.99]",
            "task1": "Binary: 0.99 correct, 0.01 incorrect",
            "task2": "Partial: 0.5 classification + 0.5 threat level proximity",
            "task3": "Partial: 0.5 sector selection + 0.5 reasoning quality",
        }
    }


# ── Tasks listing ─────────────────────────────────────────────────────────────

@app.get("/tasks")
def tasks():
    return {
        "tasks": [
            {"id": 1, "name": "false_alarm_detection", "difficulty": "easy"},
            {"id": 2, "name": "threat_classification", "difficulty": "medium"},
            {"id": 3, "name": "drone_allocation", "difficulty": "hard"},
        ]
    }


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
