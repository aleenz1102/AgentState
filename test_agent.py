import os
import sys
import time
from openai import OpenAI

SESSION_ID = "agentstate_demo_session_1"
CRASH_FILE = "failed_once.txt"

# Initialize OpenAI client pointing to our local AgentState proxy
client = OpenAI(
    api_key="mock-key", # Pass mock key or real key
    base_url="http://localhost:8080/v1"
)

# Prompts for each step of the agent execution
STEPS = [
    {"step": 0, "name": "Fetch customer record", "prompt": "Find customer record for user Alice who joined in 2024."},
    {"step": 1, "name": "Generate report", "prompt": "SummarizeAlice's account activity and generate a monthly usage report."},
    {"step": 2, "name": "Send email", "prompt": "Draft and send an email notification to Alice with her account activity summary."}
]

def run_agent():
    print(f"\n[START] Running Agentic Workflow for Session: '{SESSION_ID}'")
    
    # Check if this is the first execution (which will crash) or the recovery execution
    first_run = not os.path.exists(CRASH_FILE)
    
    if first_run:
        print("[RUN 1] First run: Agent will simulate a crash on Step 2.")
    else:
        print("[RUN 2] Recovery run: Agent is resuming from previous checkpoint.")
        
    for step in STEPS:
        step_num = step["step"]
        step_name = step["name"]
        prompt = step["prompt"]
        
        print(f"\n--- [Step #{step_num}] {step_name} ---")
        print(f"Prompt: {prompt}")
        
        # Simulate agent code crashing on Step 2 during first run
        if step_num == 2 and first_run:
            print("[WARN] [Agent Code] Simulating network/tool error on step 2...")
            # Create the crash flag file so the next run succeeds
            with open(CRASH_FILE, "w") as f:
                f.write("failed")
            print("[FAIL] Agent crashed! Exiting execution dynamically.")
            sys.exit(1)
            
        start_time = time.time()
        
        # Call proxy
        try:
            raw_response = client.chat.completions.with_raw_response.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                extra_headers={
                    "x-agent-session-id": SESSION_ID,
                    "x-agent-step-number": str(step_num)
                }
            )
            
            latency = time.time() - start_time
            response = raw_response.parse()
            content = response.choices[0].message.content
            
            # Check custom cache header returned by the proxy
            is_cached = raw_response.headers.get("x-agentstate-cache-hit") == "true"
            
            if is_cached:
                print(f"[CACHE HIT] [AgentState Cache Hit] Retuned instant response in {latency:.4f}s (Cost: $0.00)")
            else:
                print(f"[CACHE MISS] [LLM Execution] Called LLM in {latency:.2f}s")
                
            print(f"Response: {content}")
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            sys.exit(1)

    print("\n[SUCCESS] Agent workflow completed successfully!")
    
    # Clean up the crash file on success
    if os.path.exists(CRASH_FILE):
        os.remove(CRASH_FILE)
        print("[CLEANUP] Cleaned up temporary crash file.")

if __name__ == "__main__":
    # If the user passed '--reset', we delete the crash file and reset
    if "--reset" in sys.argv:
        if os.path.exists(CRASH_FILE):
            os.remove(CRASH_FILE)
        print("Reset simulation state.")
        sys.exit(0)
        
    run_agent()
