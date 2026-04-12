"""
GeoShield Procedural Case Generator — Template-based case synthesis.

Generates unlimited unique cases from parameterized templates with
deterministic seed control. Each seed maps to exactly one case,
guaranteeing reproducibility across runs.

Design:
  • Templates compose report fragments from pools of locations, actors,
    anomalies, and threat indicators
  • Geographic coordinates are generated within realistic border-region ranges
  • Timestamps are distributed across a 24-hour operational window
  • Difficulty is assigned based on template ambiguity level
  • All gold labels are deterministically derived from template parameters
"""

import random
import hashlib
from typing import Dict, Any, List, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED TEMPLATE POOLS
# ═══════════════════════════════════════════════════════════════════════════════

REGIONS = [
    "Northern Border Zone Alpha", "Eastern Coastal Sector", "Southern Mountain Range",
    "Western Desert Corridor", "Central Plains Observatory", "Northeast Peninsula",
    "Southeast Jungle Perimeter", "Northwest Tundra Strip", "Southwest Canyon Network",
    "Midlands River Basin", "Highland Plateau Zone", "Lowland Marsh Sector",
    "Volcanic Ridge Outpost", "Steppe Border Station", "Island Chain Perimeter",
    "Arctic Monitoring Post", "Tropical Littoral Zone", "Arid Wasteland Sector",
    "Temperate Forest Line", "Glacial Valley Corridor",
]

FACILITY_NAMES = [
    "MediCorp Ltd", "AgroTech Industries", "SunPower Solutions", "CloudCore Technologies",
    "SecureForce Training", "GreenCircuit Recycling", "FastFashion Manufacturing",
    "TeleStar Communications", "BioFuel Energy Co", "AquaPure Water Systems",
    "NovaChem Laboratories", "PetroDyne Extraction", "LogiTrack Shipping",
    "EduBuild Foundation", "CyberVault Security", "FreshHarvest Co-op",
    "AutoTech Services", "GoldenHop Brewery", "PrintMaster Ltd", "HomeCraft Furniture",
    "SteelFrame Construction", "SwiftDeliver Technologies", "NutriPack Foods",
    "GreenFuel Bio", "DailyBread Bakeries", "ElectraGrid Power",
    "OceanDeep Marine", "SkyBridge Aviation", "TerraForm Mining", "QuantumLeap Research",
]

CIVILIAN_ACTIVITIES = [
    "agricultural machinery", "fishing boats", "school buses", "livestock market",
    "religious ceremony", "construction crane", "solar panel installation",
    "wind turbine installation", "marathon race", "power line maintenance",
    "oil pipeline inspection", "hospital expansion", "forest fire response",
    "weather station readings", "geological survey", "road construction",
    "bridge repair", "dam inspection", "railway maintenance", "port loading operations",
]

THREAT_INDICATORS_MILITARY = [
    "armored vehicles detected", "camouflage netting deployed", "military-grade radar",
    "encrypted radio transmissions", "troop formations observed", "weapons storage detected",
    "fortified perimeter constructed", "anti-aircraft systems", "artillery positioning",
    "night vision equipment detected", "command post infrastructure", "ammunition depot",
    "signals intelligence equipment", "drone launch systems", "mine-laying activity",
    "sniper positions identified", "armored personnel carriers", "mobile missile launchers",
    "electronic warfare systems", "military helicopter landing zone",
]

THREAT_INDICATORS_COVERT = [
    "power consumption exceeds declared capacity by 500%",
    "underground construction detected via seismic sensors",
    "chemical precursors inconsistent with declared products",
    "military-grade access control and biometric security",
    "encrypted communications on non-commercial frequencies",
    "blast-resistant construction not standard for declared use",
    "visitors include known defense ministry officials",
    "shipping manifests show weight 3x declared cargo",
    "Faraday cage shielding detected in commercial building",
    "workers have confirmed military backgrounds",
    "production schedule aligns with known procurement timelines",
    "equipment exceeds civilian specifications by order of magnitude",
    "underground tunnel network extends beyond property boundary",
    "secondary hidden facility detected beneath primary structure",
    "nighttime activity increases 400% after declared closing hours",
    "raw materials sourced from sanctioned military suppliers",
    "security perimeter matches military installation spec",
    "exhaust signatures inconsistent with declared industrial process",
    "satellite imagery shows systematic deception in facility layout",
    "radiation signatures detected inconsistent with declared purpose",
]

