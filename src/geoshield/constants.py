"""
GeoShield Constants — Task configurations, keywords, and validation rules.
"""

from typing import List

TASK_ACTIONS = {
    1: ["ignore", "flag_for_review", "request_context"],
    2: ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity", "request_analysis"],
    3: ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c",
        "investigate_sector_a", "investigate_sector_b", "investigate_sector_c"],
    4: ["covert_operation", "legitimate_activity", "request_verification"],
}

MAX_STEPS = {
    1: 2,
    2: 3,
    3: 6,
    4: 4,
}

TASK_NAMES = {
    1: "false_alarm_detection",
    2: "threat_classification",
    3: "drone_allocation",
    4: "covert_operation_detection",
}

DIFFICULTY_WEIGHTS = {
    "easy": 0.98,
    "medium": 1.5,
    "hard": 2.0,
    "ultra": 3.0,
}

STRATEGIC_KEYWORDS = [
    "threat", "priority", "risk", "intelligence", "reconnaissance",
    "confirm", "verify", "assess", "sector", "deploy", "critical",
    "immediate", "strategic", "tactical", "covert", "deception",
    "cover", "legitimate", "suspicious", "anomaly", "pattern",
    "military", "weapons", "surveillance", "detection", "confidence",
    "perimeter", "fortification", "concealment", "infiltration",
]

# Valid gold actions per task — used for defensive validation
VALID_GOLD_ACTIONS = {
    1: ["ignore", "flag_for_review"],
    2: ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity"],
    3: ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c"],
    4: ["covert_operation", "legitimate_activity"],
}

DEFAULT_GOLD_ACTIONS = {
    1: "ignore",
    2: "civilian_activity",
    3: "deploy_to_sector_a",
    4: "legitimate_activity",
}
