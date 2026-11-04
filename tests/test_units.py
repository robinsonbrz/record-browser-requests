from src.services.normalizer import template_path
from src.services.schema_infer import infer_many
from src.utils.redact import REDACTED, auth_scheme, redact_header, redact_value

from .conftest import FAKE_JWT


def test_template_path():
    assert template_path("https://h/orders/1") == "/orders/{id}"
    assert template_path("https://h/orders/2") == "/orders/{id}"
    assert template_path("https://h/e/3f2b8c1e-1d2a-4b7f-9c3e-0a1b2c3d4e5f/s") == "/e/{uuid}/s"
    assert template_path("https://h/doc/ord-48213") == "/doc/{id}"
    assert template_path("https://h/api/v1/users") == "/api/v1/users"


def test_schema_merge():
    schema = infer_many([{"a": 1, "b": "x"}, {"a": None, "c": [1, 2]}])
    assert schema["type"] == "object"
    assert schema["properties"]["a"]["type"] == ["integer", "null"]
    assert schema["required"] == ["a"]
    assert schema["properties"]["c"] == {"type": "array", "items": {"type": "integer"}}


def test_redaction():
    assert redact_header("Authorization", f"Bearer {FAKE_JWT}") == REDACTED
    assert redact_header("X-Tenant", "acme") == "acme"
    red = redact_value({"password": "x", "nested": {"refresh_token": "y"}, "note": FAKE_JWT})
    assert red == {
        "password": REDACTED,
        "nested": {"refresh_token": REDACTED},
        "note": "<jwt:redacted>",
    }
    assert auth_scheme(f"Bearer {FAKE_JWT}") == "Bearer"
