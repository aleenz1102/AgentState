import subprocess
import time
import httpx

print("Starting test_hitl_agent.py...")
proc = subprocess.Popen([r".\venv\Scripts\python.exe", "test_hitl_agent.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# Poll for pending approval up to 10 seconds
for _ in range(20):
    time.sleep(0.5)
    try:
        res = httpx.get("http://localhost:8080/api/approvals/pending")
        approvals = res.json()
        for app in approvals:
            if app["session_id"] == "hitl_demo_session":
                app_id = app["id"]
                print(f"Found Pending Approval #{app_id} for hitl_demo_session! Approving...")
                act_res = httpx.post(f"http://localhost:8080/api/approvals/{app_id}/action", json={"action": "APPROVED"})
                print("Approval API response:", act_res.json())
                break
        if proc.poll() is not None:
            break
    except Exception as e:
        print("Polling error:", e)

stdout, stderr = proc.communicate(timeout=10)
print("--- AGENT OUTPUT ---")
print(stdout)
if stderr:
    print("--- AGENT ERRORS ---")
    print(stderr)
