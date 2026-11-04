from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from src.models.catalog import Catalog, Endpoint, FlowStep, QueryParam
from src.models.har import HarEntry
from src.services.dependencies import detect_dependencies
from src.services.filters import filter_api_calls
from src.services.har_loader import parse_request_body, parse_response_body
from src.services.normalizer import endpoint_key
from src.services.schema_infer import infer_many
from src.settings.settings import Settings
from src.utils.redact import (
    REDACTED,
    auth_scheme,
    is_sensitive_key,
    redact_header,
    redact_text,
    redact_value,
)


def truncate(obj: Any, max_items: int, max_str: int) -> Any:
    if isinstance(obj, dict):
        return {k: truncate(v, max_items, max_str) for k, v in obj.items()}
    if isinstance(obj, list):
        head = [truncate(v, max_items, max_str) for v in obj[:max_items]]
        return head + ([f"... (+{len(obj) - max_items})"] if len(obj) > max_items else [])
    if isinstance(obj, str) and len(obj) > max_str:
        return obj[:max_str] + "..."
    return obj


def _example(obj: Any, s: Settings) -> Any:
    if obj is None:
        return None
    return truncate(redact_value(obj), s.example_max_list_items, s.example_max_str_len)


def _build_endpoint(
    eid: str, key: tuple[str, str, str], items: list[tuple[int, HarEntry]], s: Settings
) -> Endpoint:
    method, host, path = key
    entries = [e for _, e in items]
    req_bodies, resp_bodies, raw_req = [], [], None
    query: dict[str, str | None] = {}
    headers: dict[str, str] = {}
    schemes: set[str] = set()
    content_type = None

    for e in entries:
        kind, body = parse_request_body(e)
        if kind in ("json", "form"):
            req_bodies.append(body)
        elif kind == "text" and raw_req is None:
            raw_req = body
        if (rb := parse_response_body(e)) is not None:
            resp_bodies.append(rb)
        for q in e.request.queryString:
            if q.name not in query:
                query[q.name] = REDACTED if is_sensitive_key(q.name) else redact_text(q.value)[:100]
        for h in e.request.headers:
            name = h.name.lower()
            if name.startswith(":") or name in s.ignored_request_headers or name.startswith("sec-"):
                continue
            if name == "authorization":
                schemes.add(auth_scheme(h.value))
            if name == "content-type":
                content_type = content_type or h.value
                continue
            headers.setdefault(name, redact_header(name, h.value))

    if raw_req is not None:
        req_example = truncate(redact_text(raw_req), 0, s.example_max_str_len)
    else:
        req_example = _example(req_bodies[0], s) if req_bodies else None

    return Endpoint(
        id=eid,
        method=method,
        host=host,
        path_template=path,
        calls=len(entries),
        first_step=items[0][0],
        statuses=sorted({e.response.status for e in entries}),
        avg_ms=round(sum(e.time for e in entries) / len(entries), 1),
        request_content_type=content_type,
        auth_schemes=sorted(schemes),
        query_params=[QueryParam(name=k, example=v) for k, v in query.items()],
        request_headers=headers,
        request_schema=infer_many(req_bodies),
        response_schema=infer_many(resp_bodies),
        request_example=req_example,
        response_example=_example(resp_bodies[0], s) if resp_bodies else None,
    )


def analyze(
    entries: list[HarEntry], source_name: str, settings: Settings, exclude_hosts: Iterable[str] = ()
) -> Catalog:
    api = filter_api_calls(entries, settings, exclude_hosts)

    groups: dict[tuple[str, str, str], list[tuple[int, HarEntry]]] = defaultdict(list)
    for i, e in enumerate(api):
        groups[endpoint_key(e.request.method, e.request.url)].append((i, e))

    ids = {key: f"E{n:02d}" for n, key in enumerate(groups, start=1)}  # ordem de 1ª aparição
    endpoints = [_build_endpoint(ids[k], k, items, settings) for k, items in groups.items()]

    step_ids: list[str] = []
    flow: list[FlowStep] = []
    for i, e in enumerate(api):
        key = endpoint_key(e.request.method, e.request.url)
        step_ids.append(ids[key])
        flow.append(
            FlowStep(
                index=i,
                started=e.startedDateTime,
                endpoint_id=ids[key],
                method=key[0],
                host=key[1],
                path_template=key[2],
                status=e.response.status,
                duration_ms=round(e.time, 1),
            )
        )

    return Catalog(
        source_har=source_name,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        total_entries=len(entries),
        api_entries=len(api),
        endpoints=endpoints,
        flow=flow,
        dependencies=detect_dependencies(api, step_ids, settings.min_dependency_value_len),
    )
