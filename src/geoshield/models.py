from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# ── Actions ──────────────────────────────────────────────────────────────────

class GeoShieldAction(BaseModel):
    action: str
    threat_level: Optional[int] = None      # Task 2: 1-10
    target_sector: Optional[str] = None     # Task 3: which sector to deploy drone
    reasoning: Optional[str] = None         # Task 3: mandatory strategic reasoning


# ── Observations ─────────────────────────────────────────────────────────────

class SectorReport(BaseModel):
    sector_id: str
    summary: str
    anomaly_type: Optional[str] = None
    confidence: float = 0.0
    coordinates: Optional[str] = None
    timestamp: str = "00:00Z"

class GeoObservation(BaseModel):
    task_id: int
    case_id: str
    step: int = 0
    difficulty: str = "easy"
    # Task 1 & 2
    report: Optional[str] = None
    context: Optional[str] = None
    # Task 3 — multiple sectors
    sectors: Optional[List[SectorReport]] = None
    available_actions: List[str] = []
    available_assets: Optional[str] = None
    hint: Optional[str] = None


# ── Reward ────────────────────────────────────────────────────────────────────

class GeoReward(BaseModel):
    score: float
    feedback: str
    breakdown: Optional[Dict[str, Any]] = None


# ── State ─────────────────────────────────────────────────────────────────────

class GeoState(BaseModel):
    task_id: int
    case_id: str
    completed: bool
    step: int
    rewards: List[float] = []
    total_score: float = 0.0
    difficulty: str = "easy"
    current_observation: Optional[str] = None