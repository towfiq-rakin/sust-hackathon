import json
import logging
from typing import Any, Dict, List, Optional

from app import rules, safety
from app.gemini_client import build_prompt, call_gemini_api
from app.schemas import CaseType, Department, EvidenceVerdict, Severity, TicketRequest, TicketResponse

logger = logging.getLogger(__name__)


def _matched_transaction_id(matched_txn: Optional[Dict[str, Any]]) -> Optional[str]:
    if not matched_txn:
        return None
    txn_id = matched_txn.get("transaction_id") or matched_txn.get("txn_id")
    return str(txn_id) if txn_id else None


def _default_summary(case_type: CaseType, verdict: EvidenceVerdict, matched_txn_id: Optional[str]) -> str:
    base = {
        CaseType.WRONG_TRANSFER: "Customer reports sending money to a wrong recipient.",
        CaseType.PAYMENT_FAILED: "Customer reports a failed payment or deducted balance.",
        CaseType.REFUND_REQUEST: "Customer requests a refund related to a prior transaction.",
        CaseType.DUPLICATE_PAYMENT: "Customer reports a possible duplicate payment.",
        CaseType.MERCHANT_SETTLEMENT_DELAY: "Customer reports a merchant settlement delay.",
        CaseType.AGENT_CASH_IN_ISSUE: "Customer reports an agent cash-in issue.",
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING: "Customer reports suspicious contact or a request for sensitive credentials.",
        CaseType.OTHER: "Customer submitted a complaint that requires manual review.",
    }[case_type]
    if matched_txn_id:
        return f"{base} Matched transaction: {matched_txn_id}. Evidence verdict: {verdict.value}."
    return f"{base} Evidence verdict: {verdict.value}."


def _default_action(case_type: CaseType, matched_txn_id: Optional[str]) -> str:
    txn_part = f" transaction {matched_txn_id}" if matched_txn_id else " matched records"
    actions = {
        CaseType.WRONG_TRANSFER: f"Escalate to dispute resolution and verify{txn_part} through internal records before taking any action.",
        CaseType.PAYMENT_FAILED: f"Verify{txn_part} status and check whether balance deduction and reversal records exist in internal systems.",
        CaseType.REFUND_REQUEST: f"Review{txn_part} and confirm refund eligibility under internal policy before any customer commitment.",
        CaseType.DUPLICATE_PAYMENT: f"Review{txn_part} and confirm whether duplicate debit occurred before any reversal step.",
        CaseType.MERCHANT_SETTLEMENT_DELAY: f"Review{txn_part} and merchant settlement ledger, then route to merchant operations for follow-up.",
        CaseType.AGENT_CASH_IN_ISSUE: f"Review{txn_part} and agent ledger entries, then route to agent operations for reconciliation.",
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING: "Escalate to fraud risk, advise the customer not to share credentials, and review for suspicious activity.",
        CaseType.OTHER: "Review the ticket manually and verify relevant transaction records through internal tools.",
    }
    return actions[case_type]


def _default_customer_reply(case_type: CaseType) -> str:
    replies = {
        CaseType.WRONG_TRANSFER: "We have noted your concern about this transfer. Please do not share your PIN, OTP, password, or sensitive account information with anyone. Our team will review the issue through official channels.",
        CaseType.PAYMENT_FAILED: "We have noted your concern about this payment. Please do not share your PIN, OTP, password, or sensitive account information with anyone. Our team will review the payment status through official channels.",
        CaseType.REFUND_REQUEST: "We have noted your refund concern. Please do not share your PIN, OTP, password, or sensitive account information with anyone. Our team will review the issue through official channels.",
        CaseType.DUPLICATE_PAYMENT: "We have noted your concern about this payment. Please do not share your PIN, OTP, password, or sensitive account information with anyone. Our team will review the issue through official channels.",
        CaseType.MERCHANT_SETTLEMENT_DELAY: "We have noted your settlement concern. Please do not share your PIN, OTP, password, or sensitive account information with anyone. Our team will review the issue through official channels.",
        CaseType.AGENT_CASH_IN_ISSUE: "We have noted your cash-in concern. Please do not share your PIN, OTP, password, or sensitive account information with anyone. Our team will review the issue through official channels.",
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING: "This may be a suspicious request. Please do not share your PIN, OTP, password, verification code, or sensitive account information with anyone. Only use official support channels for assistance.",
        CaseType.OTHER: safety.SAFE_DEFAULT_REPLY,
    }
    return replies[case_type]


def clean_json_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def create_fallback_response(
    request: TicketRequest,
    case_type: CaseType,
    matched_txn: Optional[Dict[str, Any]],
    verdict: EvidenceVerdict,
    signals: Dict[str, Any],
    reason: str,
) -> TicketResponse:
    matched_txn_id = _matched_transaction_id(matched_txn)
    amount = signals.get("amount")
    severity = rules.calculate_severity(case_type, amount, verdict)
    department = rules.get_department(case_type, amount, verdict)
    confidence = 0.5 if verdict == EvidenceVerdict.INSUFFICIENT_DATA else 0.82
    human_review = rules.needs_human_review(case_type, severity, verdict, confidence, amount)

    reason_codes = rules.build_reason_codes(case_type, verdict, matched_txn, signals)
    reason_codes.insert(0, "fallback_used")
    reason_codes.append(reason)

    return TicketResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=matched_txn_id,
        evidence_verdict=verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        agent_summary=_default_summary(case_type, verdict, matched_txn_id),
        recommended_next_action=_default_action(case_type, matched_txn_id),
        customer_reply=safety.sanitize_customer_reply(_default_customer_reply(case_type)),
        human_review_required=human_review,
        confidence=max(0.0, min(confidence, 1.0)),
        reason_codes=reason_codes,
    )


