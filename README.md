# 🛡️ AgentState
### The Open-Source Resilience & Debugging Proxy for Autonomous AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)

**Stop wasting tokens when AI agents crash.** When an agent fails on step 87 out of 100, you typically lose the entire execution history and have to restart. 

**AgentState** is a lightweight, self-hosted proxy that intercepts your LLM and tool calls, automatically checkpoints their state, and lets you pause, edit, and resume runs from any point—saving you money and time.

![AgentState Dashboard Demo](assets/demo.gif)

---

## ⚡ The 10-Second Setup

**No SDKs. No code rewrites.** Just change your LLM client's `baseURL` to point to the AgentState proxy.

### Python (OpenAI SDK)
```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="http://localhost:8080/v1", # <-- Route through AgentState
    default_headers={
        "x-agent-session-id": "session_user_9812", 
        "x-agent-step-number": "0" # Optional: track execution steps
    }
)
```

### Node.js (OpenAI SDK)
```javascript
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: "your-api-key",
  baseURL: "http://localhost:8080/v1", // <-- Route through AgentState
  defaultHeaders: {
    "x-agent-session-id": "session_user_9812", 
    "x-agent-step-number": "0"
  }
});
```

---

## 🚀 Key Features

* **🔌 Plug-and-Play Integration:** No SDKs or code changes required. Just swap your LLM provider's `baseURL` to point to AgentState.
* **💾 Automatic Checkpointing:** Every prompt, response, and tool invocation is saved to a local SQLite database.
* **🔁 Fail-Safe Retries:** Automatic exponential backoff for failed tool executions and rate-limited LLM API calls.
* **🎛️ Session Replay & Rollback:** Visual dashboard to inspect agent trajectories. If a step fails, fix the code/prompt and resume the run exactly where it left off.
* **✋ Human-in-the-Loop Gateway:** Intercept sensitive tool calls (e.g., executing shell commands, processing payments) and pause execution until approved via webhook or dashboard.
* **🔌 Offline Mock Mode:** Run simulations completely offline with zero API costs using the built-in mock responder.

---

## 🛠️ Architecture

```mermaid
graph TD
    A[AI Agent / Application] -->|1. LLM / Tool Request| B[AgentState Proxy]
    B -->|2. Checkpoint State| C[(SQLite / Postgres)]
    B -->|3. Forward Request| D[OpenAI / Claude / Local LLM]
    D -->|4. Return Response| B
    B -->|5. Update Cache & Log| C
    B -->|6. Return to Agent| A
```

---

## 💻 Quick Start & Setup

### 1. Clone & Set Up Environment

```bash
# Clone the repository (once created)
git clone https://github.com/aleenz1102/AgentState.git
cd agentstate

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn httpx openai
```

### 2. Start the Proxy Server
```bash
python server.py
```
* The proxy will start listening on `http://localhost:8080`.
* The embedded dashboard will be live at `http://localhost:8080/dashboard`.

### 3. Run the Agent Simulator
To see AgentState in action, run the simulated agent:
```bash
python test_agent.py
```
* **First Run:** The agent will execute Step 0 (Fetch customer) and Step 1 (Generate report) successfully, then simulate a crash on Step 2 (Send email).
* **Second Run:** Run `python test_agent.py` again. Steps 0 and 1 will be returned from the local SQLite cache instantly (**~15ms, $0.00 token cost**), and Step 2 will be retried and complete successfully.

---

## 🔌 API Reference

### Proxy Endpoint
* **`POST /v1/chat/completions`**: OpenAI-compatible endpoint. Expects standard OpenAI body.
  * **Headers:**
    * `x-agent-session-id` (Required for caching): Unique session ID tracking the agent run.
    * `x-agent-step-number` (Recommended): Step index of the execution loop (e.g. `0`, `1`, `2`).

### Management API (Used by Dashboard)
* **`GET /api/sessions`**: Retrieve list of all logged sessions.
* **`GET /api/sessions/{session_id}`**: Retrieve session metadata and step list.
* **`POST /api/sessions/{session_id}/reset`**: Rollback a session.
  * **Body:** `{"step_number": int}`
  * **Description:** Deletes all cached steps starting from the specified index and marks the session status as `RUNNING`.
* **`POST /api/sessions/{session_id}/status`**: Update session status.
  * **Body:** `{"status": "RUNNING" | "COMPLETED" | "FAILED"}`

---

## 🗺️ Long-Term Roadmap

* **Phase 2:** Visual dashboard node graph representation (replacing list view).
* **Phase 3:** Open-core multi-tenant authentication (OAuth2 / API keys).
* **Phase 4:** Out-of-the-box integrations for LangGraph, Autogen, and CrewAI frameworks.

---

## 📄 License
AgentState is open-source software licensed under the [MIT License](LICENSE).
