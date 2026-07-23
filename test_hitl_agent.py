import time
from openai import OpenAI

# Initialize client pointing to local AgentState proxy
client = OpenAI(
    api_key="mock-key",
    base_url="http://localhost:8080/v1"
)

SESSION_ID = "hitl_demo_session"

print("=" * 60)
print(f"[START] Starting Human-in-the-Loop Demo Agent [Session: {SESSION_ID}]")
print("=" * 60)

# Step 0: Harmless query
print("\n--- [Step #0] Query Database ---")
res0 = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Search database for active user list."}],
    extra_headers={
        "x-agent-session-id": SESSION_ID,
        "x-agent-step-number": "0"
    }
)
print("Response:", res0.choices[0].message.content)

# Step 1: Sensitive Operation requiring Human Approval
print("\n--- [Step #1] Sensitive Tool: Send Email Notification ---")
print("[WARN] Sending prompt containing sensitive action 'send_email'...")
print("[WAIT] Waiting for Human Approval on Dashboard (http://localhost:8080/dashboard)...")

start_time = time.time()
try:
    res1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Action: send_email to user@example.com with monthly invoice details."}],
        extra_headers={
            "x-agent-session-id": SESSION_ID,
            "x-agent-step-number": "1",
            "x-agent-require-approval": "true"
        }
    )
    duration = time.time() - start_time
    print(f"\n[APPROVED] Human approved action in {duration:.2f}s!")
    print("Response:", res1.choices[0].message.content)
except Exception as e:
    duration = time.time() - start_time
    print(f"\n[REJECTED/BLOCKED] Action blocked after {duration:.2f}s!")
    print("Error Details:", str(e))

print("\n" + "=" * 60)
print("Demo complete!")
print("=" * 60)
