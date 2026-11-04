from collections.abc import Iterable
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from src.models.har import HarEntry
from src.settings.settings import Settings

_API_MIME_HINTS = ("json", "xml", "form-urlencoded", "graphql", "text/plain", "event-stream")


def _host_matches(host: str, patterns: Iterable[str]) -> bool:
    return any(host == p or host.endswith("." + p) for p in patterns)


def is_api_call(entry: HarEntry, settings: Settings, exclude_hosts: Iterable[str] = ()) -> bool:
    method = entry.request.method.upper()
    if method == "OPTIONS":
        return False
    parts = urlsplit(entry.request.url)
    if parts.scheme not in ("http", "https"):
        return False
    host = (parts.hostname or "").lower()
    if _host_matches(host, settings.telemetry_hosts) or _host_matches(host, exclude_hosts):
        return False

    rtype = (entry.resource_type or "").lower()
    if rtype:
        if rtype in settings.api_resource_types:
            return True
        # Submissão de formulário clássica (navegação POST) também faz parte do fluxo
        return rtype == "document" and method != "GET"

    if PurePosixPath(parts.path).suffix.lower() in settings.static_extensions:
        return False
    if method != "GET":
        return True
    resp_mime = entry.response.content.mimeType.lower()
    return any(h in resp_mime for h in _API_MIME_HINTS)


def filter_api_calls(
    entries: list[HarEntry], settings: Settings, exclude_hosts: Iterable[str] = ()
) -> list[HarEntry]:
    hosts = [h.lower() for h in exclude_hosts]
    return [e for e in entries if is_api_call(e, settings, hosts)]
