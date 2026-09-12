import re
from html import escape
from typing import Any


CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(value: str, limit: int = 120_000) -> str:
    compact = CONTROL_CHARS.sub(" ", value)
    compact = re.sub(r"[ \t]+", " ", compact)
    compact = re.sub(r"\n{4,}", "\n\n", compact)
    return compact.strip()[:limit]


def sanitize_ai_output(value: Any) -> Any:
    if isinstance(value, str):
        no_tags = re.sub(r"<[^>]+>", "", value)
        return escape(no_tags, quote=False)
    if isinstance(value, list):
        return [sanitize_ai_output(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_ai_output(item) for key, item in value.items()}
    return value


def strip_json_fences(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    return text
