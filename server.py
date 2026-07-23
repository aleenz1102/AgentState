import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import time
import json
import db

app = FastAPI(title="AgentState Proxy")

# CORS middleware for local dashboard development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db.init_db()

# Target LLM API URL
OPENAI_API_URL = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "mock-key")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    print(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.2f}s")
    return response

# Static Dashboard Routes
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/dashboard")
async def get_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/")
async def root_redirect():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Proxy Endpoint
@app.post("/v1/chat/completions")
async def proxy_completions(request: Request):
    headers = request.headers
    session_id = headers.get("x-agent-session-id")
    step_number_str = headers.get("x-agent-step-number")
    
    # If no session ID is provided, behave as a standard transparent proxy
    if not session_id:
        return await forward_to_llm(request)
        
    step_number = int(step_number_str) if step_number_str else 0
    
    # Ensure session exists in the DB
    db.get_or_create_session(session_id)
    
    body = await request.json()
    
    # Extract prompt messages and tools to hash
    messages = body.get("messages", [])
    tools = body.get("tools", [])
    
    prompt_str = json.dumps(messages)
    tools_str = json.dumps(tools)
    
    request_hash = db.calculate_hash(prompt_str, tools_str)
    
    # Check for Human-in-the-Loop approval requirements
    require_approval = headers.get("x-agent-require-approval", "false").lower() == "true"
    
    # Auto-detect sensitive prompt contents if flag is not set explicitly
    last_msg = messages[-1].get("content", "") if messages else ""
    if not require_approval and any(keyword in last_msg.lower() for keyword in ["send_email", "execute_command", "delete_database", "stripe_charge"]):
        require_approval = True

    if require_approval:
        tool_name = "sensitive_operation"
        if "send_email" in last_msg.lower(): tool_name = "send_email"
        elif "execute_command" in last_msg.lower(): tool_name = "execute_command"
        elif "delete_database" in last_msg.lower(): tool_name = "delete_database"
        elif "stripe_charge" in last_msg.lower(): tool_name = "stripe_charge"
        
        approval_id = db.create_approval_request(session_id, step_number, tool_name, last_msg)
        print(f"[HITL GATEWAY] Session: {session_id}, Step: {step_number} PAUSED waiting for approval #{approval_id}...")
        await send_webhook_alert("APPROVAL_REQUIRED", {"session_id": session_id, "approval_id": approval_id, "tool_name": tool_name, "prompt": last_msg})
        
        # Poll DB until approval is resolved or timed out (60 seconds)
        start_wait = time.time()
        approved = False
        rejected = False
        
        import asyncio
        while time.time() - start_wait < 60:
            app_req = db.get_approval_by_id(approval_id)
            if app_req:
                if app_req["status"] == "APPROVED":
                    approved = True
                    break
                elif app_req["status"] == "REJECTED":
                    rejected = True
                    break
            await asyncio.sleep(0.5)
            
        if rejected:
            print(f"[HITL GATEWAY] Approval #{approval_id} REJECTED by human.")
            db.update_session_status(session_id, "FAILED")
            return JSONResponse(
                status_code=403,
                content={"error": {"message": "Execution blocked: Tool call rejected by Human-in-the-Loop Gateway", "type": "human_rejection"}}
            )
        elif not approved:
            print(f"[HITL GATEWAY] Approval #{approval_id} TIMED OUT.")
            db.update_session_status(session_id, "FAILED")
            return JSONResponse(
                status_code=408,
                content={"error": {"message": "Execution blocked: Human approval timed out after 60s", "type": "approval_timeout"}}
            )
            
        print(f"[HITL GATEWAY] Approval #{approval_id} APPROVED! Resuming LLM execution...")

    # Check cache
    cached_step = db.get_cached_step(session_id, step_number, request_hash)
    if cached_step:
        print(f"[CACHE HIT] Session: {session_id}, Step: {step_number}")
        # Parse cached response string back to dict
        response_data = json.loads(cached_step["response"])
        return JSONResponse(
            content=response_data,
            headers={"x-agentstate-cache-hit": "true"}
        )
        
    print(f"[CACHE MISS] Session: {session_id}, Step: {step_number}. Calling LLM...")
    
    # Check for fallback model preferences
    fallback_model = headers.get("x-agent-fallback-model") or os.getenv("FALLBACK_MODEL")
    
    # Forward to real LLM
    start_time = time.time()
    response_data, status_code = await forward_to_llm_internal(body, request.headers)
    latency = time.time() - start_time
    
    # Handle multi-model fallback on provider error/rate-limit
    if status_code != 200 and fallback_model and body.get("model") != fallback_model:
        print(f"[FALLBACK TRIGGERED] Primary model failed ({status_code}). Rerouting to fallback model: {fallback_model}...")
        body["model"] = fallback_model
        start_time = time.time()
        response_data, status_code = await forward_to_llm_internal(body, request.headers)
        latency = time.time() - start_time
        if status_code == 200:
            print(f"[FALLBACK SUCCESS] Rerouted execution to {fallback_model} completed successfully!")
    
    if status_code != 200:
        db.update_session_status(session_id, "FAILED")
        await send_webhook_alert("SESSION_FAILED", {"session_id": session_id, "step_number": step_number, "error": response_data})
        return JSONResponse(content=response_data, status_code=status_code)
        
    # Calculate token costs (standard estimate or read from response usage)
    usage = response_data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    
    # Standard GPT-4o prices per 1M tokens ($2.50 / $10.00)
    cost = (prompt_tokens * 0.0000025) + (completion_tokens * 0.000010)
    
    # Cache the step
    db.save_step(
        session_id=session_id,
        step_number=step_number,
        request_hash=request_hash,
        prompt=json.dumps(body),
        response=json.dumps(response_data),
        token_cost=cost,
        latency=latency
    )
    
    return JSONResponse(content=response_data)

