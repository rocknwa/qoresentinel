from unittest.mock import patch
import pytest
from audit.llm_client import generate


def test_cloud_adapter_returns_actual_text():
    with patch("audit.llm_client.run_specialist", return_value={"provider":"groq", "response":"Potential reentrancy", "error":None, "_simulated":False}) as client:
        assert generate("Audit this", role="judge") == "Potential reentrancy"
        client.assert_called_once_with("judge", "Audit this", timeout=60)


def test_cloud_adapter_rejects_simulated_results():
    with patch("audit.llm_client.run_specialist", return_value={"response":"dummy", "error":None,"_simulated":True}):
        with pytest.raises(RuntimeError, match="Simulated"):
            generate("Audit this")


def test_cloud_adapter_rejects_no_provider():
    with patch("audit.llm_client.run_specialist", return_value={"response":"", "error":"No configured providers", "_simulated":False}):
        with pytest.raises(RuntimeError, match="No configured providers"):
            generate("Audit this")
