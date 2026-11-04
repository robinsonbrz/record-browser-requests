import base64
import json
from pathlib import Path

import pytest


def _b64(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


# Valor fictício com formato de JWT, montado em runtime só para testar a redação
FAKE_JWT = f"{_b64({'alg': 'none'})}.{_b64({'sub': 'test-user'})}.fakesig"
FAKE_SESSION = "sess-test-000000111111"
API = "https://api.example.test"


def _entry(
    method,
    url,
    *,
    status=200,
    req_headers=None,
    body=None,
    form=None,
    resp=None,
    resp_headers=None,
    rtype="fetch",
    mime="application/json",
    t="00",
    time=50.0,
):
    from urllib.parse import parse_qsl, urlsplit

    entry = {
        "startedDateTime": f"2026-11-04T10:00:{t}.000Z",
        "time": time,
        "_resourceType": rtype,
        "request": {
            "method": method,
            "url": url,
            "headers": [{"name": k, "value": v} for k, v in (req_headers or {}).items()],
            "queryString": [{"name": k, "value": v} for k, v in parse_qsl(urlsplit(url).query)],
        },
        "response": {
            "status": status,
            "headers": [{"name": k, "value": v} for k, v in (resp_headers or {}).items()],
            "content": {"mimeType": mime, "text": json.dumps(resp) if resp is not None else ""},
        },
    }
    if body is not None:
        entry["request"]["postData"] = {"mimeType": "application/json", "text": json.dumps(body)}
    if form is not None:
        entry["request"]["postData"] = {
            "mimeType": "application/x-www-form-urlencoded",
            "params": [{"name": k, "value": v} for k, v in form.items()],
        }
    return entry


def build_entries() -> list[dict]:
    auth = {"Authorization": f"Bearer {FAKE_JWT}", "Cookie": f"SESSION={FAKE_SESSION}"}
    return [
        _entry(
            "GET",
            "https://app.example.test/static/app.js",
            rtype="script",
            mime="application/javascript",
            t="01",
        ),
        _entry("GET", "https://app.example.test/logo.png", rtype="image", mime="image/png", t="02"),
        _entry("POST", "https://www.google-analytics.com/collect", rtype="fetch", t="03"),
        _entry("OPTIONS", f"{API}/auth/login", rtype="preflight", t="04"),
        _entry(
            "POST",
            f"{API}/auth/login",
            form={"username": "tester", "password": "hunter2"},
            resp={"access_token": FAKE_JWT, "expires_in": 3600},
            resp_headers={"Set-Cookie": f"SESSION={FAKE_SESSION}; Path=/; HttpOnly"},
            t="05",
        ),
        _entry(
            "GET",
            f"{API}/orders?page=1&status=open",
            req_headers=auth,
            resp={"items": [{"id": 1001, "total": 10.5}, {"id": 1002, "total": None}]},
            t="06",
        ),
        _entry(
            "GET",
            f"{API}/orders/1001",
            req_headers=auth,
            resp={"id": 1001, "customer": {"name": "Ana", "cpf": "123.456.789-00"}},
            t="07",
        ),
        _entry("GET", f"{API}/orders/1002", req_headers=auth, resp={"id": 1002}, t="08"),
        _entry(
            "POST",
            f"{API}/emissions",
            req_headers=auth,
            body={"order_id": 1001, "amount": 10.5},
            resp={"emission_id": "3f2b8c1e-1d2a-4b7f-9c3e-0a1b2c3d4e5f"},
            status=201,
            t="09",
        ),
        _entry(
            "GET",
            f"{API}/emissions/3f2b8c1e-1d2a-4b7f-9c3e-0a1b2c3d4e5f/status",
            req_headers=auth,
            resp={"state": "done"},
            t="10",
        ),
    ]


@pytest.fixture
def har_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.har"
    path.write_text(json.dumps({"log": {"version": "1.2", "entries": build_entries()}}))
    return path
