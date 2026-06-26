import json
import logging
from typing import Dict, Any, Optional, List
from app.schemas import (
    TicketRequest, TicketResponse, EvidenceVerdict, CaseType, Severity, Department
)
from app import rules
from app import safety
from app.gemini_client import call_gemini_api, build_prompt

logger = logging.getLogger(__name__)

def generate_rule_based_reply(case_type: CaseType, ticket_id: str) -> str:
    """
    Generates a type-specific safe customer reply.
    """
    replies = {
        CaseType.WRONG_TRANSFER: (
            "We have noted your wrong transfer concern. Please do not share your PIN, OTP, or password with anyone. "
            "Our dispute resolution team is investigating the target account and transaction status."
        ),
        CaseType.PAYMENT_FAILED: (
            "We are reviewing your failed payment request. If your balance was deducted, the amount will be "
            "automatically refunded within 72 hours. Do not share your PIN, OTP, or passwords."
        ),
        CaseType.REFUND_REQUEST: (
            "We have received your refund request. Our support team will verify the details with the merchant "
            "and update you shortly. Please keep your account details secure."
        ),
        CaseType.DUPLICATE_PAYMENT: (
            "We have noted your concern regarding double payment. If you were charged twice for the transaction, "
            "the duplicate amount will be reversed back to your account after verification."
        ),
        CaseType.MERCHANT_SETTLEMENT_DELAY: (
            "We are investigating the merchant settlement delay. Our operations team is processing pending payouts "
            "and will coordinate with you. Please do not share sensitive credentials."
        ),
        CaseType.AGENT_CASH_IN_ISSUE: (
            "We have received your complaint regarding agent cash-in. We are verifying the deposit ledger with the agent "
            "to credit the amount. Please stay secure."
        ),
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING: (
            "IMPORTANT: We will never ask for your PIN, OTP, or password. Your fraud report has been escalated "
            "to our fraud and risk team immediately. Please secure your account credentials."
        ),
        CaseType.OTHER: safety.SAFE_DEFAULT_REPLY
    }
    return replies.get(case_type, safety.SAFE_DEFAULT_REPLY)

def generate_rule_based_action(case_type: CaseType) -> str:
    """
    Generates a type-specific next action for the support agent.
    """
    actions = {
        CaseType.WRONG_TRANSFER: "Verify wrong transfer details and escalate to dispute resolution for holding/reversal.",
        CaseType.PAYMENT_FAILED: "Check gateway settlement status for matching transaction and initiate refund if balance deducted.",
        CaseType.REFUND_REQUEST: "Verify refund request details and coordinate merchant guidelines compliance.",
        CaseType.DUPLICATE_PAYMENT: "Check transaction history for double debit and process reversal.",
        CaseType.MERCHANT_SETTLEMENT_DELAY: "Verify merchant settlement reports and process pending payouts.",
        CaseType.AGENT_CASH_IN_ISSUE: "Validate agent deposit details and update user ledger.",
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING: "Flag customer account, suspend target fraud account if internal, and escalate to fraud team.",
        CaseType.OTHER: "Review ticket details manually and route appropriately."
    }
    return actions.get(case_type, "Review ticket details manually and route appropriately.")

def create_fallback_response(request: TicketRequest, rule_case: CaseType, matched_txn: Optional[Dict[str, Any]], rule_verdict: EvidenceVerdict, reason: str) -> TicketResponse:
    """
    Constructs a valid, safe fallback response using deterministic rules.
    """
    logger.info(f"Generating fallback response for ticket {request.ticket_id} due to: {reason}")
    
    # Extract values using rules
    signals = rules.extract_signals(request.complaint)
    amount = signals.get("amount")
    
    severity = rules.calculate_severity(rule_case, amount)
    department = rules.get_department(rule_case, amount, rule_verdict)
    
    # Construct strings
    relevant_txn_id = matched_txn.get("transaction_id") or matched_txn.get("txn_id") if matched_txn else None
    
    agent_summary = f"Customer submitted ticket reporting {rule_case.value.replace('_', ' ')}."
    if relevant_txn_id:
        agent_summary += f" Matched with transaction {relevant_txn_id}."
        
    next_action = generate_rule_based_action(rule_case)
    customer_reply = safety.sanitize_customer_reply(generate_rule_based_reply(rule_case, request.ticket_id))
    
    # Fallback response has a baseline confidence
    confidence = 0.50
    
    # Determine human review requirement
    human_review = rules.needs_human_review(rule_case, severity, rule_verdict, confidence)
    
    return TicketResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=str(relevant_txn_id) if relevant_txn_id else None,
        evidence_verdict=rule_verdict,
        case_type=rule_case,
        severity=severity,
        department=department,
        agent_summary=agent_summary,
        recommended_next_action=next_action,
        customer_reply=customer_reply,
        human_review_required=human_review,
        confidence=confidence,
        reason_codes=["fallback_used", reason]
    )

