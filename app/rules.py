import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import CaseType, Department, EvidenceVerdict, Severity

PHONE_PATTERN = re.compile(r"(?:\+?88)?01[3-9]\d{8}")
TXN_PATTERN = re.compile(r"\b(?:TXN|txn)-?[A-Za-z0-9]+\b")
AMOUNT_WITH_CURRENCY_PATTERN = re.compile(
    r"\b(\d+(?:\.\d{1,2})?)\s*(?:bdt|taka|tk|/-)\b", re.IGNORECASE
)
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d{1,2})?\b")

PHISHING_TERMS = [
    "otp",
    "pin",
    "password",
    "scam",
    "fraud",
    "verification code",
    "code chaiche",
    "pin chaiche",
    "otp chaiche",
    "suspicious call",
    "phishing",
]
WRONG_TRANSFER_TERMS = [
    "wrong number",
    "wrong recipient",
    "wrong account",
    "bhul number",
    "vul number",
    "wrong e pathaisi",
    "sent to wrong",
]
PAYMENT_FAILED_TERMS = [
    "failed",
    "deducted",
    "not successful",
    "balance deducted",
    "payment hoy nai",
    "taka keteche",
    "fail hoise",
]
REFUND_TERMS = ["refund", "money back", "return my money", "taka ferot", "refund chai"]
DUPLICATE_TERMS = [
    "twice",
    "duplicate",
    "double charged",
    "two times",
    "duibar",
    "2 bar",
    "double payment",
]
MERCHANT_TERMS = ["settlement", "merchant settlement", "settlement pending", "settlement pai nai"]
AGENT_TERMS = ["cash in", "cash-in", "agent", "deposit not added", "cash in hoy nai"]

