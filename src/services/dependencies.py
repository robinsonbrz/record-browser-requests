"""Detecta valores que nascem numa resposta e são reutilizados em requests posteriores."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from src.models.catalog import Dependency
from src.models.har import HarEntry
from src.services.har_loader import parse_request_body, parse_response_body
from src.services.normalizer import path_segments
from src.utils.redact import is_sensitive_header, is_sensitive_key, looks_secret

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_INTERESTING_RESP_HEADER = re.compile(r"token|csrf|xsrf|session|location|request-id|etag", re.I)
_SUBSTRING_MIN = 8


@dataclass(frozen=True)
class _Source:
    step: int
    endpoint: str
    location: str
    value: str
    sensitive: bool


def _walk(obj: Any, path: str = "$") -> Iterator[tuple[str, str, Any]]:
    """Gera (json_path, última_chave, valor_escalar)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_key(v, f"{path}.{k}", k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, f"{path}[*]")
    else:
        yield path, "", obj


def _walk_key(obj: Any, path: str, key: str) -> Iterator[tuple[str, str, Any]]:
    if isinstance(obj, dict | list):
        yield from _walk(obj, path)
    else:
        yield path, key, obj


def _candidate(value: Any, min_len: int) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    s = str(value)
    if len(s) < min_len:
        return None
    # Palavras comuns ("active", "pending") geram falso positivo: exige dígito ou tamanho grande
    if not re.search(r"\d", s) and len(s) < 16:
        return None
    return s


def _value_kind(value: str) -> str:
    if looks_secret(value):
        return "jwt"
    if _UUID.match(value):
        return "uuid"
    if value.isdigit():
        return "numeric"
    return "token" if len(value) >= 20 else "string"


def _sources(step: int, endpoint: str, entry: HarEntry, min_len: int) -> list[_Source]:
    out: list[_Source] = []
    body = parse_response_body(entry)
    if body is not None:
        for path, key, val in _walk(body):
            if (s := _candidate(val, min_len)) is not None:
                out.append(
                    _Source(
                        step,
                        endpoint,
                        f"response.body{path[1:] or '$'}",
                        s,
                        is_sensitive_key(key) or looks_secret(s),
                    )
                )
    for h in entry.response.headers:
        name = h.name.lower()
        if name == "set-cookie":
            for line in h.value.split("\n"):
                cname, _, rest = line.partition("=")
                cval = rest.split(";", 1)[0]
                if (s := _candidate(cval, min_len)) is not None:
                    out.append(
                        _Source(step, endpoint, f"response.set-cookie:{cname.strip()}", s, True)
                    )
        elif _INTERESTING_RESP_HEADER.search(name) and (s := _candidate(h.value, min_len)):
            out.append(
                _Source(step, endpoint, f"response.header:{name}", s, is_sensitive_header(name))
            )
    return out


def _sinks(entry: HarEntry) -> Iterator[tuple[str, str, bool]]:
    """Gera (local, valor, sensível) dos pontos onde um request carrega valores."""
    for i, seg in enumerate(path_segments(entry.request.url)):
        yield f"request.path[{i}]", seg, False
    for q in entry.request.queryString:
        yield f"request.query:{q.name}", q.value, is_sensitive_key(q.name)
    for h in entry.request.headers:
        name = h.name.lower()
        if name.startswith(":"):
            continue
        if name == "cookie":
            for part in h.value.split(";"):
                cname, _, cval = part.strip().partition("=")
                yield f"request.cookie:{cname}", cval, True
        else:
            yield f"request.header:{name}", h.value, is_sensitive_header(name)
    kind, body = parse_request_body(entry)
    if kind == "form":
        for k, v in body.items():
            yield f"request.form:{k}", str(v), is_sensitive_key(k)
    elif kind == "json":
        for path, key, val in _walk(body):
            if val is not None and not isinstance(val, bool):
                yield f"request.body{path[1:] or '$'}", str(val), is_sensitive_key(key)
    elif kind == "text":
        yield "request.body", body, False


def detect_dependencies(
    entries: list[HarEntry], endpoint_ids: list[str], min_len: int = 4
) -> list[Dependency]:
    """entries/endpoint_ids alinhados por índice e em ordem cronológica."""
    index: dict[str, _Source] = {}
    deps: dict[tuple[str, str, str, str], Dependency] = {}

    for step, (entry, endpoint) in enumerate(zip(entries, endpoint_ids, strict=True)):
        for location, value, sink_sensitive in _sinks(entry):
            if not value:
                continue
            src = index.get(value)
            if src is None and len(value) >= _SUBSTRING_MIN:
                src = next(
                    (s for v, s in index.items() if len(v) >= _SUBSTRING_MIN and v in value), None
                )
            if src is None or src.step == step:
                continue
            key = (src.endpoint, src.location, endpoint, location)
            if key in deps:
                deps[key].occurrences += 1
                continue
            deps[key] = Dependency(
                from_endpoint=src.endpoint,
                from_location=src.location,
                to_endpoint=endpoint,
                to_location=location,
                first_from_step=src.step,
                first_to_step=step,
                value_kind=_value_kind(src.value),
                sensitive=src.sensitive or sink_sensitive or looks_secret(src.value),
            )
        for src in _sources(step, endpoint, entry, min_len):
            index[src.value] = src  # mantém o produtor mais recente

    return sorted(deps.values(), key=lambda d: (d.first_to_step, d.to_location))
