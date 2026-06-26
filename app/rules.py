import re
from typing import List, Dict, Any, Optional
from app.schemas import EvidenceVerdict, CaseType, Severity, Department

# Regex patterns for signal extraction
PHONE_PATTERN = re.compile(r'(?:\+?88)?01[3-9]\d{8}')
TXN_PATTERN = re.compile(r'\b(?:TXN|txn)-?[A-Za-z0-9]+\b')
AMOUNT_PATTERN = re.compile(r'\b(\d+(?:\.\d{1,2})?)\s*(?:BDT|bdt|taka|Taka|tk|Tk|TK|/-)?\b')

def extract_signals(complaint: str) -> Dict[str, Any]:
    text = complaint.lower()
    
    # 1. Extract phone number
    phones = PHONE_PATTERN.findall(complaint)
    mentioned_phone = phones[0] if phones else None
    
    # 2. Extract transaction ID
    txns = TXN_PATTERN.findall(complaint)
    mentioned_transaction_id = txns[0].upper() if txns else None
    
    # 3. Extract amount
    # Find all numeric values, map them, filter out phone numbers and txn IDs if possible, or look for indicators like BDT/Taka/Tk
    amounts = []
    # Search specifically for amounts with currency suffix first
    currency_matches = re.findall(r'\b(\d+(?:\.\d{1,2})?)\s*(?:bdt|taka|tk|/-)\b', text)
    if currency_matches:
        amounts = [float(x) for x in currency_matches]
    else:
        # Fallback to general numbers
        all_nums = AMOUNT_PATTERN.findall(text)
        for num_str in all_nums:
            # Avoid matching parts of transaction IDs or phone numbers
            if len(num_str) < 7: # phone numbers are at least 11 digits, txn IDs typically have chars
                try:
                    amounts.append(float(num_str))
                except ValueError:
                    pass
    
    mentioned_amount = amounts[0] if amounts else None

    return {
        "amount": mentioned_amount,
        "mentioned_transaction_id": mentioned_transaction_id,
        "mentioned_phone": mentioned_phone
    }

def detect_case_type(text: str) -> CaseType:
    t = text.lower()

    if any(x in t for x in ["otp", "pin", "password", "scam", "fraud", "verification code", "suspicious call", "phishing"]):
        return CaseType.PHISHING_OR_SOCIAL_ENGINEERING

    if any(x in t for x in ["wrong number", "wrong recipient", "wrong account", "bhul number", "vul number", "wrong e pathaisi"]):
        return CaseType.WRONG_TRANSFER

    if any(x in t for x in ["failed", "deducted", "not successful", "payment hoy nai", "taka keteche", "fail hoise"]):
        return CaseType.PAYMENT_FAILED

    if any(x in t for x in ["refund", "money back", "return my money", "taka ferot", "refund chai"]):
        return CaseType.REFUND_REQUEST

    if any(x in t for x in ["twice", "duplicate", "double", "duibar", "2 bar", "double payment"]):
        return CaseType.DUPLICATE_PAYMENT

    if any(x in t for x in ["settlement", "merchant payment pending", "settlement pai nai"]):
        return CaseType.MERCHANT_SETTLEMENT_DELAY

    if any(x in t for x in ["cash in", "cash-in", "agent", "deposit not added", "cash in hoy nai"]):
        return CaseType.AGENT_CASH_IN_ISSUE

    return CaseType.OTHER