CASE_TO_DEPARTMENT = {
    CaseType.WRONG_TRANSFER: Department.DISPUTE_RESOLUTION,
    CaseType.PAYMENT_FAILED: Department.PAYMENTS_OPS,
    CaseType.REFUND_REQUEST: Department.CUSTOMER_SUPPORT,
    CaseType.DUPLICATE_PAYMENT: Department.PAYMENTS_OPS,
    CaseType.MERCHANT_SETTLEMENT_DELAY: Department.MERCHANT_OPERATIONS,
    CaseType.AGENT_CASH_IN_ISSUE: Department.AGENT_OPERATIONS,
    CaseType.PHISHING_OR_SOCIAL_ENGINEERING: Department.FRAUD_RISK,
    CaseType.OTHER: Department.CUSTOMER_SUPPORT,
}


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _contains_any(text: str, phrases: List[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def extract_signals(complaint: str) -> Dict[str, Any]:
    text = normalize_text(complaint)
    phones = PHONE_PATTERN.findall(complaint or "")
    txns = TXN_PATTERN.findall(complaint or "")

    amounts = [float(value) for value in AMOUNT_WITH_CURRENCY_PATTERN.findall(text)]
    if not amounts:
        for raw in NUMBER_PATTERN.findall(text):
            if len(raw.replace(".", "")) >= 7:
                continue
            try:
                amounts.append(float(raw))
            except ValueError:
                continue

    return {
        "normalized_complaint": text,
        "amount": amounts[0] if amounts else None,
        "mentioned_transaction_id": txns[0].upper() if txns else None,
        "mentioned_phone": phones[0] if phones else None,
        "suspicious_credential_terms": _contains_any(text, PHISHING_TERMS),
        "failed_payment_terms": _contains_any(text, PAYMENT_FAILED_TERMS),
        "refund_terms": _contains_any(text, REFUND_TERMS),
        "duplicate_payment_terms": _contains_any(text, DUPLICATE_TERMS),
        "merchant_terms": _contains_any(text, MERCHANT_TERMS),
        "agent_terms": _contains_any(text, AGENT_TERMS),
        "wrong_transfer_terms": _contains_any(text, WRONG_TRANSFER_TERMS),
    }


def detect_case_type(complaint: str) -> CaseType:
    text = normalize_text(complaint)

    if _contains_any(text, PHISHING_TERMS):
        return CaseType.PHISHING_OR_SOCIAL_ENGINEERING
    if _contains_any(text, WRONG_TRANSFER_TERMS):
        return CaseType.WRONG_TRANSFER
    if _contains_any(text, PAYMENT_FAILED_TERMS):
        return CaseType.PAYMENT_FAILED
    if _contains_any(text, REFUND_TERMS):
        return CaseType.REFUND_REQUEST
    if _contains_any(text, DUPLICATE_TERMS):
        return CaseType.DUPLICATE_PAYMENT
    if _contains_any(text, MERCHANT_TERMS):
        return CaseType.MERCHANT_SETTLEMENT_DELAY
    if _contains_any(text, AGENT_TERMS):
        return CaseType.AGENT_CASH_IN_ISSUE
    return CaseType.OTHER


def _normalize_phone(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _normalized_txn_id(txn: Dict[str, Any]) -> Optional[str]:
    txn_id = txn.get("transaction_id") or txn.get("txn_id")
    return str(txn_id).strip().upper() if txn_id else None


def _transaction_type_matches(case_type: CaseType, txn_type: str) -> bool:
    transfer_types = {"transfer", "send_money", "p2p"}
    payment_types = {"payment", "merchant_payment", "bill_payment", "purchase"}
    cash_in_types = {"cash_in", "cash-in", "agent_cash_in", "deposit"}

    if case_type == CaseType.WRONG_TRANSFER:
        return txn_type in transfer_types
    if case_type in {CaseType.PAYMENT_FAILED, CaseType.REFUND_REQUEST, CaseType.DUPLICATE_PAYMENT}:
        return txn_type in payment_types or txn_type in transfer_types
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return txn_type in {"settlement", "merchant_settlement", "merchant_payment"}
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return txn_type in cash_in_types
    return False


def _status_supports_case(case_type: CaseType, status: str) -> bool:
    if case_type == CaseType.WRONG_TRANSFER:
        return status == "completed"
    if case_type == CaseType.PAYMENT_FAILED:
        return status in {"failed", "pending", "reversed"}
    if case_type == CaseType.REFUND_REQUEST:
        return status in {"completed", "settled"}
    if case_type == CaseType.DUPLICATE_PAYMENT:
        return status == "completed"
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return status in {"pending", "processing"}
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return status in {"pending", "failed"}
    return False


def _parse_hour_clue(text: str) -> Optional[int]:
    match = re.search(r"\b(?:around\s*)?(\d{1,2})(?::\d{2})?\s*(am|pm)\b", text)
    if not match:
        return None
    hour = int(match.group(1)) % 12
    if match.group(2) == "pm":
        hour += 12
    return hour


def _parse_txn_hour(timestamp: Any) -> Optional[int]:
    if not timestamp:
        return None
    raw = str(timestamp).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw).hour
    except ValueError:
        return None


def score_transaction(
    complaint_signals: Dict[str, Any],
    case_type: CaseType,
    txn: Dict[str, Any],
) -> int:
    score = 0
    txn_id = _normalized_txn_id(txn)
    mentioned_txn_id = complaint_signals.get("mentioned_transaction_id")
    if txn_id and mentioned_txn_id and txn_id == mentioned_txn_id:
        score += 100

    txn_amount = txn.get("amount")
    amount = complaint_signals.get("amount")
    if txn_amount is not None and amount is not None:
        try:
            if abs(float(txn_amount) - float(amount)) < 0.01:
                score += 40
        except (TypeError, ValueError):
            pass

    counterparty = (
        txn.get("counterparty")
        or txn.get("recipient")
        or txn.get("sender")
        or txn.get("phone")
        or txn.get("merchant")
        or txn.get("agent")
    )
    mentioned_phone = complaint_signals.get("mentioned_phone")
    if counterparty and mentioned_phone:
        if _normalize_phone(counterparty) == _normalize_phone(mentioned_phone):
            score += 40

    txn_type = normalize_text(str(txn.get("type") or ""))
    if _transaction_type_matches(case_type, txn_type):
        score += 25

    status = normalize_text(str(txn.get("status") or ""))
    if _status_supports_case(case_type, status):
        score += 25

    clue_hour = _parse_hour_clue(complaint_signals.get("normalized_complaint", ""))
    txn_hour = _parse_txn_hour(txn.get("timestamp"))
    if clue_hour is not None and txn_hour is not None and abs(clue_hour - txn_hour) <= 2:
        score += 10

    return score


def match_transaction(
    complaint_signals: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    case_type: Optional[CaseType] = None,
) -> Optional[Dict[str, Any]]:
    active_case_type = case_type or detect_case_type(complaint_signals.get("normalized_complaint", ""))
    best_txn: Optional[Dict[str, Any]] = None
    best_score = 0

    for txn in transactions or []:
        score = score_transaction(complaint_signals, active_case_type, txn)
        if score > best_score:
            best_score = score
            best_txn = txn

    return best_txn if best_score >= 40 else None


def _count_matching_amount_transactions(
    transactions: List[Dict[str, Any]], amount: Optional[float], status: str = "completed"
) -> int:
    if amount is None:
        return 0
    count = 0
    for txn in transactions or []:
        try:
            txn_amount = float(txn.get("amount"))
        except (TypeError, ValueError):
            continue
        txn_status = normalize_text(str(txn.get("status") or ""))
        if abs(txn_amount - float(amount)) < 0.01 and txn_status == status:
            count += 1
    return count


def decide_verdict(
    case_type: CaseType,
    matched_txn: Optional[Dict[str, Any]],
    complaint_signals: Optional[Dict[str, Any]] = None,
    transactions: Optional[List[Dict[str, Any]]] = None,
) -> EvidenceVerdict:
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return EvidenceVerdict.INSUFFICIENT_DATA

    if not matched_txn:
        return EvidenceVerdict.INSUFFICIENT_DATA

    status = normalize_text(str(matched_txn.get("status") or ""))
    txn_type = normalize_text(str(matched_txn.get("type") or ""))
    amount = (complaint_signals or {}).get("amount")

    if case_type == CaseType.WRONG_TRANSFER:
        if status == "completed" and _transaction_type_matches(case_type, txn_type):
            return EvidenceVerdict.CONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.PAYMENT_FAILED:
        if status in {"failed", "pending", "reversed"}:
            return EvidenceVerdict.CONSISTENT
        if status == "completed":
            return EvidenceVerdict.INCONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.REFUND_REQUEST:
        if status in {"completed", "settled"}:
            return EvidenceVerdict.CONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.DUPLICATE_PAYMENT:
        completed_count = _count_matching_amount_transactions(transactions or [], amount)
        if completed_count >= 2:
            return EvidenceVerdict.CONSISTENT
        if completed_count == 1:
            return EvidenceVerdict.INCONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        if status in {"pending", "processing"}:
            return EvidenceVerdict.CONSISTENT
        if status in {"completed", "settled"}:
            return EvidenceVerdict.INCONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        if status in {"pending", "failed"}:
            return EvidenceVerdict.CONSISTENT
        if status == "completed":
            return EvidenceVerdict.INCONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    return EvidenceVerdict.INSUFFICIENT_DATA


def get_department(
    case_type: CaseType,
    amount: Optional[float] = None,
    verdict: Optional[EvidenceVerdict] = None,
) -> Department:
    if case_type == CaseType.REFUND_REQUEST:
        if (amount is not None and amount >= 5000) or verdict == EvidenceVerdict.INCONSISTENT:
            return Department.DISPUTE_RESOLUTION
    return CASE_TO_DEPARTMENT.get(case_type, Department.CUSTOMER_SUPPORT)


def calculate_severity(
    case_type: CaseType,
    amount: Optional[float],
    verdict: Optional[EvidenceVerdict] = None,
) -> Severity:
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return Severity.CRITICAL
    if amount is not None and amount >= 5000:
        return Severity.HIGH
    if case_type in {CaseType.WRONG_TRANSFER, CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT}:
        return Severity.HIGH
    if verdict in {EvidenceVerdict.INCONSISTENT, EvidenceVerdict.INSUFFICIENT_DATA}:
        return Severity.MEDIUM
    if case_type in {CaseType.MERCHANT_SETTLEMENT_DELAY, CaseType.AGENT_CASH_IN_ISSUE}:
        return Severity.MEDIUM
    return Severity.LOW


def needs_human_review(
    case_type: CaseType,
    severity: Severity,
    verdict: EvidenceVerdict,
    confidence: float,
    amount: Optional[float] = None,
) -> bool:
    if case_type in {
        CaseType.WRONG_TRANSFER,
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING,
        CaseType.MERCHANT_SETTLEMENT_DELAY,
        CaseType.AGENT_CASH_IN_ISSUE,
    }:
        return True
    if severity in {Severity.HIGH, Severity.CRITICAL}:
        return True
    if verdict in {EvidenceVerdict.INCONSISTENT, EvidenceVerdict.INSUFFICIENT_DATA}:
        return True
    if amount is not None and amount >= 5000:
        return True
    if case_type == CaseType.REFUND_REQUEST and verdict != EvidenceVerdict.CONSISTENT:
        return True
    if confidence < 0.75:
        return True
    return False


def build_reason_codes(
    case_type: CaseType,
    verdict: EvidenceVerdict,
    matched_txn: Optional[Dict[str, Any]],
    signals: Dict[str, Any],
) -> List[str]:
    codes = [case_type.value, verdict.value]
    if matched_txn:
        codes.append("transaction_match")
    else:
        codes.append("no_transaction_match")
    if signals.get("amount") is not None:
        codes.append("amount_detected")
    if signals.get("mentioned_transaction_id"):
        codes.append("transaction_id_mentioned")
    if signals.get("mentioned_phone"):
        codes.append("counterparty_detected")
    return codes
