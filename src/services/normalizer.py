import re
from urllib.parse import unquote, urlsplit

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_NUM = re.compile(r"^\d+$")
_HEX = re.compile(r"^[0-9a-f]{16,}$", re.I)
_DIGIT_RUN = re.compile(r"\d{4,}")
_TOKENISH = re.compile(r"^[A-Za-z0-9_\-=.~+]{20,}$")


def template_segment(segment: str) -> str:
    if _NUM.match(segment):
        return "{id}"
    if _UUID.match(segment):
        return "{uuid}"
    if _HEX.match(segment):
        return "{hash}"
    if _TOKENISH.match(segment) and re.search(r"\d", segment) and re.search(r"[A-Za-z]", segment):
        return "{token}"
    if _DIGIT_RUN.search(segment):
        return "{id}"
    return segment


def path_segments(url: str) -> list[str]:
    return [unquote(s) for s in urlsplit(url).path.split("/") if s]


def template_path(url: str) -> str:
    return "/" + "/".join(template_segment(s) for s in path_segments(url))


def endpoint_key(method: str, url: str) -> tuple[str, str, str]:
    host = (urlsplit(url).hostname or "").lower()
    return method.upper(), host, template_path(url)