def _valid_transaction_id(txn_id: Any, transaction_history: List[Dict[str, Any]]) -> Optional[str]:
    if txn_id is None:
        return None
    normalized = str(txn_id)
    valid_ids = {
        str(txn.get("transaction_id") or txn.get("txn_id"))
        for txn in transaction_history
        if txn.get("transaction_id") or txn.get("txn_id")
    }
    return normalized if normalized in valid_ids else None


def _coerce_enum(enum_cls: Any, value: Any, fallback: Any) -> Any:
    try:
        return enum_cls(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_ai_response(
    ai_data: Dict[str, Any],
    request: TicketRequest,
    signals: Dict[str, Any],
    matched_txn: Optional[Dict[str, Any]],
    rule_case: CaseType,
    rule_verdict: EvidenceVerdict,
) -> TicketResponse:
    case_type = _coerce_enum(CaseType, ai_data.get("case_type"), rule_case)
    evidence_verdict = _coerce_enum(EvidenceVerdict, ai_data.get("evidence_verdict"), rule_verdict)
    amount = signals.get("amount")
    severity = rules.calculate_severity(case_type, amount, evidence_verdict)
    department = rules.get_department(case_type, amount, evidence_verdict)

    relevant_transaction_id = _valid_transaction_id(
        ai_data.get("relevant_transaction_id"), request.transaction_history
    ) or _matched_transaction_id(matched_txn)

    try:
        confidence = float(ai_data.get("confidence", 0.85))
    except (TypeError, ValueError):
        confidence = 0.85
    confidence = max(0.0, min(confidence, 1.0))

    raw_codes = ai_data.get("reason_codes")
    if isinstance(raw_codes, list):
        reason_codes = [str(code) for code in raw_codes if str(code).strip()]
    else:
        reason_codes = []
    if not reason_codes:
        reason_codes = rules.build_reason_codes(case_type, evidence_verdict, matched_txn, signals)
    reason_codes.append("gemini_used")

    customer_reply = safety.sanitize_customer_reply(str(ai_data.get("customer_reply") or ""))
    if customer_reply == safety.SAFE_DEFAULT_REPLY and str(ai_data.get("customer_reply") or "").strip():
        reason_codes.append("safety_sanitizer_triggered")

    human_review_required = rules.needs_human_review(
        case_type,
        severity,
        evidence_verdict,
        confidence,
        amount,
    )
    if "safety_sanitizer_triggered" in reason_codes:
        human_review_required = True

    return TicketResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=relevant_transaction_id,
        evidence_verdict=evidence_verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        agent_summary=str(ai_data.get("agent_summary") or _default_summary(case_type, evidence_verdict, relevant_transaction_id)),
        recommended_next_action=str(ai_data.get("recommended_next_action") or _default_action(case_type, relevant_transaction_id)),
        customer_reply=customer_reply,
        human_review_required=human_review_required,
        confidence=confidence,
        reason_codes=reason_codes,
    )


def analyze_ticket(ticket: TicketRequest) -> TicketResponse:
    signals = rules.extract_signals(ticket.complaint)
    case_type = rules.detect_case_type(ticket.complaint)
    matched_txn = rules.match_transaction(signals, ticket.transaction_history, case_type)
    verdict = rules.decide_verdict(case_type, matched_txn, signals, ticket.transaction_history)

    payload = {
        "ticket_id": ticket.ticket_id,
        "complaint": ticket.complaint,
        "language": ticket.language,
        "channel": ticket.channel,
        "user_type": ticket.user_type,
        "campaign_context": ticket.campaign_context,
        "metadata": ticket.metadata,
        "transaction_history": ticket.transaction_history,
        "extracted_signals": signals,
        "rule_case_type": case_type.value,
        "rule_evidence_verdict": verdict.value,
        "matched_transaction_id": _matched_transaction_id(matched_txn),
    }

    try:
        prompt = build_prompt(json.dumps(payload, ensure_ascii=True, default=str))
        ai_raw = call_gemini_api(prompt)
        if ai_raw:
            ai_data = json.loads(clean_json_text(ai_raw))
            if ai_data.get("ticket_id") != ticket.ticket_id:
                raise ValueError("Gemini returned mismatched ticket_id")
            return _normalize_ai_response(ai_data, ticket, signals, matched_txn, case_type, verdict)
    except Exception as exc:
        logger.warning("Gemini path failed for %s: %s", ticket.ticket_id, exc)
        return create_fallback_response(
            request=ticket,
            case_type=case_type,
            matched_txn=matched_txn,
            verdict=verdict,
            signals=signals,
            reason="gemini_failure",
        )

    return create_fallback_response(
        request=ticket,
        case_type=case_type,
        matched_txn=matched_txn,
        verdict=verdict,
        signals=signals,
        reason="gemini_skipped",
    )


def analyze_ticket_flow(ticket: TicketRequest) -> TicketResponse:
    return analyze_ticket(ticket)
