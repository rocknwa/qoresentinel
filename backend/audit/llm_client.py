"""QoreSentinel adapter using RiskSearcher cloud LLM provider failover.

Provider priority: Anthropic -> OpenRouter -> Groq -> AgentRouter.
No local models or Ollama. Credentials remain server-side.
"""

from audit.risksearcher_client import run_specialist


def generate(prompt: str, *, max_tokens: int = 8000, role: str = "agent") -> str:
    # RiskSearcher currently manages completion limits within each provider client.
    # max_tokens is reserved for subsequent per-provider token budget integration.
    result = run_specialist(role, prompt, timeout=60)
    if result.get("_simulated"):
        raise RuntimeError("Simulated LLM responses cannot be used as audit evidence")
    response = result.get("response")
    if result.get("error") or not isinstance(response, str) or not response.strip():
        raise RuntimeError("Cloud LLM provider unavailable: " + str(result.get("error") or "empty response"))
    return response
