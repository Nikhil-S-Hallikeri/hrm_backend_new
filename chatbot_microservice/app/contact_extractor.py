import re

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}")

INVALID_NAMES = {
    "hi", "hii", "hiii", "hello", "hey", "there", "test", "testing",
    "none", "null", "admin", "user", "sir", "ma", "mam", "madam",
    "how", "doing", "good", "morning", "afternoon", "evening", "night",
    "welcome", "who", "what", "where", "when", "why", "can", "could",
    "would", "should", "please", "option", "options", "thanks", "thank",
}

# Words stripped OUT of a candidate string before name extraction
STOP_WORDS = {
    "phone", "number", "email", "mail", "interested", "fees", "fee",
    "price", "looking", "training", "career", "guidance", "want", "need",
    "learn", "hi", "hey", "hello", "there", "i", "m", "im", "am", "is", "the", "in",
    "for", "my", "me", "this", "here", "side", "myself", "name", "call",
    "just", "also", "and", "or", "with", "from", "about", "regarding",
    "sir", "mam", "madam", "dear", "thank", "thanks", "please", "kindly",
    "how", "doing", "you", "your", "yours", "what", "whats", "who", "where",
}

# If ANY of these appear in the candidate string, skip it early as it's a domain/action signal, not a name
DOMAIN_WORDS = {
    "student", "working", "professional", "fresher", "job", "jobs", "seeker",
    "business", "owner", "engineer", "developer", "analyst", "manager",
    "executive", "marketing", "digital", "design", "automation",
    "interested", "looking", "want", "need", "learn", "upskill",
    "expert", "hr", "hiring", "solution", "solutions", "talk", "location",
    "academy", "trading", "skill", "enhancement", "schedule", "interview",
    "update", "status", "reject", "rejected", "company", "details", "info",
    "information", "consultant", "recruiter", "service", "services", "portal",
    "resume", "cv", "apply", "application", "openings", "opening", "vacancy",
    "vacancies", "payroll", "outsourcing", "staffing", "rpo", "workforce",
    "option", "options", "choice", "choices", "help", "support", "contact",
    "call", "callback", "timing", "timings", "salary", "salaries", "leave",
    "leaves", "policy", "policies", "period", "notice", "location", "locations",
    "morning", "afternoon", "evening", "night", "sde", "software", "development",
}

# Ordered by confidence — first match wins
NAME_PATTERNS = [
    # Explicit declarations — highest confidence
    re.compile(r"\bmy name is\s+([a-zA-Z][a-zA-Z\s]{1,50})", re.I),
    re.compile(r"\bname\s*[:\-]\s*([a-zA-Z][a-zA-Z\s]{1,50})", re.I),
    re.compile(r"\bthis is\s+([a-zA-Z][a-zA-Z\s]{1,50})", re.I),
    re.compile(r"\bi'?m\s+([a-zA-Z][a-zA-Z\s]{1,50})", re.I),
    re.compile(r"\bi am\s+([a-zA-Z][a-zA-Z\s]{1,50})", re.I),
    re.compile(r"\bmyself\s+([a-zA-Z][a-zA-Z\s]{1,50})", re.I),
    re.compile(r"\bcall me\s+([a-zA-Z][a-zA-Z\s]{1,50})", re.I),
    # Slightly lower confidence
    re.compile(r"^([a-zA-Z][a-zA-Z\s]{1,50}?)\s+here\b", re.I),
    re.compile(r"^([a-zA-Z][a-zA-Z\s]{1,50}?)\s+this side\b", re.I),
]


