import os
from openai import OpenAI

class AgentStateOpenAI(OpenAI):
    """
    A 1-line wrapper around the standard OpenAI client that automatically
    routes all LLM and tool completions through the local AgentState proxy.
    """
    def __init__(
        self,
        session_id: str,
        step_number: int = 0,
        base_url: str = "http://localhost:8080/v1",
        api_key: str = None,
        require_approval: bool = False,
        fallback_model: str = None,
        **kwargs
    ):
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "mock-key")
            
        default_headers = kwargs.pop("default_headers", {})
        default_headers["x-agent-session-id"] = str(session_id)
        default_headers["x-agent-step-number"] = str(step_number)
        if require_approval:
            default_headers["x-agent-require-approval"] = "true"
        if fallback_model:
            default_headers["x-agent-fallback-model"] = str(fallback_model)
            
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers,
            **kwargs
        )

def wrap_langchain(session_id: str, step_number: int = 0, base_url: str = "http://localhost:8080/v1"):
    """
    Returns kwargs to pass directly into LangChain's ChatOpenAI:
    
    from langchain_openai import ChatOpenAI
    from agentstate import wrap_langchain
    
    llm = ChatOpenAI(**wrap_langchain(session_id="session_123"))
    """
    return {
        "openai_api_base": base_url,
        "openai_api_key": os.getenv("OPENAI_API_KEY", "mock-key"),
        "default_headers": {
            "x-agent-session-id": str(session_id),
            "x-agent-step-number": str(step_number)
        }
    }

def wrap_crewai(session_id: str, step_number: int = 0, base_url: str = "http://localhost:8080/v1"):
    """
    Returns config dictionary for CrewAI LLM initialization:
    
    from agentstate import wrap_crewai
    from crewai import Agent
    
    agent = Agent(llm_config=wrap_crewai(session_id="session_123"))
    """
    return {
        "config": {
            "base_url": base_url,
            "api_key": os.getenv("OPENAI_API_KEY", "mock-key"),
            "extra_headers": {
                "x-agent-session-id": str(session_id),
                "x-agent-step-number": str(step_number)
            }
        }
    }
