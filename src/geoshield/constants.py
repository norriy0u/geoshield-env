TASK_ACTIONS = {
    1: ["ignore", "flag_for_review"],
    2: ["troop_movement", "illegal_construction", "unauthorized_aircraft", "weapons_cache", "civilian_activity"],
    3: ["deploy_to_sector_a", "deploy_to_sector_b", "deploy_to_sector_c"],
}

TASK_DESCRIPTIONS = {
    1: "False Alarm vs Real Threat — classify satellite report as ignore or flag_for_review",
    2: "Threat Classification & Severity — classify anomaly type and assign threat level 1-10",
    3: "Multi-Zone Drone Allocation — deploy one reconnaissance drone to highest priority sector",
}

TASK_NAMES = {
    1: "false_alarm_detection",
    2: "threat_classification",
    3: "drone_allocation",
}

MAX_STEPS = {1: 2, 2: 3, 3: 4}