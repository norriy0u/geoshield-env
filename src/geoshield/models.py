from pydantic import BaseModel, Field
from typing import Optional, List


class SectorReport(BaseModel):
    sector_id: str
    summary: str
    anomaly_type: Optional[str] = None
    confidence: float = 0.5
    coordinates: Optional[str] = None
    timestamp: str = "00:00Z"
    cover_story: Optional[str] = None
    deception_indicators: Optional[List[str]] = None


class GeoShieldAction(BaseModel):
    action: str
    threat_level: Optional[int] = None
    target_sector: Optional[str] = None
    reasoning: Optional[str] = None
    cover_story_identified: Optional[str] = None
    deception_type: Optional[str] = None


class GeoObservation(BaseModel):
    task_id: int
    case_id: str
    step: int
    difficulty: str
    report: Optional[str] = None
    context: Optional[str] = None
    sectors: Optional[List[SectorReport]] = None
    available_actions: List[str] = []
    available_assets: Optional[str] = None
    hint: Optional[str] = None
    investigation_results: Optional[dict] = None
    steps_remaining: Optional[int] = None
    deception_indicators: Optional[List[str]] = None


class GeoReward(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: str
    breakdown: dict = {}

    def model_post_init(self, __context):
        # Hard clamp: never touch 0.0 or 1.0 boundaries
        self.score = round(max(0.02, min(0.98, float(self.score))), 4)


class GeoState(BaseModel):
    task_id: int
    case_id: str
    completed: bool = False
    step: int = 0
    rewards: List[float] = []
    total_score: float = 0.02
    difficulty: str = "easy"
    current_observation: Optional[str] = None
    investigation_used: bool = False
    drone_deployed: bool = False
