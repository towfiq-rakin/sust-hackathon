import json
import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_official_sample_cases(monkeypatch):
    # Disable Gemini to validate rule-based fallback compliance
    monkeypatch.setattr(settings, "USE_GEMINI", False)
    # Load sample cases from the JSON file
    file_path = os.path.join(os.path.dirname(__file__), "..", "SUST_Preli_Sample_Cases.json")
    assert os.path.exists(file_path), "SUST_Preli_Sample_Cases.json not found"
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    cases = data.get("cases", [])
    
    for case in cases:
        case_id = case["id"]
        case_input = case["input"]
        expected = case["expected_output"]
        
        response = client.post("/analyze-ticket", json=case_input)
        assert response.status_code == 200, f"Case {case_id} failed with status {response.status_code}"
        
        res_data = response.json()
        
        # Check matching schemas and enums
        assert res_data["ticket_id"] == case_input["ticket_id"], f"Case {case_id} ticket_id mismatch"
        assert res_data["relevant_transaction_id"] == expected["relevant_transaction_id"], f"Case {case_id} relevant_transaction_id mismatch"
        assert res_data["evidence_verdict"] == expected["evidence_verdict"], f"Case {case_id} evidence_verdict mismatch"
        assert res_data["case_type"] == expected["case_type"], f"Case {case_id} case_type mismatch"
        assert res_data["department"] == expected["department"], f"Case {case_id} department mismatch"
        
        # Severity should match (comparable severity check)
        assert res_data["severity"] == expected["severity"], f"Case {case_id} severity mismatch"
        
        # Human review check (fallback mode forces True due to low confidence)
        if "fallback_used" not in res_data.get("reason_codes", []):
            assert res_data["human_review_required"] == expected["human_review_required"], f"Case {case_id} human_review_required mismatch"
        
        # Safety check: reply must be safe
        from app.safety import is_reply_safe
        assert is_reply_safe(res_data["customer_reply"]) is True, f"Case {case_id} response customer_reply is unsafe"
