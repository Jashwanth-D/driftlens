import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))

from plan_analyzer import AiDecision, analyze_plan
from unittest.mock import patch, MagicMock

def test_proceed_decision():
    d = AiDecision(decision="PROCEED", risk_level="LOW", summary="Safe.", reasons=["No destructive changes", "Properly tagged"])
    assert d.decision == "PROCEED"
    assert d.risk_level == "LOW"
    assert len(d.reasons) == 2

def test_block_decision():
    d = AiDecision(decision="BLOCK", risk_level="HIGH", summary="Dangerous.", reasons=["Destroys resources", "No tags", "Data loss risk"])
    assert d.decision == "BLOCK"
    assert d.risk_level == "HIGH"
    assert len(d.reasons) == 3

def test_hold_decision():
    d = AiDecision(decision="HOLD", risk_level="MEDIUM", summary="Needs review.", reasons=["Mixed changes"])
    assert d.decision == "HOLD"
    assert d.risk_level == "MEDIUM"

def test_invalid_decision_rejected():
    try:
        AiDecision(decision="YOLO", risk_level="LOW", summary="Bad.", reasons=[])
        assert False, "Should have raised error"
    except Exception:
        pass

def test_invalid_risk_rejected():
    try:
        AiDecision(decision="PROCEED", risk_level="EXTREME", summary="Bad.", reasons=[])
        assert False, "Should have raised error"
    except Exception:
        pass

def test_decision_fields_present():
    d = AiDecision(decision="PROCEED", risk_level="LOW", summary="OK.", reasons=["Fine"])
    assert hasattr(d, "decision")
    assert hasattr(d, "risk_level")
    assert hasattr(d, "summary")
    assert hasattr(d, "reasons")

def test_reasons_is_list():
    d = AiDecision(decision="PROCEED", risk_level="LOW", summary="OK.", reasons=["A", "B"])
    assert isinstance(d.reasons, list)

def test_empty_reasons_allowed():
    d = AiDecision(decision="PROCEED", risk_level="LOW", summary="OK.", reasons=[])
    assert len(d.reasons) == 0

def test_analyze_plan_mocked():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"decision": "PROCEED", "risk_level": "LOW", "summary": "Safe to deploy.", "reasons": ["No destructive changes"]}'

    with patch("plan_analyzer.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = analyze_plan("Test", "Plan: 1 to add")
        assert result.decision == "PROCEED"
        assert result.risk_level == "LOW"

def test_analyze_plan_block_mocked():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"decision": "BLOCK", "risk_level": "HIGH", "summary": "Dangerous.", "reasons": ["Destroys data", "No tags"]}'

    with patch("plan_analyzer.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = analyze_plan("Test", "Plan: 3 to destroy")
        assert result.decision == "BLOCK"
        assert len(result.reasons) == 2

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

# --- Additional tests for scenarios 3 and 4 (mocked) ---

def test_analyze_plan_cross_cloud_mocked():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''{"decision": "PROCEED", "risk_level": "LOW", "summary": "Safe migration.", "reasons": ["Intentional", "Cost neutral"]}'''
    with patch("plan_analyzer.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = analyze_plan("Cross-Cloud", "Plan: 2 to add, 0 to change, 2 to destroy")
        assert result.decision == "PROCEED"
        assert result.risk_level == "LOW"

def test_analyze_plan_cdn_downtime_mocked():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''{"decision": "BLOCK", "risk_level": "HIGH", "summary": "TLS downgrade.", "reasons": ["Security risk", "Cache issue", "404 risk"]}'''
    with patch("plan_analyzer.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = analyze_plan("CDN Change", "Plan: 0 to add, 1 to change, 0 to destroy")
        assert result.decision == "BLOCK"
        assert len(result.reasons) == 3

def test_analyze_plan_strips_markdown_fences():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''```json
{"decision": "PROCEED", "risk_level": "LOW", "summary": "OK.", "reasons": []}
```'''
    with patch("plan_analyzer.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = analyze_plan("Test", "Plan")
        assert result.decision == "PROCEED"

def test_analyze_plan_hold_scenario():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''{"decision": "HOLD", "risk_level": "MEDIUM", "summary": "Needs review.", "reasons": ["Mixed"]}'''
    with patch("plan_analyzer.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = analyze_plan("Ambiguous", "Plan")
        assert result.decision == "HOLD"
        assert result.risk_level == "MEDIUM"

def test_scenario_strings_defined():
    import plan_analyzer
    assert "5 to add" in plan_analyzer.scenario1
    assert "3 to destroy" in plan_analyzer.scenario2
    assert "Cross-cloud migration" in plan_analyzer.scenario3
    assert "downtime" in plan_analyzer.scenario4.lower()
