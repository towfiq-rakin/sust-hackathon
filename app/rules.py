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

    if any(x in t for x in [
        "otp", "pin", "password", "scam", "fraud", "verification code", "suspicious call", "phishing",
        "code chaiche", "pin chaiche", "otp chaiche", "পিন", "ওটিপি", "পাসওয়ার্ড"
    ]):
        return CaseType.PHISHING_OR_SOCIAL_ENGINEERING

    if any(x in t for x in [
        "wrong number", "wrong recipient", "wrong account", "wrong person", "wrong transfer", "wrong send",
        "bhul number", "vul number", "wrong e pathaisi", "bhul e", "vul e", "ভুল নাম্বার", "ভুল অ্যাকাউন্ট", "ভুল নম্বর", "ভুল এ"
    ]):
        return CaseType.WRONG_TRANSFER

    if any(x in t for x in [
        "twice", "duplicate", "double", "duibar", "2 bar", "double payment", "double charged", "two times",
        "দুইবার", "২ বার", "ডাবল"
    ]):
        return CaseType.DUPLICATE_PAYMENT

    if any(x in t for x in [
        "settlement", "merchant payment pending", "settlement pai nai", "merchant settlement", "settlement pending",
        "মার্চেন্ট পেমেন্ট", "মার্চেন্ট"
    ]):
        return CaseType.MERCHANT_SETTLEMENT_DELAY

    if any(x in t for x in [
        "cash in", "cash-in", "agent", "deposit not added", "cash in hoy nai", "এজেন্ট", "ক্যাশ ইন", "ক্যাশ-ইন"
    ]):
        return CaseType.AGENT_CASH_IN_ISSUE

    if any(x in t for x in [
        "failed", "deducted", "not successful", "payment hoy nai", "taka keteche", "fail hoise", "balance deducted",
        "ব্যালেন্স কেটেছে", "টাকা কেটেছে", "পেমেন্ট হয়নি", "ব্যালেন্স কেটে নিয়েছে", "ব্যালেন্স কেটে"
    ]):
        return CaseType.PAYMENT_FAILED

    if any(x in t for x in [
        "refund", "money back", "return my money", "taka ferot", "refund chai", "টাকা ফেরত", "ফেরত চাই"
    ]):
        return CaseType.REFUND_REQUEST

    if any(x in t for x in [
        "sent", "send", "transfer", "পাঠিয়েছি", "পাঠালাম", "পাঠায়", "পাঠাইছি", "send money"
    ]):
        return CaseType.WRONG_TRANSFER

    return CaseType.OTHER

def match_transaction(complaint_signals: Dict[str, Any], transactions: List[Dict[str, Any]], case_type: Optional[CaseType] = None) -> Optional[Dict[str, Any]]:
    if not transactions:
        return None

    scored_txns = []
    for txn in transactions:
        score = 0
        
        # 1. Transaction ID matches exactly
        txn_id = txn.get("transaction_id") or txn.get("txn_id")
        if txn_id and complaint_signals.get("mentioned_transaction_id"):
            # Normalize and compare
            if str(txn_id).strip().upper() == str(complaint_signals["mentioned_transaction_id"]).strip().upper():
                score += 100
        
        # 2. Amount matches
        txn_amount = txn.get("amount")
        if txn_amount is not None and complaint_signals.get("amount") is not None:
            try:
                if abs(float(txn_amount) - float(complaint_signals["amount"])) < 0.01:
                    score += 40
            except (ValueError, TypeError):
                pass
        
        # 3. Counterparty matches
        counterparty = txn.get("counterparty") or txn.get("recipient") or txn.get("sender") or txn.get("phone")
        if counterparty and complaint_signals.get("mentioned_phone"):
            # Check if mentioned phone matches or is a substring of counterparty
            clean_cp = re.sub(r'\D', '', str(counterparty))
            clean_mp = re.sub(r'\D', '', str(complaint_signals["mentioned_phone"]))
            if clean_mp in clean_cp or clean_cp in clean_mp:
                score += 40

        scored_txns.append((txn, score))

    if not scored_txns:
        return None

    max_score = max(score for txn, score in scored_txns)
    if max_score < 40:
        return None

    # Find all transactions with the max score
    candidates = [txn for txn, score in scored_txns if score == max_score]

    if len(candidates) > 1:
        if case_type == CaseType.DUPLICATE_PAYMENT:
            # Sort candidates by timestamp (prefer the later one)
            def get_timestamp(t):
                return t.get("timestamp") or ""
            candidates.sort(key=get_timestamp)
            return candidates[-1]
        else:
            # Ambiguous match, return None
            return None

    return candidates[0]

