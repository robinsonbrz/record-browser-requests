from src.services.analyzer import analyze
from src.services.har_loader import load_har
from src.services.reporter import write_reports
from src.settings.settings import Settings

from .conftest import FAKE_JWT, FAKE_SESSION


def _catalog(har_file):
    return analyze(load_har(har_file), har_file.name, Settings())


def test_filters_noise(har_file):
    c = _catalog(har_file)
    assert c.total_entries == 10
    assert c.api_entries == 6
    assert all(s.host == "api.example.test" for s in c.flow)
    assert "OPTIONS" not in {s.method for s in c.flow}


def test_groups_templated_paths(har_file):
    c = _catalog(har_file)
    paths = {(e.method, e.path_template): e for e in c.endpoints}
    assert paths[("GET", "/orders/{id}")].calls == 2
    assert ("GET", "/emissions/{uuid}/status") in paths
    orders = paths[("GET", "/orders")]
    assert [q.name for q in orders.query_params] == ["page", "status"]
    assert orders.auth_schemes == ["Bearer"]
    assert orders.response_schema["properties"]["items"]["items"]["properties"]["total"][
        "type"
    ] == ["null", "number"]


def test_dependencies(har_file):
    c = _catalog(har_file)
    by_id = {e.id: e for e in c.endpoints}
    edges = {
        (
            by_id[d.from_endpoint].path_template,
            d.from_location,
            by_id[d.to_endpoint].path_template,
            d.to_location,
        ): d
        for d in c.dependencies
    }

    token = edges[
        ("/auth/login", "response.body.access_token", "/orders", "request.header:authorization")
    ]
    assert token.sensitive and token.value_kind == "jwt"
    assert (
        "/auth/login",
        "response.set-cookie:SESSION",
        "/orders",
        "request.cookie:SESSION",
    ) in edges
    assert ("/orders", "response.body.items[*].id", "/orders/{id}", "request.path[1]") in edges
    assert any(k[2] == "/emissions" and k[3] == "request.body.order_id" for k in edges)
    assert (
        "/emissions",
        "response.body.emission_id",
        "/emissions/{uuid}/status",
        "request.path[1]",
    ) in edges


def test_reports_contain_no_secrets(har_file, tmp_path):
    json_path, md_path = write_reports(_catalog(har_file), tmp_path / "out")
    for path in (json_path, md_path):
        text = path.read_text()
        for secret in (FAKE_JWT, FAKE_SESSION, "hunter2", "123.456.789-00"):
            assert secret not in text, f"{secret!r} vazou em {path.name}"
    md = md_path.read_text()
    assert "sequenceDiagram" in md and "/orders/{id}" in md