# Webhook Alert Helper
async def send_webhook_alert(event_type: str, details: dict):
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        return
        
    payload = {
        "event": event_type,
        "timestamp": time.time(),
        "details": details
    }
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(webhook_url, json=payload, timeout=5.0)
            print(f"[WEBHOOK SENT] Event: {event_type} delivered to {webhook_url}")
        except Exception as e:
            print(f"[WEBHOOK FAILED] Error sending {event_type} to {webhook_url}: {e}")

# Dashboard & Management APIs
@app.get("/api/sessions")
async def list_sessions():
    return db.get_all_sessions()

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    details = db.get_session_details(session_id)
    if not details:
        raise HTTPException(status_code=404, detail="Session not found")
    return details

@app.post("/api/sessions/{session_id}/reset")
async def reset_session(session_id: str, payload: dict):
    step_number = payload.get("step_number", 0)
    db.reset_session_from_step(session_id, step_number)
    return {"message": f"Session {session_id} reset from step {step_number} successfully."}

@app.post("/api/sessions/{session_id}/status")
async def set_session_status(session_id: str, payload: dict):
    status = payload.get("status", "RUNNING")
    db.update_session_status(session_id, status)
    return {"message": f"Session {session_id} status updated to {status}."}

# Human-in-the-Loop Approval APIs
@app.get("/api/approvals/pending")
async def list_pending_approvals():
    return db.get_pending_approvals()

@app.post("/api/approvals/{approval_id}/action")
async def resolve_approval_action(approval_id: int, payload: dict):
    action = payload.get("action", "").upper()
    if action not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Action must be APPROVED or REJECTED")
    db.update_approval_status(approval_id, action)
    return {"message": f"Approval #{approval_id} updated to {action}"}

# Dataset Exporter APIs (Fine-Tuning JSONL)
@app.get("/api/sessions/{session_id}/export")
async def export_session_dataset(session_id: str):
    dataset = db.get_exportable_steps(session_id)
    jsonl_str = "\n".join(json.dumps(entry) for entry in dataset)
    return Response(
        content=jsonl_str,
        media_type="application/x-jsonlines",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}_dataset.jsonl"}
    )

@app.get("/api/export/dataset")
async def export_bulk_dataset():
    dataset = db.get_exportable_steps()
    jsonl_str = "\n".join(json.dumps(entry) for entry in dataset)
    return Response(
        content=jsonl_str,
        media_type="application/x-jsonlines",
        headers={"Content-Disposition": "attachment; filename=agentstate_fine_tuning_dataset.jsonl"}
    )

# HTTP Helpers for forwarding
async def forward_to_llm(request: Request):
    body = await request.body()
    headers = dict(request.headers)
    
    # Clean up proxy headers before forwarding
    headers.pop("host", None)
    headers.pop("content-length", None)
    headers["authorization"] = f"Bearer {OPENAI_API_KEY}"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                f"{OPENAI_API_URL}/chat/completions",
                content=body,
                headers=headers,
                timeout=60.0
            )
            return Response(content=res.content, status_code=res.status_code, headers=dict(res.headers))
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)

async def forward_to_llm_internal(body: dict, original_headers):
    # Mock completions locally if no real API key is set
    if OPENAI_API_KEY == "mock-key":
        time.sleep(0.5)  # Simulate API latency
        last_message = body.get("messages", [])[-1].get("content", "")
        return {
            "id": "chatcmpl-mock123",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "gpt-4o"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[MOCK RESPONSE] Successfully processed prompt: {last_message}"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 20,
                "total_tokens": 35
            }
        }, 200

    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # Pass along any target organization or project headers if present
    for k, v in original_headers.items():
        if k.lower().startswith("openai-"):
            headers[k.lower()] = v

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                f"{OPENAI_API_URL}/chat/completions",
                json=body,
                headers=headers,
                timeout=60.0
            )
            if res.status_code == 200:
                return res.json(), 200
            else:
                return {"error": res.text}, res.status_code
        except Exception as e:
            return {"error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting AgentState Proxy on port {port}...")
    print(f"Dashboard available at http://localhost:{port}/dashboard")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
