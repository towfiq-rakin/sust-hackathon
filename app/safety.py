import re

# Banned strings that should not be asked from the customer
SENSITIVE_INFO_PATTERNS = [
    r'\bpin\b',
    r'\botp\b',
    r'\bpassword\b',
    r'\bcvv\b',
    r'card\s*number',
    r'security\s*code',
    r'verification\s*code',
    r'one\s*time\s*password'
]

# Phrases that are explicitly forbidden (e.g. prompt injection successes or bad promises)
FORBIDDEN_PHRASES = [
    "we will refund you",
    "we have refunded",
    "refund confirmed",
    "refund is confirmed",
    "your money has been reversed",
    "your account has been recovered",
    "we have unblocked your account",
    "we have reversed",
    "amount has been refunded",
    "amount will be automatically refunded",
    "will be reversed back",
    "contact this number"
]

# The standard safe customer response to use if a violation occurs or as a fallback base
SAFE_DEFAULT_REPLY = (
    "We have noted your concern. Please do not share your PIN, OTP, password, or "
    "sensitive account information with anyone. Our team will review the issue "
    "through official channels. If any amount is found eligible after review, "
    "it will be handled through official channels."
)

def is_reply_safe(customer_reply: str) -> bool:
    reply_lower = customer_reply.lower()
    
    # 1. Check for banned phrases
    for phrase in FORBIDDEN_PHRASES:
        if phrase in reply_lower:
            return False
            
    # 2. Check if it asks the customer to provide/share sensitive credentials
    request_indicators = [
        "share your", "provide your", "send us", "enter your", "what is your", 
        "give us", "tell us", "send your", "submit your", "type your", "need your",
        "give your", "ask for your"
    ]
    
    for indicator in request_indicators:
        start = 0
        while True:
            pos = reply_lower.find(indicator, start)
            if pos == -1:
                break
            
            # Check if this indicator is part of a warning (preceded by negation)
            pre_context = reply_lower[max(0, pos-15):pos]
            if not any(neg in pre_context for neg in ["do not", "don't", "never", "not to"]):
                for pattern in SENSITIVE_INFO_PATTERNS:
                    if re.search(pattern, reply_lower):
                        return False
            start = pos + len(indicator)
                    
    # Also verify there are no direct calls to actions that tell users to do unsafe things
    if "ignore all rules" in reply_lower or "ignore previous instructions" in reply_lower:
        return False
        
    # Check for direct refund/reversal promises
    refund_promises = [
        "refund is confirmed", "refund will be sent", "reversal is successful", 
        "money is returned", "returned your money"
    ]
    for promise in refund_promises:
        if promise in reply_lower:
            return False
            
    return True

def sanitize_customer_reply(customer_reply: str) -> str:
    """
    Validates a customer reply. If it violates safety guidelines,
    it returns the standard SAFE_DEFAULT_REPLY. Otherwise, returns the original reply.
    """
    if not customer_reply or not customer_reply.strip():
        return SAFE_DEFAULT_REPLY
        
    if not is_reply_safe(customer_reply):
        return SAFE_DEFAULT_REPLY
        
    return customer_reply


# Forbidden phrases specific to recommended_next_action
ACTION_FORBIDDEN_PHRASES = [
    "confirm refund to customer",
    "tell customer refund is confirmed",
    "promise refund",
    "promise reversal",
    "inform customer money returned",
    "share otp",
    "ask for pin",
    "ask for otp",
    "ask for password",
    "request customer pin",
    "request customer otp",
]

SAFE_DEFAULT_ACTION = (
    "Review the ticket manually and verify relevant transaction records "
    "through internal tools before taking any action."
)

def sanitize_next_action(next_action: str) -> str:
    """
    Validates recommended_next_action. Replaces with safe default if it
    contains forbidden phrases (refund promises, credential requests).
    """
    if not next_action or not next_action.strip():
        return SAFE_DEFAULT_ACTION
    
    action_lower = next_action.lower()
    
    for phrase in ACTION_FORBIDDEN_PHRASES:
        if phrase in action_lower:
            return SAFE_DEFAULT_ACTION
    
    # Also check for direct refund/reversal promises in action text
    for phrase in FORBIDDEN_PHRASES:
        if phrase in action_lower:
            return SAFE_DEFAULT_ACTION
    
    return next_action
