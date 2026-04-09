---
title: GeoShield
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
- openenv
---

# 🛡️ GeoShield — Satellite Intelligence Triage Environment

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compliant-blue)](https://huggingface.co/spaces/norriy0u/geoshield-env)
[![HuggingFace](https://img.shields.io/badge/HF-HuggingFace%20Space-yellow)](https://huggingface.co/spaces/norriy0u/geoshield-env)
[![Docker](https://img.shields.io/badge/Docker-ready-brightgreen)](./Dockerfile)

## Overview

GeoShield is a **real-world OpenEnv environment** where an AI agent acts as a **Defense Zone Commander**. The agent receives textual intelligence reports — simulating the output of a Vision-Language Model (like Meta's Llama Vision + SAM 2) analyzing satellite imagery — and must make fast, accurate strategic decisions.

This environment models a genuine operational challenge faced by modern defense analysts: processing high volumes of satellite intelligence, filtering false alarms, classifying threats, and allocating scarce reconnaissance assets across multiple simultaneous incidents.

---

## Motivation & Real-World Relevance

Borders and defense zones span thousands of kilometers of remote terrain. Human analysts suffer from fatigue, scale limitations, and cognitive overload when monitoring continuous satellite feeds.

**Real-world parallels:**
- **Project Maven** (Pentagon): AI system that scans drone and satellite footage to flag targets for human analysts
- **Palantir & Anduril**: Multi-billion dollar defense tech companies whose core product is taking sensor data (satellites, drones) and using AI to help commanders make fast decisions
- **NATO STANAG 3596**: Standard for imagery intelligence reporting that our observation format is modeled after

GeoShield trains agents to perform the **Strategic Command Interface** layer — the decision-making system that sits on top of vision models and converts raw intelligence into actionable commands.

---

## Environment Architecture
'''
Satellite Image
│
▼
[SAM 2 + Llama Vision] ← simulated by our data generators
│
▼
Text Intelligence Report
│
▼
[GeoShield Agent] ← THIS is what we train
│
▼
Strategic Decision (ignore / classify / deploy)
'''
---

## Tasks

### Task 1 — False Alarm Detection (Easy)
**Objective:** Classify satellite reports as false alarms or real threats.

| Field | Value |
|-------|-------|
| Difficulty | Easy |
| Max Steps | 2 |
| Actions | `ignore`, `flag_for_review` |
| Reward | Binary: 0.99 correct, 0.01 incorrect |

**Example observation:**
**Expected action:** `ignore`

---

### Task 2 — Threat Classification & Severity (Medium)
**Objective:** Classify the anomaly type AND assign a threat level from 1–10.

| Field | Value |
|-------|-------|
| Difficulty | Medium |
| Max Steps | 3 |
| Actions | `troop_movement`, `illegal_construction`, `unauthorized_aircraft`, `weapons_cache`, `civilian_activity` |
| Extra fields | `threat_level` (int 1–10) |
| Reward | Partial: 0.5 classification + 0.5 threat level proximity |

**Example observation:**
**Expected action:** `illegal_construction` with `threat_level: 7`

**Partial credit logic:**
- Exact classification match → 0.99 classification score
- Related classification (e.g. weapons_cache for troop_movement) → partial score
- Threat level within ±1 → 0.80 level score
- Threat level within ±2 → 0.60 level score

---

### Task 3 — Multi-Zone Drone Allocation (Hard)
- **Task 4** (Ultra): Covert Operation Detection � unmask facilities using civilian cover stories to hide weapons/military activity
**Objective:** Receive simultaneous reports from 3 sectors, deploy ONE drone to the highest priority sector, and explain the strategic reasoning.

| Field | Value |
|-------|-------|
| Difficulty | Hard |
| Max Steps | 4 |
| Actions | `deploy_to_sector_a`, `deploy_to_sector_b`, `deploy_to_sector_c` |
| Extra fields | `target_sector` (str), `reasoning` (str, min 100 chars) |
| Reward | 0.5 sector selection + 0.5 reasoning quality |

**Example observation:**
**Expected action:** `deploy_to_sector_b` with strategic reasoning paragraph

**Reasoning scoring:**
- Length > 20 chars → +0.10
- Length > 80 chars → +0.10
- Length > 150 chars → +0.10
- 3+ strategic keywords → +0.10
- 5+ strategic keywords → +0.10

This mechanic forces the agent to **think before acting** — mirroring real SOC analyst workflows where decisions must be documented.

---

## Observation Space

```python
class GeoObservation(BaseModel):
    task_id: int                          # 1, 2, or 3
    case_id: str                          # unique case identifier
    step: int                             # current step number
    difficulty: str                       # "easy" | "medium" | "hard"
    report: Optional[str]                 # intelligence report text (Task 1 & 2)
    context: Optional[str]                # situational context (Task 1 & 2)
    sectors: Optional[List[SectorReport]] # multi-sector reports (Task 3)
    available_actions: List[str]          # valid actions for this task
    available_assets: Optional[str]       # available assets (Task 3)
    hint: Optional[str]                   # task instruction hint
```

```python
class SectorReport(BaseModel):
    sector_id: str          # "sector_a" | "sector_b" | "sector_c"
    summary: str            # intelligence summary text
    anomaly_type: str       # detected anomaly category
    confidence: float       # detection confidence 0.0–1.0
    coordinates: str        # geographic coordinates
    timestamp: str          # UTC timestamp
```

---

## Action Space

```python
class GeoShieldAction(BaseModel):
    action: str                      # required — the primary decision
    threat_level: Optional[int]      # Task 2 only — severity 1-10
    target_sector: Optional[str]     # Task 3 only — chosen sector id
    reasoning: Optional[str]         # Task 3 only — strategic reasoning
```

**Task 1 valid actions:** `ignore`, `flag_for_review`

**Task 2 valid actions:** `troop_movement`, `illegal_construction`, `unauthorized_aircraft`, `weapons_cache`, `civilian_activity`

**Task 3 valid actions:** `deploy_to_sector_a`, `deploy_to_sector_b`, `deploy_to_sector_c`

---

## Reward Function

All rewards are strictly in **(0.01, 0.99)** — never exactly 0 or 1.

| Task | Reward Logic |
|------|-------------|
| Task 1 | Binary: 0.99 correct, 0.01 incorrect |
| Task 2 | 0.5 × classification score + 0.5 × threat level proximity score |
| Task 3 | 0.5 × sector selection + 0.5 × reasoning quality (length + keywords) |

**Step penalties:** Invalid actions receive 0.01 reward immediately.

**Early termination:** Episodes end early if reward ≥ 0.80 (high confidence correct answer).

---

## Baseline Scores

| Agent | Task 1 | Task 2 | Task 3 | Overall |
|-------|--------|--------|--------|---------|
| Random Agent | ~0.50 | ~0.30 | ~0.25 | ~0.35 |
| Rules Agent | ~0.75 | ~0.55 | ~0.55 | ~0.62 |
| LLM Agent (Qwen2.5-72B) | ~0.85 | ~0.70 | ~0.60 | ~0.72 |

Frontier models (GPT-4, Claude) expected to score ~0.90 on Task 1, ~0.80 on Task 2, ~0.65 on Task 3.

Task 3 is intentionally designed to challenge frontier models — the multi-sector ambiguous scenarios require genuine strategic reasoning that resists simple pattern matching.

---

## Setup & Usage

### Local Development

```bash
# Clone repo
git clone https://github.com/norriy0u/geoshield-env
cd geoshield-env

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Test endpoints
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1, "seed": 42}'

curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": "flag_for_review", "session_id": "<your_session_id>"}'
```

### Docker

```bash
# Build
docker build -t geoshield .

# Run
docker run -p 7860:7860 geoshield

# Test
curl -X POST http://localhost:7860/reset -d '{"task_id": 1}'
```

### Run Inference Script

```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_URL=http://localhost:7860

python inference.py
```

### Run Baselines

```bash
# Random agent
python baselines/random_agent.py

# Rules-based agent
python baselines/rules_agent.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset` | POST | Start new episode |
| `/step` | POST | Submit action, get reward |
| `/state` | POST/GET | Get current episode state |
| `/info` | GET | Full environment documentation |
| `/tasks` | GET | List all tasks |
| `/health` | GET | Health check |

### Reset Request
```json
{
  "task_id": 1,
  "seed": 42,
  "split": "train",
  "session_id": "optional-session-id"
}
```

### Step Request
```json
{
  "action": "flag_for_review",
  "threat_level": 8,
  "target_sector": "sector_b",
  "reasoning": "Strategic reasoning here...",
  "session_id": "your-session-id"
}
```

### Step Response
```json
{
  "observation": {...},
  "reward": 0.85,
  "done": true,
  "info": {
    "feedback": "Correct! 'flag_for_review' matches gold action.",
    "breakdown": {...},
    "step": 1,
    "total_score": 0.85
  }
}
```

---

## Project Structure
'''
geoshield-env/
├── Dockerfile
├── requirements.txt
├── openenv.yaml
├── pyproject.toml
├── README.md
├── inference.py
├── server/
│   └── app.py
├── src/
│   └── geoshield/
│       ├── init.py
│       ├── models.py
│       ├── constants.py
│       └── server/
│           ├── init.py
│           ├── environment.py
│           ├── graders.py
│           └── generators.py
├── data/
│   ├── task1_train.jsonl  (30 cases)
│   ├── task2_train.jsonl  (30 cases)
│   ├── task3_train.jsonl  (30 cases)
│   ├── task1_eval.jsonl   (30 cases)
│   ├── task2_eval.jsonl   (30 cases)
│   └── task3_eval.jsonl   (30 cases)
└── baselines/
├── random_agent.py
└── rules_agent.py
'''
---

## Data

180 total cases across 6 splits (3 tasks × train/eval × 30 cases each).

Each case includes:
- Realistic satellite intelligence report text
- Ground truth action and threat level
- Difficulty label (easy / medium / hard)
- Category label for analysis

Cases are designed so that:
- **Easy cases** are solvable by keyword matching
- **Medium cases** require contextual reasoning
- **Hard cases** involve deliberate ambiguity that challenges frontier LLMs

---

## References

- [Project Maven — Pentagon AI Program](https://www.defense.gov/News/Releases/)
- [NATO STANAG 3596 — Imagery Intelligence Standards](https://www.nato.int)
- [Meta SAM 2 — Segment Anything Model](https://ai.meta.com/sam2/)
- [OpenEnv Framework](https://huggingface.co/openenv)
- [Palantir AIP Defense](https://www.palantir.com/platforms/aip/)

---

## License

MIT License — open for research and agent evaluation use.






