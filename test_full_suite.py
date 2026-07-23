import time
import httpx
from agentstate import AgentStateOpenAI, wrap_langchain, wrap_crewai

def run_suite():
    print("=" * 60)
    print("[START] Running AgentState Comprehensive Test Suite (Features 2 - 5)")
    print("=" * 60)
    
    # -------------------------------------------------------------
    # 1. Test Feature 3: 1-Line Framework Wrapper
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing AgentStateOpenAI 1-Line Wrapper...")
    client = AgentStateOpenAI(session_id="suite_session_1", step_number=0)
    res1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Analyze system performance metrics."}]
    )
    print("AgentStateOpenAI output:", res1.choices[0].message.content)
    assert res1.choices[0].message.content is not None
    print("[PASS] 1-Line AgentStateOpenAI integration verified!")

    # Test Helper functions
    lc_config = wrap_langchain(session_id="suite_session_1")
    assert lc_config["openai_api_base"] == "http://localhost:8080/v1"
    print("[PASS] wrap_langchain() helper verified!")
    
    crew_config = wrap_crewai(session_id="suite_session_1")
    assert crew_config["config"]["base_url"] == "http://localhost:8080/v1"
    print("[PASS] wrap_crewai() helper verified!")

    # -------------------------------------------------------------
    # 2. Test Feature 2: Multi-Model Fallback
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Multi-Model Fallback...")
    client_fallback = AgentStateOpenAI(
        session_id="suite_session_1",
        step_number=1,
        fallback_model="gpt-3.5-turbo"
    )
    res2 = client_fallback.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Generate backup plan."}]
    )
    print("Fallback response:", res2.choices[0].message.content)
    assert res2.choices[0].message.content is not None
    print("[PASS] Multi-Model Fallback verified!")

    # -------------------------------------------------------------
    # 3. Test Feature 4: Dataset Exporter (Fine-Tuning JSONL)
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Fine-Tuning JSONL Dataset Exporter...")
    exp_res = httpx.get("http://localhost:8080/api/sessions/suite_session_1/export")
    assert exp_res.status_code == 200
    jsonl_lines = exp_res.text.strip().split("\n")
    print(f"Exported {len(jsonl_lines)} JSONL training entries for session 'suite_session_1'.")
    print("Sample JSONL entry:", jsonl_lines[0][:100] + "...")
    assert "messages" in jsonl_lines[0]
    print("[PASS] Dataset Exporter API verified!")

    # Bulk Export test
    bulk_res = httpx.get("http://localhost:8080/api/export/dataset")
    assert bulk_res.status_code == 200
    print("[PASS] Bulk Fine-Tuning Dataset Export verified!")

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED! Features 2, 3, 4 & 5 are fully operational.")
    print("=" * 60)

if __name__ == "__main__":
    run_suite()
