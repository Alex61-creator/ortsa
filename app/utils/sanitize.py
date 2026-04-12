import re
from html import escape

def sanitize_string(value: str, max_length: int = 255) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]*>", "", value)
    value = value.replace("{", "").replace("}", "").replace('"""', "")
    value = escape(value)
    return value[:max_length].strip()

def sanitize_email_subject(subject: str) -> str:
    return sanitize_string(subject, max_length=200)