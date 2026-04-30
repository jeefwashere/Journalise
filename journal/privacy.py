import re


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}"
)
URL_RE = re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.IGNORECASE)
LONG_ID_RE = re.compile(r"\b\d{6,}\b")


def sanitize_text(text: str) -> str:
    sanitized = EMAIL_RE.sub("[redacted-email]", text)
    sanitized = PHONE_RE.sub("[redacted-phone]", sanitized)
    sanitized = URL_RE.sub("[redacted-url]", sanitized)
    sanitized = LONG_ID_RE.sub("[redacted-id]", sanitized)
    return sanitized
