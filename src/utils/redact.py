"""Mascaramento de segredos e dados pessoais antes de qualquer saída."""

import re
from typing import Any

REDACTED = "<redacted>"

_SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-csrf-token",
    "x-xsrf-token",
}
_SENSITIVE_HEADER_PART = re.compile(
    r"token|secret|key|session|auth|cookie|csrf|xsrf|signature", re.I
)
_SENSITIVE_KEY = re.compile(
    r"pass(word|wd)?|senha|token|secret|otp|cpf|cnpj|card|cvv|cvc|api[_-]?key|"
    r"authorization|session|credential|private[_-]?key|signature|refresh|code_verifier",
    re.I,
)
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*")
_BEARER_RE = re.compile(r"\b(Bearer|Basic|Token)\s+[A-Za-z0-9._~+/=-]+", re.I)
_CPF_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_AUTH_SCHEMES = {"bearer", "basic", "digest", "token", "negotiate", "hmac", "aws4-hmac-sha256"}


def is_sensitive_header(name: str) -> bool:
    lname = name.lower()
    return lname in _SENSITIVE_HEADERS or bool(_SENSITIVE_HEADER_PART.search(lname))


def is_sensitive_key(name: str) -> bool:
    return bool(_SENSITIVE_KEY.search(name))


def redact_text(text: str) -> str:
    text = JWT_RE.sub("<jwt:redacted>", text)
    text = _BEARER_RE.sub(lambda m: f"{m.group(1)} {REDACTED}", text)
    text = _CPF_RE.sub("<cpf:redacted>", text)
    return _CNPJ_RE.sub("<cnpj:redacted>", text)


def redact_header(name: str, value: str) -> str:
    return REDACTED if is_sensitive_header(name) else redact_text(value)


def redact_value(obj: Any, key: str | None = None) -> Any:
    """Redige recursivamente dict/list; chaves sensíveis têm o valor trocado por <redacted>."""
    if key is not None and is_sensitive_key(key) and not isinstance(obj, dict | list):
        return REDACTED
    if isinstance(obj, dict):
        return {k: redact_value(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_value(v, key) for v in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj


def auth_scheme(value: str) -> str:
    """Retorna só o esquema (ex. 'Bearer'), nunca a credencial."""
    first = value.strip().split(" ", 1)[0]
    return first if first.lower() in _AUTH_SCHEMES else "<custom>"


def looks_secret(value: str) -> bool:
    return bool(JWT_RE.search(value))