INNOCENT_EXPLANATIONS = [
    "registered with local municipal authority",
    "valid environmental permits on file",
    "consistent with seasonal activity patterns",
    "matches registered commercial operation profile",
    "standard equipment for declared industry",
    "workforce verified through labor ministry records",
    "activity aligns with published business schedule",
    "construction permits filed with planning authority",
    "routine maintenance consistent with industry standards",
    "matches known civilian infrastructure patterns",
]

COVER_STORIES = [
    ("pharmaceutical manufacturing facility", "research_weapons"),
    ("agricultural cooperative and storage", "logistics_supply"),
    ("solar energy installation company", "civilian_military"),
    ("telecommunications network provider", "civilian_military"),
    ("university research department", "research_weapons"),
    ("private security training academy", "civilian_military"),
    ("electronics recycling facility", "commercial_weapons"),
    ("textile manufacturing complex", "commercial_weapons"),
    ("cement quarry and processing plant", "construction_fortification"),
    ("data center and cloud services", "civilian_military"),
    ("water treatment and distribution", "research_weapons"),
    ("automotive repair and parts depot", "commercial_weapons"),
    ("biofuel production facility", "research_weapons"),
    ("drone logistics and delivery hub", "civilian_military"),
    ("mining and mineral extraction", "construction_fortification"),
    ("chemical cleaning products plant", "commercial_weapons"),
    ("satellite ground tracking station", "civilian_military"),
    ("food processing and canning plant", "logistics_supply"),
    ("commercial shipping terminal", "logistics_supply"),
    ("waste management and recycling", "construction_fortification"),
]

ANOMALY_TYPES = [
    "troop_movement", "illegal_construction", "unauthorized_aircraft",
    "weapons_cache", "civilian_activity",
]


