from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_analyze_empty_complaint():
    # Empty complaint should raise a 422 Unprocessable Entity
    response = client.post("/analyze-ticket", json={
        "ticket_id": "TKT-001",
        "complaint": "",
        "transaction_history": []
    })
    assert response.status_code == 422

def test_analyze_ticket_fallback(monkeypatch):
    # Disable Gemini to force fallback
    monkeypatch.setattr(settings, "USE_GEMINI", False)
    payload = {
        "ticket_id": "TKT-001",
        "complaint": "I sent money to wrong number, target was 01712345678 and amount was 5000 tk.",
        "transaction_history": [
            {
                "transaction_id": "TXN-999",
                "amount": 5000,
                "counterparty": "01712345678",
                "status": "completed",
                "type": "transfer"
            }
        ]
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["ticket_id"] == "TKT-001"
    assert data["relevant_transaction_id"] == "TXN-999"
    assert data["case_type"] == "wrong_transfer"
    assert data["evidence_verdict"] == "consistent"
    assert data["severity"] == "high"
    assert data["department"] == "dispute_resolution"
    assert data["human_review_required"] is True
    assert "fallback_used" in data["reason_codes"]