def clean_json_text(text: str) -> str:
    """
    Cleans up common markdown wraps or surrounding garbage from Gemini response.
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def analyze_ticket_flow(request: TicketRequest) -> TicketResponse:
    """
    Main entry point for analyzing a ticket.
    """
    # 1. First extract signals & run deterministic matching
    signals = rules.extract_signals(request.complaint)
    matched_txn = rules.match_transaction(signals, request.transaction_history)
    
    rule_case = rules.detect_case_type(request.complaint)
    rule_verdict = rules.decide_verdict(rule_case, matched_txn)
    
    # If Gemini is enabled, try AI path
    try:
        # Construct input payload json for Gemini prompt
        payload = {
            "ticket_id": request.ticket_id,
            "complaint": request.complaint,
            "language": request.language,
            "channel": request.channel,
            "user_type": request.user_type,
            "extracted_signals": signals,
            "matched_transaction": matched_txn,
            "transaction_history": request.transaction_history
        }
        payload_str = json.dumps(payload, indent=2, default=str)
        prompt = build_prompt(payload_str)
        
        # Call API
        ai_raw_response = call_gemini_api(prompt)
        
        if ai_raw_response:
            # Parse response
            cleaned_response = clean_json_text(ai_raw_response)
            ai_data = json.loads(cleaned_response)
            
            # 2. Normalize and validate enums
            # Evidence Verdict validation
            try:
                evidence_verdict = EvidenceVerdict(ai_data.get("evidence_verdict"))
            except ValueError:
                evidence_verdict = rule_verdict
                
            # Case Type validation
            try:
                case_type = CaseType(ai_data.get("case_type"))
            except ValueError:
                case_type = rule_case
                
            # Enforce deterministic severity and department calculation
            severity = rules.calculate_severity(case_type, signals.get("amount"))
            department = rules.get_department(case_type, signals.get("amount"), evidence_verdict)
                
            # Set relevant transaction ID (guarantee it exists in list or is matched)
            relevant_txn_id = ai_data.get("relevant_transaction_id")
            if relevant_txn_id:
                # Check if it exists in history
                txn_ids = [str(txn.get("transaction_id") or txn.get("txn_id")) for txn in request.transaction_history]
                if str(relevant_txn_id) not in txn_ids:
                    # Fallback to matched txn if Gemini selected an invalid txn ID
                    relevant_txn_id = matched_txn.get("transaction_id") or matched_txn.get("txn_id") if matched_txn else None
            else:
                relevant_txn_id = matched_txn.get("transaction_id") or matched_txn.get("txn_id") if matched_txn else None

            # 3. Apply safety checker
            customer_reply = str(ai_data.get("customer_reply", ""))
            sanitized_reply = safety.sanitize_customer_reply(customer_reply)
            
            # If safety rules altered the reply, flag it
            safety_triggered = (customer_reply != sanitized_reply)
            
            # Reason codes normalization
            raw_codes = ai_data.get("reason_codes", [])
            reason_codes = [str(code) for code in raw_codes] if isinstance(raw_codes, list) else ["ai_reasoning"]
            if safety_triggered:
                reason_codes.append("safety_sanitizer_triggered")
                
            # Confidence normalizer
            try:
                confidence = float(ai_data.get("confidence", 0.9))
            except (ValueError, TypeError):
                confidence = 0.85
                
            # Force human review if safety was triggered or based on rules
            human_review = rules.needs_human_review(case_type, severity, evidence_verdict, confidence)
            if safety_triggered:
                human_review = True
                
            return TicketResponse(
                ticket_id=request.ticket_id,
                relevant_transaction_id=str(relevant_txn_id) if relevant_txn_id else None,
                evidence_verdict=evidence_verdict,
                case_type=case_type,
                severity=severity,
                department=department,
                agent_summary=str(ai_data.get("agent_summary", f"Gemini analyzed ticket {request.ticket_id}")),
                recommended_next_action=str(ai_data.get("recommended_next_action", "Manual ticket review")),
                customer_reply=sanitized_reply,
                human_review_required=human_review,
                confidence=confidence,
                reason_codes=reason_codes
            )
            
    except Exception as e:
        logger.error(f"Error parsing Gemini response or executing analyzer: {e}", exc_info=True)
        # Fall through to fallback engine
        return create_fallback_response(request, rule_case, matched_txn, rule_verdict, "gemini_parsing_error")

    # If Gemini returned None or empty or disabled
    return create_fallback_response(request, rule_case, matched_txn, rule_verdict, "gemini_api_skipped")