def _proc_seed(task_id: int, seed: int) -> random.Random:
    """Create a deterministic RNG from task_id + seed."""
    h = hashlib.sha256(f"geoshield_t{task_id}_s{seed}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def _gen_coords(rng: random.Random) -> str:
    lat = round(rng.uniform(8.0, 72.0), 4)
    lon = round(rng.uniform(20.0, 140.0), 4)
    lat_d = "N" if lat >= 0 else "S"
    lon_d = "E" if lon >= 0 else "W"
    return f"{abs(lat):.4f}°{lat_d}, {abs(lon):.4f}°{lon_d}"


def _gen_timestamp(rng: random.Random) -> str:
    h = rng.randint(0, 23)
    m = rng.randint(0, 59)
    return f"{h:02d}:{m:02d}Z"


def _gen_sector_id(rng: random.Random) -> int:
    return rng.randint(1, 99)


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 1 — False Alarm Detection (Procedural)
# ═══════════════════════════════════════════════════════════════════════════════

_T1_FALSE_ALARM_TEMPLATES = [
    "Satellite scan — Sector {sector}: {civilian_activity} detected in {region}. {innocent}. No military signatures.",
    "Satellite scan — Sector {sector}: Thermal signatures consistent with {civilian_activity} in {region}. {innocent}.",
    "Satellite scan — Sector {sector}: Movement detected in {region}. Analysis confirms {civilian_activity}. {innocent}.",
    "Satellite scan — Sector {sector}: Activity spike in {region}. Pattern matches known {civilian_activity}. {innocent}.",
    "Satellite scan — Sector {sector}: Automated alert triggered in {region}. Investigation reveals {civilian_activity}. {innocent}.",
]

_T1_THREAT_TEMPLATES = [
    "Satellite scan — Sector {sector}: {threat_indicator} in {region}. Unregistered activity. No civilian explanation. Night operation confirmed.",
    "Satellite scan — Sector {sector}: Anomalous activity in {region}. {threat_indicator}. Pattern inconsistent with civilian use. No permits on file.",
    "Satellite scan — Sector {sector}: High-confidence alert — {threat_indicator} detected in {region}. Location has no registered civilian purpose.",
    "Satellite scan — Sector {sector}: Unauthorized {threat_indicator} in {region}. Activity commenced at 0300 hours. No advance notification filed.",
    "Satellite scan — Sector {sector}: Intelligence confirms {threat_indicator} in {region}. Rapid deployment pattern. Attempting concealment.",
]

# Medium difficulty: ambiguous cases with mixed signals
_T1_AMBIGUOUS_TEMPLATES = [
    "Satellite scan — Sector {sector}: Activity in {region} initially resembles {civilian_activity}, but {threat_indicator}. Further assessment needed.",
    "Satellite scan — Sector {sector}: {region} shows mixed signals. Primary pattern suggests {civilian_activity}, however anomalous {threat_indicator} detected in adjacent grid.",
    "Satellite scan — Sector {sector}: Unusual timing for {civilian_activity} in {region}. Equipment scale exceeds normal parameters. {threat_indicator} cannot be ruled out.",
]


def generate_task1(seed: int) -> Dict[str, Any]:
    rng = _proc_seed(1, seed)
    sector = _gen_sector_id(rng)
    coords = _gen_coords(rng)
    ts = _gen_timestamp(rng)
    region = rng.choice(REGIONS)

    roll = rng.random()
    if roll < 0.40:
        # False alarm — easy
        template = rng.choice(_T1_FALSE_ALARM_TEMPLATES)
        report = template.format(
            sector=sector,
            civilian_activity=rng.choice(CIVILIAN_ACTIVITIES),
            region=region,
            innocent=rng.choice(INNOCENT_EXPLANATIONS),
        )
        context = f"{region}, daytime patrol, coordinates {coords}, timestamp {ts}"
        return {
            "id": f"t1_proc_{seed}", "task": 1, "report": report,
            "context": context, "gold_action": "ignore", "difficulty": "easy",
            "category": "false_alarm", "coordinates": coords, "timestamp": ts,
            "additional_context": f"Routine monitoring cycle. {rng.choice(INNOCENT_EXPLANATIONS)}.",
            "hint": "Classify this satellite report as 'ignore' or 'flag_for_review'. You may 'request_context' for additional intel first.",
        }
    elif roll < 0.75:
        # Real threat — easy/medium
        template = rng.choice(_T1_THREAT_TEMPLATES)
        indicator = rng.choice(THREAT_INDICATORS_MILITARY)
        report = template.format(
            sector=sector, threat_indicator=indicator, region=region,
        )
        difficulty = rng.choice(["easy", "medium"])
        context = f"{region}, elevated threat level, coordinates {coords}, timestamp {ts}"
        return {
            "id": f"t1_proc_{seed}", "task": 1, "report": report,
            "context": context, "gold_action": "flag_for_review",
            "difficulty": difficulty, "category": "real_threat",
            "coordinates": coords, "timestamp": ts,
            "additional_context": f"Intelligence confirms prior activity in this region. {indicator} aligns with known threat patterns.",
            "hint": "Classify this satellite report as 'ignore' or 'flag_for_review'. You may 'request_context' for additional intel first.",
        }
    else:
        # Ambiguous — hard
        template = rng.choice(_T1_AMBIGUOUS_TEMPLATES)
        report = template.format(
            sector=sector,
            civilian_activity=rng.choice(CIVILIAN_ACTIVITIES),
            threat_indicator=rng.choice(THREAT_INDICATORS_MILITARY),
            region=region,
        )
        gold = rng.choice(["flag_for_review", "flag_for_review", "ignore"])  # Bias toward flag
        context = f"{region}, mixed signals, coordinates {coords}, timestamp {ts}"
        return {
            "id": f"t1_proc_{seed}", "task": 1, "report": report,
            "context": context, "gold_action": gold,
            "difficulty": "hard", "category": "ambiguous",
            "coordinates": coords, "timestamp": ts,
            "additional_context": f"Historical records show intermittent activity in this zone. Classification requires careful signal analysis.",
            "hint": "Classify this satellite report as 'ignore' or 'flag_for_review'. You may 'request_context' for additional intel first.",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Threat Classification & Severity (Procedural)
# ═══════════════════════════════════════════════════════════════════════════════

_T2_TEMPLATES = {
    "troop_movement": [
        "Intelligence Report — Sector {sector}: {count} military vehicles detected moving in convoy formation through {region}. {detail}. Speed consistent with tactical deployment.",
        "Intelligence Report — Sector {sector}: Infantry formations observed in {region}. Approximately {count} personnel in tactical gear. {detail}.",
        "Intelligence Report — Sector {sector}: Armored column detected advancing through {region}. {count} vehicles identified. {detail}. Movement heading toward border.",
    ],
    "illegal_construction": [
        "Intelligence Report — Sector {sector}: Unauthorized construction activity in {region}. {detail}. No civilian permits on record. {count} workers on site.",
        "Intelligence Report — Sector {sector}: Rapid construction of fortified structure in {region}. {detail}. Reinforced concrete dimensions inconsistent with civilian use.",
        "Intelligence Report — Sector {sector}: Underground excavation detected in {region}. {detail}. Pattern matches military bunker specifications. {count} dump trucks observed.",
    ],
    "unauthorized_aircraft": [
        "Intelligence Report — Sector {sector}: Unregistered aircraft detected in {region} airspace. {detail}. No flight plan filed. {count} craft observed.",
        "Intelligence Report — Sector {sector}: Low-altitude drone swarm in {region}. {count} UAVs in coordinated formation. {detail}. Military-grade flight patterns.",
        "Intelligence Report — Sector {sector}: Helicopter operations in restricted airspace over {region}. {detail}. {count} rotary aircraft, no markings visible.",
    ],
    "weapons_cache": [
        "Intelligence Report — Sector {sector}: Suspected weapons storage detected in {region}. {detail}. {count} crates unloaded from unmarked trucks at night.",
        "Intelligence Report — Sector {sector}: Ammunition depot signatures in {region}. {detail}. Blast-proof construction with {count} protected storage units.",
        "Intelligence Report — Sector {sector}: Arms cache indicators in {region}. {detail}. Underground vault with {count} separate compartments detected.",
    ],
    "civilian_activity": [
        "Intelligence Report — Sector {sector}: Commercial activity detected in {region}. {detail}. {count} civilian vehicles with registered plates. Normal operations confirmed.",
        "Intelligence Report — Sector {sector}: Routine civilian operations in {region}. {detail}. All {count} personnel identified as registered workers. No anomalies.",
        "Intelligence Report — Sector {sector}: Agricultural operations in {region}. {detail}. {count} farming vehicles. Activity matches seasonal patterns.",
    ],
}

_T2_DETAILS = {
    "troop_movement": [
        "Night vision equipment and encrypted communications detected",
        "Supply trucks and mobile command post accompanying the column",
        "Soldiers carrying heavy weapons, tactical formation",
        "Combat engineering vehicles and mine-clearing equipment present",
        "Air defense systems integrated into convoy",
    ],
    "illegal_construction": [
        "Blast-resistant walls being erected in rapid timeline",
        "Tunnel entrance detected via ground-penetrating radar",
        "Reinforced observation posts with line-of-sight to border",
        "Camouflage netting being deployed over construction area",
        "Anti-surveillance measures — reflective coating on walls",
    ],
    "unauthorized_aircraft": [
        "Electronic warfare signatures detected from aircraft",
        "Aircraft carrying external payloads inconsistent with civilian use",
        "Formation flying patterns match military reconnaissance doctrine",
        "Autopilot signatures consistent with armed drone platforms",
        "Jamming of local radar detected during flight window",
    ],
    "weapons_cache": [
        "Radiation signatures suggest fissile material presence",
        "Chemical agent containment vessels detected",
        "Anti-tampering devices on storage containers",
        "Armed guards with military-grade equipment on perimeter",
        "Temperature-controlled storage consistent with explosive ordinance",
    ],
    "civilian_activity": [
        "Workers wearing standard safety equipment for declared industry",
        "Vehicles display valid commercial registration and insurance",
        "Activity level consistent with declared business operations",
        "No restricted materials or equipment detected on site",
        "Schedule matches normal business hours and seasonal patterns",
    ],
}

_T2_THREAT_LEVELS = {
    "troop_movement": (5, 9),
    "illegal_construction": (3, 7),
    "unauthorized_aircraft": (4, 8),
    "weapons_cache": (6, 10),
    "civilian_activity": (1, 3),
}

_T2_ANALYSIS_DETAILS = {
    "troop_movement": "Spectral analysis confirms military-grade vehicle thermal signatures. Movement vector analysis indicates offensive positioning.",
    "illegal_construction": "Subsurface radar confirms reinforced structures at depth inconsistent with civilian construction. Material composition analysis pending.",
    "unauthorized_aircraft": "Radar cross-section analysis identifies non-civilian airframe characteristics. Electronic emissions match known military platforms.",
    "weapons_cache": "Chemical spectroscopy detects trace explosive compounds in air samples. Thermal anomalies consistent with active storage systems.",
    "civilian_activity": "All signatures consistent with declared commercial operations. No anomalous readings detected in any sensor band.",
}


def generate_task2(seed: int) -> Dict[str, Any]:
    rng = _proc_seed(2, seed)
    sector = _gen_sector_id(rng)
    coords = _gen_coords(rng)
    ts = _gen_timestamp(rng)
    region = rng.choice(REGIONS)

    threat_type = rng.choice(ANOMALY_TYPES)
    templates = _T2_TEMPLATES[threat_type]
    details = _T2_DETAILS[threat_type]
    level_range = _T2_THREAT_LEVELS[threat_type]

    count = rng.randint(2, 30)
    template = rng.choice(templates)
    detail = rng.choice(details)
    threat_level = rng.randint(*level_range)

    report = template.format(sector=sector, region=region, detail=detail, count=count)
    difficulty = "easy" if threat_type == "civilian_activity" else rng.choice(["medium", "medium", "hard"])
    context = f"{region}, threat assessment required, coordinates {coords}, timestamp {ts}"

    return {
        "id": f"t2_proc_{seed}", "task": 2, "report": report,
        "context": context, "gold_action": threat_type,
        "gold_threat_level": threat_level, "difficulty": difficulty,
        "category": threat_type, "coordinates": coords, "timestamp": ts,
        "analysis_detail": _T2_ANALYSIS_DETAILS.get(threat_type, "Analysis pending."),
        "hint": "Identify the threat type and rate its severity (1-10). You may 'request_analysis' for detailed sensor data first.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 3 — Multi-Zone Drone Allocation (Procedural)
# ═══════════════════════════════════════════════════════════════════════════════

_T3_SECTOR_SUMMARIES = {
    "high_threat": [
        "Armed convoy of {count} vehicles advancing toward border crossing. Military-grade equipment confirmed.",
        "Confirmed weapons cache being distributed. {count} armed personnel. Active loading operations.",
        "Missile launch preparations detected. {count} systems being erected. Countdown infrastructure active.",
        "Special forces unit of {count} operators conducting covert breach of perimeter fence.",
        "Mass troop staging area with {count} personnel. Field hospital and command post established.",
    ],
    "medium_threat": [
        "Suspicious vehicle movement — {count} unmarked trucks on unpaved roads at night.",
        "Construction activity not matching permits — {count} workers, possible observation post.",
        "Unidentified drone flights — {count} small UAVs, flight path along border. Purpose unknown.",
        "Unusual radio emissions from abandoned building. {count} antenna arrays newly installed.",
        "Small boat activity near restricted waterway — {count} vessels, no navigation lights.",
    ],
    "low_threat": [
        "Civilian farming equipment operating in fields. {count} tractors visible. Normal seasonal activity.",
        "Registered fishing vessels in authorized waters. {count} boats with valid markings.",
        "School transport detected — {count} buses on registered route during normal hours.",
        "Commercial delivery vehicles on public road. {count} trucks with visible company branding.",
        "Weather station maintenance crew — {count} workers with utility company vehicles.",
    ],
}


def generate_task3(seed: int) -> Dict[str, Any]:
    rng = _proc_seed(3, seed)
    coords_a = _gen_coords(rng)
    coords_b = _gen_coords(rng)
    coords_c = _gen_coords(rng)
    ts = _gen_timestamp(rng)

    # Deterministically assign priority: one high, one medium, one low
    priority_order = ["high_threat", "medium_threat", "low_threat"]
    rng.shuffle(priority_order)

    sectors = []
    gold_sector = None
    second_best = None

    for i, (sid, priority) in enumerate(zip(["sector_a", "sector_b", "sector_c"], priority_order)):
        count = rng.randint(3, 25)
        summary = rng.choice(_T3_SECTOR_SUMMARIES[priority]).format(count=count)

        anomaly_map = {
            "high_threat": rng.choice(["troop_movement", "weapons_cache", "unauthorized_aircraft"]),
            "medium_threat": rng.choice(["illegal_construction", "unauthorized_aircraft", "troop_movement"]),
            "low_threat": "civilian_activity",
        }
        conf_map = {
            "high_threat": round(rng.uniform(0.80, 0.98), 2),
            "medium_threat": round(rng.uniform(0.45, 0.70), 2),
            "low_threat": round(rng.uniform(0.10, 0.35), 2),
        }

        coord = [coords_a, coords_b, coords_c][i]

        sectors.append({
            "sector_id": sid,
            "summary": summary,
            "anomaly_type": anomaly_map[priority],
            "confidence": conf_map[priority],
            "coordinates": coord,
            "timestamp": ts,
        })

        if priority == "high_threat":
            gold_sector = f"deploy_to_{sid}"
        elif priority == "medium_threat":
            second_best = f"deploy_to_{sid}"

    return {
        "id": f"t3_proc_{seed}", "task": 3, "gold_action": gold_sector,
        "second_best_sector": second_best, "difficulty": "hard",
        "sectors": sectors, "available_assets": "1 surveillance drone",
        "coordinates": coords_a, "timestamp": ts,
        "hint": "Analyze all sectors and deploy your drone to the highest priority threat. You may investigate one sector first.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 4 — Covert Operation Detection (Procedural)
# ═══════════════════════════════════════════════════════════════════════════════

_T4_REPORT_TEMPLATES_COVERT = [
    "Intelligence Report — Sector {sector}: {facility_type} detected near {region}. {equipment}. Company registered as {company}. {worker_count} workers on site.",
    "Intelligence Report — Sector {sector}: {company} operating {facility_type} in {region}. {equipment}. Satellite imagery shows {worker_count} personnel.",
    "Intelligence Report — Sector {sector}: Large-scale {facility_type} identified in {region}. Operated by {company} with {worker_count} staff. {equipment}.",
]

_T4_REPORT_TEMPLATES_LEGIT = [
    "Intelligence Report — Sector {sector}: {facility_type} operating in {region}. Standard {equipment}. Registered as {company} with valid permits. {worker_count} employees.",
    "Intelligence Report — Sector {sector}: {company} confirmed operating {facility_type} in {region}. {equipment}. All certifications current. {worker_count} workers verified.",
    "Intelligence Report — Sector {sector}: Routine monitoring of {facility_type} in {region}. {company} holds valid licenses. {equipment}. {worker_count} personnel consistent with declared operations.",
]

# RED HERRING templates — look suspicious but are legitimate
_T4_REPORT_TEMPLATES_RED_HERRING = [
    "Intelligence Report — Sector {sector}: {facility_type} in {region} shows unusual activity patterns. {company} operations include {equipment}. {worker_count} workers, some with unusual schedules. However, {innocent_explanation}.",
    "Intelligence Report — Sector {sector}: {company} operating {facility_type} in {region}. Initial scan flagged {equipment}. {worker_count} personnel. Deeper analysis reveals {innocent_explanation}.",
]


def generate_task4(seed: int) -> Dict[str, Any]:
    rng = _proc_seed(4, seed)
    sector = _gen_sector_id(rng)
    coords = _gen_coords(rng)
    ts = _gen_timestamp(rng)
    region = rng.choice(REGIONS)
    company = rng.choice(FACILITY_NAMES)
    worker_count = rng.randint(50, 800)

    roll = rng.random()

    if roll < 0.40:
        # Covert operation — hard/ultra
        cover_story, deception_type = rng.choice(COVER_STORIES)
        facility_type = cover_story.split(" ")[0:3]
        facility_type = " ".join(facility_type) + " facility"
        equipment = rng.choice(THREAT_INDICATORS_COVERT[:10])

        # Pick 4 unique deception indicators
        indicators = rng.sample(THREAT_INDICATORS_COVERT, min(4, len(THREAT_INDICATORS_COVERT)))

        template = rng.choice(_T4_REPORT_TEMPLATES_COVERT)
        report = template.format(
            sector=sector, facility_type=facility_type, region=region,
            equipment=equipment, company=company, worker_count=worker_count,
        )
        difficulty = rng.choice(["hard", "ultra", "ultra"])
        context = f"{region}, intelligence assessment required, coordinates {coords}"

        return {
            "id": f"t4_proc_{seed}", "task": 4, "report": report,
            "context": context, "gold_action": "covert_operation",
            "gold_cover_story": cover_story, "gold_deception_type": deception_type,
            "deception_indicators": indicators, "difficulty": difficulty,
            "category": "covert", "coordinates": coords, "timestamp": ts,
            "cover_story": cover_story,
            "hint": "Determine if this facility is a covert operation or legitimate activity. You may 'request_verification' for additional SIGINT.",
        }

    elif roll < 0.70:
        # Legitimate activity — easy
        cover_story, _ = rng.choice(COVER_STORIES)
        facility_type = cover_story
        equipment = rng.choice(CIVILIAN_ACTIVITIES)

        template = rng.choice(_T4_REPORT_TEMPLATES_LEGIT)
        report = template.format(
            sector=sector, facility_type=facility_type, region=region,
            equipment=equipment, company=company, worker_count=worker_count,
        )
        context = f"{region}, routine monitoring, coordinates {coords}"

        return {
            "id": f"t4_proc_{seed}", "task": 4, "report": report,
            "context": context, "gold_action": "legitimate_activity",
            "gold_cover_story": cover_story, "gold_deception_type": "",
            "deception_indicators": [], "difficulty": "easy",
            "category": "civilian", "coordinates": coords, "timestamp": ts,
            "cover_story": cover_story,
            "hint": "Determine if this facility is a covert operation or legitimate activity. You may 'request_verification' for additional SIGINT.",
        }

    else:
        # RED HERRING — looks suspicious but is legitimate (ultra difficulty)
        cover_story, _ = rng.choice(COVER_STORIES)
        facility_type = cover_story
        equipment = rng.choice(THREAT_INDICATORS_COVERT[:8])
        innocent = rng.choice(INNOCENT_EXPLANATIONS)

        # Give some deception indicators that actually have innocent explanations
        red_herring_indicators = [
            f"{rng.choice(THREAT_INDICATORS_COVERT[:6])} — however {rng.choice(INNOCENT_EXPLANATIONS)}",
            f"Initial detection of {rng.choice(THREAT_INDICATORS_COVERT[:6])} later attributed to {rng.choice(CIVILIAN_ACTIVITIES)}",
        ]

        template = rng.choice(_T4_REPORT_TEMPLATES_RED_HERRING)
        report = template.format(
            sector=sector, facility_type=facility_type, region=region,
            equipment=equipment, company=company, worker_count=worker_count,
            innocent_explanation=innocent,
        )
        context = f"{region}, flagged for review but may be benign, coordinates {coords}"

        return {
            "id": f"t4_proc_{seed}", "task": 4, "report": report,
            "context": context, "gold_action": "legitimate_activity",
            "gold_cover_story": cover_story, "gold_deception_type": "",
            "deception_indicators": red_herring_indicators,
            "difficulty": "ultra",
            "category": "red_herring", "coordinates": coords, "timestamp": ts,
            "cover_story": cover_story,
            "hint": "Determine if this facility is a covert operation or legitimate activity. Beware of false positives. You may 'request_verification' for additional SIGINT.",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

PROCEDURAL_GENERATORS = {
    1: generate_task1,
    2: generate_task2,
    3: generate_task3,
    4: generate_task4,
}


def generate_procedural_case(task_id: int, seed: int) -> Dict[str, Any]:
    """Generate a single deterministic case from the procedural template system.

    Args:
        task_id: Task number (1-4)
        seed: Integer seed for deterministic generation

    Returns:
        Complete case dict ready for grading
    """
    generator = PROCEDURAL_GENERATORS.get(task_id)
    if generator is None:
        raise ValueError(f"No procedural generator for task {task_id}")
    return generator(seed)
