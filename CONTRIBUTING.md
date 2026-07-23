# Contributing to AgentState 🛡️

First off, thank you for considering contributing to AgentState! It's people like you who make AgentState such a powerful resilience and debugging control plane for the AI developer community.

---

## 🛠️ How to Get Started

### 1. Fork & Clone
1. Fork the repository on GitHub: `https://github.com/aleenz1102/AgentState`
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/AgentState.git
   cd AgentState
   ```

### 2. Set Up Development Environment
Create and activate a virtual environment:
```bash
# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt # or pip install fastapi uvicorn httpx openai playwright Pillow imageio
```

### 3. Run the Proxy & Test Suite
Verify everything is working locally:
```bash
# Start server
python server.py

# Run comprehensive test suite
python test_full_suite.py
```

---

## 💡 Types of Contributions We Welcome

- **🐛 Bug Reports & Fixes:** Found an edge case with streaming completions or headers? Submit an issue or PR!
- **🔌 Framework Integrations:** Expand `agentstate/integrations.py` to support new agent frameworks (e.g. Autogen, LlamaIndex, DSPy).
- **🎨 Dashboard UI Improvements:** Enhance the visual dashboard (`static/index.html`) with graph visualizers, dark mode tweaks, or token analytics.
- **📚 Documentation & Examples:** Improve README guides, add code snippets, or translate docs.

---

## 📜 Pull Request Guidelines

1. **Create a Feature Branch:** `git checkout -b feature/my-cool-feature`
2. **Keep Commits Clean:** Write descriptive commit messages following Conventional Commits (e.g., `feat: add Autogen wrapper`, `fix: handle 429 backoff`).
3. **Run Tests:** Ensure `python test_full_suite.py` passes before opening a PR.
4. **Submit PR:** Open a Pull Request against the `main` branch with a summary of changes.

Thank you for helping build the future of resilient AI agents! 🚀
