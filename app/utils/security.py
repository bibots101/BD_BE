import html
import re


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def sanitize_text(value: str) -> str:
    if value is None:
        return ""
    return html.escape(value.strip())


def is_valid_email(value: str) -> bool:
    if not value:
        return False
    return bool(EMAIL_REGEX.match(value.strip()))
