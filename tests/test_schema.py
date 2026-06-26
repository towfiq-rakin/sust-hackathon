import pytest
from pydantic import ValidationError
from app.schemas import TicketRequest, TicketResponse, EvidenceVerdict, CaseType, Severity, Department

def test_ticket_request_minimal():
    # Only ticket_id and complaint are required
    req = TicketRequest(
        ticket_id="TKT-100",
        complaint="My account is locked."
    )
    assert req.ticket_id == "TKT-100"
    assert req.complaint == "My account is locked."
    assert req.transaction_history == []
    assert req.metadata == {}

def test_ticket_request_full():
    req = TicketRequest(
        ticket_id="TKT-101",
        complaint="Wrong money sent",
        transaction_history=[
            {"transaction_id": "TXN-1", "amount": 100}
        ],
        language="en",
        channel="web",
        user_type="agent",
        campaign_context={"promo": "summer_deal"},
        metadata={"client_ip": "127.0.0.1"}
    )
    assert req.language == "en"
    assert req.metadata == {"client_ip": "127.0.0.1"}

def test_ticket_request_missing_required():
    with pytest.raises(ValidationError):
        TicketRequest(ticket_id="TKT-102")  # Missing complaint

def test_ticket_response_validation():
    # Valid response schema structure
    res = TicketResponse(
        ticket_id="TKT-200",
        evidence_verdict=EvidenceVerdict.CONSISTENT,
        case_type=CaseType.WRONG_TRANSFER,
        severity=Severity.HIGH,
        department=Department.DISPUTE_RESOLUTION,
        agent_summary="Summary text",
        recommended_next_action="Action text",
        customer_reply="Reply text",
        human_review_required=True,
        confidence=0.95,
        reason_codes=["ok"]
    )
    assert res.ticket_id == "TKT-200"
    assert res.evidence_verdict == "consistent"

def test_ticket_response_invalid_enum():
    with pytest.raises(ValidationError):
        TicketResponse(
            ticket_id="TKT-201",
            evidence_verdict="invalid_verdict_value",  # Should trigger ValidationError
            case_type=CaseType.OTHER,
            severity=Severity.LOW,
            department=Department.CUSTOMER_SUPPORT,
            agent_summary="Summary",
            recommended_next_action="Action",
            customer_reply="Reply",
            human_review_required=False,
            confidence=0.5,
            reason_codes=[]
        )
