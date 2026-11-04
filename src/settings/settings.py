from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração central. Pode ser sobrescrita por variáveis com prefixo RBR_."""

    model_config = SettingsConfigDict(env_prefix="RBR_")

    recordings_dir: Path = Path("recordings")
    output_dir: Path = Path("output")
    profile_dir: Path = Path(".browser-profile")

    api_resource_types: frozenset[str] = frozenset({"xhr", "fetch"})
    static_extensions: frozenset[str] = frozenset(
        {
            ".js",
            ".mjs",
            ".css",
            ".map",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".avif",
            ".woff",
            ".woff2",
            ".ttf",
            ".otf",
            ".eot",
            ".mp4",
            ".webm",
            ".mp3",
            ".wasm",
        }
    )
    telemetry_hosts: frozenset[str] = frozenset(
        {
            "google-analytics.com",
            "analytics.google.com",
            "googletagmanager.com",
            "doubleclick.net",
            "hotjar.com",
            "hotjar.io",
            "segment.io",
            "segment.com",
            "sentry.io",
            "clarity.ms",
            "facebook.com",
            "facebook.net",
            "nr-data.net",
            "newrelic.com",
            "browser-intake-datadoghq.com",
            "mixpanel.com",
            "intercom.io",
            "fullstory.com",
            "amplitude.com",
        }
    )
    ignored_request_headers: frozenset[str] = frozenset(
        {
            "accept",
            "accept-encoding",
            "accept-language",
            "user-agent",
            "origin",
            "referer",
            "connection",
            "host",
            "content-length",
            "cache-control",
            "pragma",
            "dnt",
            "priority",
            "upgrade-insecure-requests",
            "te",
            "if-none-match",
            "if-modified-since",
        }
    )
    # Valores menores que isso não entram na detecção de dependências (evita falsos positivos)
    min_dependency_value_len: int = 4
    example_max_list_items: int = 3
    example_max_str_len: int = 200


def get_settings() -> Settings:
    return Settings()
