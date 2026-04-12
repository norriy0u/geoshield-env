import requests, json

base = "https://norriy0u-geoshield-env.hf.space"

print("=== HEALTH ===")
r = requests.get(f"{base}/health", timeout=30)
print(f"  {r.status_code}: {r.json()}")

print("\n=== TASKS ===")
r = requests.get(f"{base}/tasks", timeout=30)
d = r.json()
print(f"  {r.status_code}: {len(d['tasks'])} tasks")

print("\n=== RESET ALL 4 TASKS ===")
for tid in [1, 2, 3, 4]:
    r = requests.post(f"{base}/reset", json={"task_id": tid, "seed": 42}, timeout=30)
    if r.status_code == 200:
        obs = r.json()["observation"]
        print(f"  Task {tid}: OK  case={obs['case_id']}  difficulty={obs['difficulty']}  actions={len(obs['available_actions'])}")
    else:
        print(f"  Task {tid}: FAIL {r.status_code} {r.text[:200]}")

print("\n=== STEP TEST (Task 1) ===")
r = requests.post(f"{base}/reset", json={"task_id": 1, "seed": 42}, timeout=30)
sid = r.json()["session_id"]
r2 = requests.post(f"{base}/step", json={"session_id": sid, "action": "ignore"}, timeout=30)
if r2.status_code == 200:
    d = r2.json()
    print(f"  reward={d['reward']}  done={d['done']}  feedback={d['info'].get('feedback', '')[:80]}")
else:
    print(f"  FAIL: {r2.status_code} {r2.text[:200]}")

print("\n=== STEP TEST (Task 2) ===")
r = requests.post(f"{base}/reset", json={"task_id": 2, "seed": 42}, timeout=30)
sid = r.json()["session_id"]
r2 = requests.post(f"{base}/step", json={"session_id": sid, "action": "civilian_activity", "threat_level": 3}, timeout=30)
if r2.status_code == 200:
    d = r2.json()
    print(f"  reward={d['reward']}  done={d['done']}")
else:
    print(f"  FAIL: {r2.status_code} {r2.text[:200]}")

print("\n=== STEP TEST (Task 3 investigate) ===")
r = requests.post(f"{base}/reset", json={"task_id": 3, "seed": 42}, timeout=30)
sid = r.json()["session_id"]
r2 = requests.post(f"{base}/step", json={"session_id": sid, "action": "investigate_sector_b", "reasoning": "checking high-priority sector"}, timeout=30)
if r2.status_code == 200:
    d = r2.json()
    print(f"  reward={d['reward']}  done={d['done']}  feedback={d['info'].get('feedback', '')[:80]}")
else:
    print(f"  FAIL: {r2.status_code} {r2.text[:200]}")

print("\n=== STEP TEST (Task 4) ===")
r = requests.post(f"{base}/reset", json={"task_id": 4, "seed": 42}, timeout=30)
sid = r.json()["session_id"]
r2 = requests.post(f"{base}/step", json={
    "session_id": sid,
    "action": "covert_operation",
    "cover_story_identified": "agricultural research facility",
    "deception_type": "research_weapons",
    "reasoning": "Reinforced structures inconsistent with farming. Encrypted comms confirm military activity."
}, timeout=30)
if r2.status_code == 200:
    d = r2.json()
    print(f"  reward={d['reward']}  done={d['done']}")
    print(f"  breakdown={d['info'].get('breakdown', {})}")
else:
    print(f"  FAIL: {r2.status_code} {r2.text[:200]}")

print("\nALL TESTS COMPLETE")