def extract_contact_details(text: str) -> dict[str, str]:
    details: dict[str, str] = {}
    lower_text = text.lower()

    email_match = EMAIL_RE.search(text)
    if email_match:
        details["email"] = email_match.group(0).strip(".,;: ").lower()

    phone_match = PHONE_RE.search(text)
    if phone_match:
        phone = re.sub(r"\D", "", phone_match.group(0))
        if phone.startswith("91") and len(phone) > 10:
            phone = phone[-10:]
        if _is_valid_phone(phone):
            details["phone"] = phone

    name = _extract_name(text, details)
    if name:
        details["name"] = name

    # Work status & Company Inference (prevents asking company again when user says fresher/not working)
    fresher_triggers = ("fresher", "student", "entry-level", "entry level", "graduate", "college", "zero experience", "no experience")
    not_working_triggers = ("not working", "unemployed", "no company", "don't have a company", "dont work", "currently not working")

    if any(t in lower_text for t in fresher_triggers):
        details["company"] = "N/A (Fresher)"
    elif any(t in lower_text for t in not_working_triggers):
        details["company"] = "N/A (Not Working)"

    m_comp = re.search(r"\b(?:working (?:at|in|with)|company\s*[:\-]?)\s+([a-zA-Z0-9\s]{2,40})", text, re.I)
    if m_comp:
        comp_val = m_comp.group(1).strip()
        if len(comp_val) > 2 and comp_val.lower() not in ("a fresher", "not working", "a student"):
            details["company"] = comp_val.title()

    return details


def _is_valid_phone(phone: str) -> bool:
    if len(phone) != 10:
        return False
    if phone == phone[0] * len(phone):  # reject 9999999999 etc.
        return False
    return phone[0] in {"6", "7", "8", "9"}


def _extract_name(text: str, details: dict[str, str]) -> str | None:
    """
    STRICT ZERO-HALLUCINATION NAME EXTRACTOR:
    Extracts a person's name ONLY when:
    1. The user explicitly uses a self-identification phrase ("my name is", "i am", "name:", "call me", etc.)
    2. OR the message explicitly includes an email or phone AND a short candidate name alongside it.
    
    NEVER guesses names from arbitrary sentences, queries, or button clicks.
    """
    if not text or not text.strip():
        return None

    # Condition 1: Explicit pattern match ("my name is...", "i am...", "this is...", "call me...", "name:...")
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            raw = match.group(1)
            cleaned = _clean_name_words(raw)
            if cleaned:
                return cleaned

    # Condition 2: Text provided alongside explicit contact info (email or phone)
    if details.get("phone") or details.get("email"):
        before_contact = PHONE_RE.split(text, maxsplit=1)[0]
        before_contact = EMAIL_RE.split(before_contact, maxsplit=1)[0].strip()
        before_contact = re.sub(r"[,;|\-\:\n\r]+", " ", before_contact).strip()
        if before_contact and len(before_contact.split()) <= 4:
            cleaned = _clean_name_words(before_contact)
            if cleaned:
                return cleaned

    # No explicit self-identification or contact submission -> Return None (never guess!)
    return None


def _clean_name_words(raw: str) -> str | None:
    """
    Takes a raw string candidate and returns a cleaned, capitalized name
    or None if it doesn't look like a real name.
    """
    raw_lower = raw.lower()
    raw_words = set(re.findall(r"\b[a-z]+\b", raw_lower))
    if raw_words.intersection(DOMAIN_WORDS):
        return None
    if raw_words.intersection(INVALID_NAMES):
        return None

    # Strip emails, phones, punctuation
    cleaned = EMAIL_RE.sub(" ", raw)
    cleaned = PHONE_RE.sub(" ", cleaned)
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()

    if not cleaned:
        return None

    # Filter word by word
    words = [
        w for w in cleaned.split()
        if w.isalpha()
        and len(w) > 1
        and w not in STOP_WORDS
    ]

    # A name should be 1–4 words
    if not (1 <= len(words) <= 4):
        return None

    # Reject single very short words (likely filler that slipped through)
    if len(words) == 1 and len(words[0]) < 3:
        return None

    joined = " ".join(words)
    if joined in INVALID_NAMES:
        return None

    return " ".join(w.capitalize() for w in words)