def match_transaction(complaint_signals: Dict[str, Any], transactions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best_txn = None
    best_score = 0

    for txn in transactions:
        score = 0
        
        # 1. Transaction ID matches exactly
        txn_id = txn.get("transaction_id") or txn.get("txn_id")
        if txn_id and complaint_signals["mentioned_transaction_id"]:
            # Normalize and compare
            if str(txn_id).strip().upper() == str(complaint_signals["mentioned_transaction_id"]).strip().upper():
                score += 100
        
        # 2. Amount matches
        txn_amount = txn.get("amount")
        if txn_amount is not None and complaint_signals["amount"] is not None:
            try:
                if abs(float(txn_amount) - float(complaint_signals["amount"])) < 0.01:
                    score += 40
            except (ValueError, TypeError):
                pass
        
        # 3. Counterparty matches
        counterparty = txn.get("counterparty") or txn.get("recipient") or txn.get("sender") or txn.get("phone")
        if counterparty and complaint_signals["mentioned_phone"]:
            # Check if mentioned phone matches or is a substring of counterparty
            clean_cp = re.sub(r'\D', '', str(counterparty))
            clean_mp = re.sub(r'\D', '', str(complaint_signals["mentioned_phone"]))
            if clean_mp in clean_cp or clean_cp in clean_mp:
                score += 40

        if score > best_score:
            best_score = score
            best_txn = txn

    # Standard threshold: a match is valid if it scores at least 40
    if best_score < 40:
        return None

    return best_txn

def decide_verdict(case_type: CaseType, matched_txn: Optional[Dict[str, Any]]) -> EvidenceVerdict:
    if not matched_txn:
        return EvidenceVerdict.INSUFFICIENT_DATA

    status = (matched_txn.get("status") or "").lower()
    txn_type = (matched_txn.get("type") or "").lower()

    if case_type == CaseType.WRONG_TRANSFER:
        # Wrong transfer claim holds if a completed transfer/send transaction exists
        if status == "completed":
            return EvidenceVerdict.CONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.PAYMENT_FAILED:
        if status == "failed":
            return EvidenceVerdict.CONSISTENT
        if status == "completed":
            return EvidenceVerdict.INCONSISTENT

    if case_type == CaseType.REFUND_REQUEST:
        return EvidenceVerdict.CONSISTENT

    if case_type == CaseType.DUPLICATE_PAYMENT:
        return EvidenceVerdict.CONSISTENT

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return EvidenceVerdict.INSUFFICIENT_DATA

    return EvidenceVerdict.INSUFFICIENT_DATA

def get_department(case_type: CaseType) -> Department:
    CASE_TO_DEPARTMENT = {
        CaseType.WRONG_TRANSFER: Department.DISPUTE_RESOLUTION,
        CaseType.PAYMENT_FAILED: Department.PAYMENTS_OPS,
        CaseType.REFUND_REQUEST: Department.CUSTOMER_SUPPORT,
        CaseType.DUPLICATE_PAYMENT: Department.PAYMENTS_OPS,
        CaseType.MERCHANT_SETTLEMENT_DELAY: Department.MERCHANT_OPERATIONS,
        CaseType.AGENT_CASH_IN_ISSUE: Department.AGENT_OPERATIONS,
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING: Department.FRAUD_RISK,
        CaseType.OTHER: Department.CUSTOMER_SUPPORT
    }
    return CASE_TO_DEPARTMENT.get(case_type, Department.CUSTOMER_SUPPORT)

def calculate_severity(case_type: CaseType, amount: Optional[float]) -> Severity:
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return Severity.CRITICAL
    
    if amount is not None and amount >= 5000:
        return Severity.HIGH

    if case_type in [CaseType.WRONG_TRANSFER, CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT]:
        return Severity.HIGH

    if case_type in [CaseType.MERCHANT_SETTLEMENT_DELAY, CaseType.AGENT_CASH_IN_ISSUE, CaseType.OTHER]:
        return Severity.MEDIUM

    return Severity.LOW

def needs_human_review(case_type: CaseType, severity: Severity, verdict: EvidenceVerdict, confidence: float) -> bool:
    if case_type in [CaseType.WRONG_TRANSFER, CaseType.PHISHING_OR_SOCIAL_ENGINEERING]:
        return True
    if severity in [Severity.HIGH, Severity.CRITICAL]:
        return True
    if verdict in [EvidenceVerdict.INCONSISTENT, EvidenceVerdict.INSUFFICIENT_DATA]:
        return True
    if confidence < 0.75:
        return True
    return False