def decide_verdict(case_type: CaseType, matched_txn: Optional[Dict[str, Any]], history: List[Dict[str, Any]] = None) -> EvidenceVerdict:
    if not matched_txn:
        return EvidenceVerdict.INSUFFICIENT_DATA

    status = (matched_txn.get("status") or "").lower()
    txn_type = (matched_txn.get("type") or "").lower()

    if case_type == CaseType.WRONG_TRANSFER:
        # Wrong transfer claim holds if a completed transfer/send transaction exists
        if status == "completed":
            target_cp = matched_txn.get("counterparty") or matched_txn.get("recipient") or matched_txn.get("phone")
            if target_cp and history:
                clean_target = re.sub(r'\D', '', str(target_cp))
                matched_id = matched_txn.get("transaction_id") or matched_txn.get("txn_id")
                prior_count = 0
                for txn in history:
                    txn_id = txn.get("transaction_id") or txn.get("txn_id")
                    if txn_id == matched_id:
                        continue
                    txn_cp = txn.get("counterparty") or txn.get("recipient") or txn.get("sender") or txn.get("phone")
                    txn_status = (txn.get("status") or "").lower()
                    if txn_cp and txn_status == "completed":
                        clean_txn_cp = re.sub(r'\D', '', str(txn_cp))
                        if clean_txn_cp == clean_target:
                            prior_count += 1
                if prior_count >= 1:
                    return EvidenceVerdict.INCONSISTENT
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

    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        if status == "pending":
            return EvidenceVerdict.CONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        if status in ["pending", "failed"]:
            return EvidenceVerdict.CONSISTENT
        return EvidenceVerdict.INSUFFICIENT_DATA

    return EvidenceVerdict.INSUFFICIENT_DATA

def get_department(case_type: CaseType, amount: Optional[float] = None, verdict: Optional[EvidenceVerdict] = None) -> Department:
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
    
    # Override for contested/high-risk refund requests
    if case_type == CaseType.REFUND_REQUEST:
        is_high_amount = amount is not None and amount >= 5000
        is_contested = verdict == EvidenceVerdict.INCONSISTENT
        if is_high_amount or is_contested:
            return Department.DISPUTE_RESOLUTION
            
    return CASE_TO_DEPARTMENT.get(case_type, Department.CUSTOMER_SUPPORT)

def calculate_severity(case_type: CaseType, amount: Optional[float], verdict: EvidenceVerdict = EvidenceVerdict.INSUFFICIENT_DATA) -> Severity:
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return Severity.CRITICAL

    # Merchant settlement delay is always medium severity
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return Severity.MEDIUM

    # Agent cash-in issue is high severity if consistent (pending/failed)
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        if verdict == EvidenceVerdict.CONSISTENT:
            return Severity.HIGH
        return Severity.MEDIUM

    # If evidence is inconsistent or insufficient, wrong transfer, payment failed, and duplicate payment drop to medium
    if verdict in [EvidenceVerdict.INCONSISTENT, EvidenceVerdict.INSUFFICIENT_DATA]:
        if case_type in [CaseType.WRONG_TRANSFER, CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT]:
            return Severity.MEDIUM

    # High amount triggers high severity for standard customer complaints
    if amount is not None and amount >= 5000:
        if case_type in [CaseType.WRONG_TRANSFER, CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT]:
            return Severity.HIGH

    if case_type in [CaseType.WRONG_TRANSFER, CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT]:
        return Severity.HIGH

    return Severity.LOW

def needs_human_review(case_type: CaseType, severity: Severity, verdict: EvidenceVerdict, confidence: float) -> bool:
    # Phishing and wrong transfer (except when insufficient data / clarification request) always require review
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return True
        
    if case_type == CaseType.WRONG_TRANSFER:
        if verdict != EvidenceVerdict.INSUFFICIENT_DATA:
            return True
        return False
        
    # Duplicate payments and agent cash-in issues require human review
    if case_type in [CaseType.DUPLICATE_PAYMENT, CaseType.AGENT_CASH_IN_ISSUE]:
        return True
        
    # High severity refund requests (e.g. override to dispute_resolution) require review
    if case_type == CaseType.REFUND_REQUEST:
        if severity in [Severity.HIGH, Severity.CRITICAL] or verdict == EvidenceVerdict.INCONSISTENT:
            return True
            
    # Inconsistent evidence (contested cases) require review
    if verdict == EvidenceVerdict.INCONSISTENT:
        return True
        
    if confidence < 0.75:
        return True
        
    return False
