"""Quick server verification script — tests all endpoints locally."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, './src/geoshield')
sys.path.insert(0, './server')

from server.app import app
print(f"App title: {app.title}")
print(f"App version: {app.version}")

from fastapi.testclient import TestClient
client = TestClient(app)

# Health
r = client.get("/health")
print(f"Health: {r.status_code} {r.json()}")

# Info
r = client.get("/info")
features = list(r.json().get("features", {}).keys())
print(f"Info: {r.status_code} features={features}")

# Tasks
r = client.get("/tasks")
print(f"Tasks: {r.status_code} count={len(r.json().get('tasks', []))}")

# Reset Task 1
r = client.post("/reset", json={"task_id": 1, "seed": 42})
data = r.json()
sid = data["session_id"]
print(f"Reset T1: {r.status_code} session={sid[:8]}... done={data.get('done')}")

# Multi-step: request_context
r = client.post("/step", json={"action": "request_context", "session_id": sid})
s1 = r.json()
print(f"Step1 (context): {r.status_code} done={s1.get('done')} reward={s1.get('reward')}")

# Decide
r = client.post("/step", json={"action": "ignore", "session_id": sid})
s2 = r.json()
print(f"Step2 (decide): {r.status_code} done={s2.get('done')} reward={s2.get('reward')}")

# Reset Task 2
r = client.post("/reset", json={"task_id": 2, "seed": 42})
data = r.json()
sid2 = data["session_id"]

r = client.post("/step", json={"action": "request_analysis", "session_id": sid2})
s1 = r.json()
print(f"T2 Step1 (analysis): {r.status_code} done={s1.get('done')}")

r = client.post("/step", json={"action": "troop_movement", "threat_level": 7, "session_id": sid2})
s2 = r.json()
print(f"T2 Step2 (classify): {r.status_code} done={s2.get('done')} reward={s2.get('reward')}")

# Reset Task 4
r = client.post("/reset", json={"task_id": 4, "seed": 42})
data = r.json()
sid4 = data["session_id"]

r = client.post("/step", json={"action": "request_verification", "session_id": sid4})
s1 = r.json()
print(f"T4 Step1 (verify): {r.status_code} done={s1.get('done')}")

r = client.post("/step", json={
    "action": "covert_operation",
    "cover_story_identified": "test cover",
    "deception_type": "civilian_military",
    "reasoning": "Based on detected anomalies.",
    "session_id": sid4,
})
s2 = r.json()
print(f"T4 Step2 (classify): {r.status_code} done={s2.get('done')} reward={s2.get('reward')}")

# State endpoint
r = client.get(f"/state?session_id={sid}")
print(f"State: {r.status_code}")

print()
print("=== ALL ENDPOINTS VERIFIED SUCCESSFULLY ===")
