from fastapi.testclient import TestClient
from app.main import app
from app.schemas import EvidenceVerdict, CaseType, Severity, Department

client = TestClient(app)

def test_wrong_transfer_consistent():
    payload = {
        "ticket_id": "TKT-WT-1",
        "complaint": "I sent 5000 taka to a wrong number 01712345678.",
        "transaction_history": [
            {
                "transaction_id": "TXN-9101",
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
    assert data["case_type"] == CaseType.WRONG_TRANSFER
    assert data["evidence_verdict"] == EvidenceVerdict.CONSISTENT
    assert data["severity"] == Severity.HIGH
    assert data["department"] == Department.DISPUTE_RESOLUTION
    assert data["human_review_required"] is True

def test_payment_failed_consistent():
    payload = {
        "ticket_id": "TKT-PF-1",
        "complaint": "My payment failed but 3000 tk was deducted.",
        "transaction_history": [
            {
                "transaction_id": "TXN-PF-10",
                "amount": 3000,
                "status": "failed",
                "type": "payment"
            }
        ]
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["case_type"] == CaseType.PAYMENT_FAILED
    assert data["evidence_verdict"] == EvidenceVerdict.CONSISTENT
    assert data["severity"] == Severity.HIGH
    assert data["department"] == Department.PAYMENTS_OPS

def test_payment_failed_inconsistent():
    payload = {
        "ticket_id": "TKT-PF-2",
        "complaint": "My payment failed for amount 2500 tk.",
        "transaction_history": [
            {
                "transaction_id": "TXN-PF-20",
                "amount": 2500,
                "status": "completed",
                "type": "payment"
            }
        ]
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["case_type"] == CaseType.PAYMENT_FAILED
    assert data["evidence_verdict"] == EvidenceVerdict.INCONSISTENT
    assert data["severity"] == Severity.MEDIUM
    assert data["department"] == Department.PAYMENTS_OPS
    assert data["human_review_required"] is True

def test_phishing_critical():
    payload = {
        "ticket_id": "TKT-PH-1",
        "complaint": "Someone asked for my OTP pin and password.",
        "transaction_history": []
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["case_type"] == CaseType.PHISHING_OR_SOCIAL_ENGINEERING
    assert data["severity"] == Severity.CRITICAL
    assert data["department"] == Department.FRAUD_RISK
    assert data["human_review_required"] is True

def test_refund_request_override_high_amount():
    payload = {
        "ticket_id": "TKT-RF-1",
        "complaint": "I want a refund for my order of 6000 taka.",
        "transaction_history": [
            {
                "transaction_id": "TXN-RF-1",
                "amount": 6000,
                "status": "completed",
                "type": "payment"
            }
        ]
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["case_type"] == CaseType.REFUND_REQUEST
    assert data["evidence_verdict"] == EvidenceVerdict.CONSISTENT
    # Should override to dispute_resolution because amount >= 5000 BDT
    assert data["department"] == Department.DISPUTE_RESOLUTION
    assert data["human_review_required"] is True

def test_refund_request_no_override_low_amount():
    payload = {
        "ticket_id": "TKT-RF-2",
        "complaint": "I need a refund of 500 tk.",
        "transaction_history": [
            {
                "transaction_id": "TXN-RF-2",
                "amount": 500,
                "status": "completed",
                "type": "payment"
            }
        ]
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["case_type"] == CaseType.REFUND_REQUEST
    assert data["evidence_verdict"] == EvidenceVerdict.CONSISTENT
    # Should not override because amount < 5000 and it's consistent
    assert data["department"] == Department.CUSTOMER_SUPPORT
