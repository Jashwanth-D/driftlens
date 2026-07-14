import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))

from plan_analyzer import AiDecision

def test_proceed_decision():
    d = AiDecision(
        decision="PROCEED",
        risk_level="LOW",
        summary="Safe deployment.",
        reasons=["No destructive changes", "Properly tagged"]
    )
    assert d.decision == "PROCEED"
    assert d.risk_level == "LOW"
    assert len(d.reasons) == 2

def test_block_decision():
    d = AiDecision(
        decision="BLOCK",
        risk_level="HIGH",
        summary="Dangerous plan.",
        reasons=["Destroys resources", "No tags", "Data loss risk"]
    )
    assert d.decision == "BLOCK"
    assert d.risk_level == "HIGH"
    assert len(d.reasons) == 3

def test_invalid_decision_rejected():
    try:
        AiDecision(
            decision="YOLO",
            risk_level="LOW",
            summary="Bad.",
            reasons=[]
        )
        assert False, "Should have raised error"
    except Exception:
        pass

if __name__ == "__main__":
    test_proceed_decision()
    test_block_decision()
    test_invalid_decision_rejected()
    print("All 3 tests passed!")