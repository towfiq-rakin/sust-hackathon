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
    "send us your otp",
    "share your pin",
    "provide your password",
    "give your card number",
    "we will refund you",
    "we have reversed the amount",
    "your account has been recovered",
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
    # If the reply mentions PIN/OTP/password, it is ONLY safe if it is warning the user NOT to share it.
    # We can detect if it contains phrases like "please share", "provide your", "send us", "enter your", "what is your"
    # combined with the sensitive words.
    request_indicators = [
        "share your", "provide your", "send us", "enter your", "what is your", 
        "give us", "tell us", "send your", "submit your", "type your", "need your"
    ]
    
    for indicator in request_indicators:
        if indicator in reply_lower:
            for pattern in SENSITIVE_INFO_PATTERNS:
                if re.search(pattern, reply_lower):
                    return False
                    
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
