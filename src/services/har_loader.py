import base64
import binascii
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

from src.models.har import HarEntry

_TEXTUAL = ("json", "text", "xml", "javascript", "form-urlencoded", "graphql")


def load_har(path: Path) -> list[HarEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = [HarEntry.model_validate(e) for e in data.get("log", {}).get("entries", [])]
    for entry in entries:
        _decode_content(entry)
    entries.sort(key=lambda e: e.startedDateTime)
    return entries


def _decode_content(entry: HarEntry) -> None:
    content = entry.response.content
    if content.encoding != "base64" or content.text is None:
        return
    if not any(t in content.mimeType.lower() for t in _TEXTUAL):
        return
    try:
        content.text = base64.b64decode(content.text).decode("utf-8", errors="replace")
        content.encoding = None
    except (binascii.Error, ValueError):
        pass


def _try_json(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def parse_request_body(entry: HarEntry) -> tuple[str | None, Any]:
    """Retorna (tipo, valor): 'json' | 'form' | 'text' | None."""
    pd = entry.request.postData
    if pd is None:
        return None, None
    mime = pd.mimeType.lower()
    if pd.params:
        return "form", {p.name: p.value for p in pd.params}
    if "form-urlencoded" in mime and pd.text:
        return "form", dict(parse_qsl(pd.text, keep_blank_values=True))
    parsed = _try_json(pd.text)
    if parsed is not None:
        return "json", parsed
    if pd.text:
        return "text", pd.text
    return None, None


def parse_response_body(entry: HarEntry) -> Any:
    content = entry.response.content
    if content.encoding == "base64":
        return None
    return _try_json(content.text)
