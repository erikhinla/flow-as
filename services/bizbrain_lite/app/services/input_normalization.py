import html
import re
from typing import Any


_BLOCK_TAGS = {
    "p": "\n\n",
    "/p": "\n\n",
    "div": "\n",
    "/div": "\n",
    "br": "\n",
    "br/": "\n",
    "br /": "\n",
    "li": "- ",
    "/li": "\n",
    "ul": "\n",
    "/ul": "\n",
    "ol": "\n",
    "/ol": "\n",
    "h1": "# ",
    "/h1": "\n\n",
    "h2": "## ",
    "/h2": "\n\n",
    "h3": "### ",
    "/h3": "\n\n",
    "h4": "#### ",
    "/h4": "\n\n",
    "h5": "##### ",
    "/h5": "\n\n",
    "h6": "###### ",
    "/h6": "\n\n",
}


def _replace_html_tag(match: re.Match[str]) -> str:
    raw = match.group(1).strip().lower()
    tag = raw.split()[0]
    return _BLOCK_TAGS.get(tag, "")


def normalize_text(value: str, *, max_length: int | None = None) -> str:
    text = html.unescape(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = re.sub(r"<([^>]+)>", _replace_html_tag, text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = text.strip()
    if max_length and len(text) > max_length:
        text = text[: max_length - 3].rstrip() + "..."
    return text


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_value(item) for key, item in value.items()}
    return value