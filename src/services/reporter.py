import json
from pathlib import Path
from typing import Any

from src.models.catalog import Catalog

_MERMAID_MAX_STEPS = 150


def _cell(v: Any) -> str:
    return str(v).replace("|", "\\|").replace("\n", " ")


def _code(obj: Any) -> str:
    if obj is None:
        return "_(vazio)_\n"
    body = obj if isinstance(obj, str) else json.dumps(obj, indent=2, ensure_ascii=False)
    return f"```json\n{body}\n```\n"


def _mermaid(catalog: Catalog) -> str:
    hosts = list(dict.fromkeys(s.host for s in catalog.flow))
    alias = {h: f"H{i}" for i, h in enumerate(hosts, start=1)}
    lines = ["```mermaid", "sequenceDiagram", "    participant B as Browser"]
    lines += [f"    participant {alias[h]} as {h}" for h in hosts]
    for s in catalog.flow[:_MERMAID_MAX_STEPS]:
        msg = f"{s.index}. {s.method} {s.path_template}".replace(";", ",").replace("#", "")
        lines.append(f"    B->>{alias[s.host]}: {msg}")
        lines.append(f"    {alias[s.host]}-->>B: {s.status}")
    if len(catalog.flow) > _MERMAID_MAX_STEPS:
        lines.append(f"    Note over B: +{len(catalog.flow) - _MERMAID_MAX_STEPS} passos omitidos")
    lines.append("```")
    return "\n".join(lines)


def render_markdown(c: Catalog) -> str:
    out = [
        f"# Catálogo de requests — {c.source_har}",
        "",
        f"Gerado em {c.generated_at}. {c.api_entries} chamadas de API de {c.total_entries} "
        f"requests gravados; {len(c.endpoints)} endpoints distintos; "
        f"{len(c.dependencies)} dependências detectadas.",
        "",
        "> Valores sensíveis (tokens, cookies, senhas, CPF/CNPJ) foram redigidos. "
        "Dependências mostram apenas onde o valor nasce e onde é usado.",
        "",
        "## Endpoints",
        "",
        "| ID | Método | Host | Path | Chamadas | Status | Média (ms) | Auth |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for e in c.endpoints:
        out.append(
            f"| {e.id} | {e.method} | {_cell(e.host)} | `{_cell(e.path_template)}` | "
            f"{e.calls} | {', '.join(map(str, e.statuses))} | {e.avg_ms} | "
            f"{', '.join(e.auth_schemes) or '-'} |"
        )

    out += [
        "",
        "## Fluxo (ordem cronológica)",
        "",
        "| # | Endpoint | Método | Path | Status | ms |",
        "|---|---|---|---|---|---|",
    ]
    for s in c.flow:
        out.append(
            f"| {s.index} | {s.endpoint_id} | {s.method} | `{_cell(s.path_template)}` | "
            f"{s.status} | {s.duration_ms} |"
        )
    out += ["", _mermaid(c), ""]

    out += ["## Dependências entre requests", ""]
    if c.dependencies:
        out += [
            "| De | Origem do valor | Para | Usado em | Tipo | Sensível | Ocorrências |",
            "|---|---|---|---|---|---|---|",
        ]
        for d in c.dependencies:
            out.append(
                f"| {d.from_endpoint} (#{d.first_from_step}) | `{_cell(d.from_location)}` | "
                f"{d.to_endpoint} (#{d.first_to_step}) | `{_cell(d.to_location)}` | "
                f"{d.value_kind} | {'sim' if d.sensitive else 'não'} | {d.occurrences} |"
            )
    else:
        out.append("_Nenhuma dependência detectada._")

    out += ["", "## Detalhe por endpoint", ""]
    for e in c.endpoints:
        out += [
            f"### {e.id} — {e.method} `{e.path_template}`",
            "",
            f"- Host: `{e.host}`",
            f"- Chamadas: {e.calls} (primeira no passo #{e.first_step})",
            f"- Status: {', '.join(map(str, e.statuses))}",
            f"- Content-Type do request: {e.request_content_type or '-'}",
            f"- Auth: {', '.join(e.auth_schemes) or '-'}",
        ]
        if e.query_params:
            out.append("- Query params: " + ", ".join(f"`{q.name}`" for q in e.query_params))
        if e.request_headers:
            out.append("- Headers relevantes: " + ", ".join(f"`{h}`" for h in e.request_headers))
        out += [
            "",
            "**Request — schema**",
            "",
            _code(e.request_schema),
            "**Request — exemplo**",
            "",
            _code(e.request_example),
            "**Response — schema**",
            "",
            _code(e.response_schema),
            "**Response — exemplo**",
            "",
            _code(e.response_example),
        ]
    return "\n".join(out) + "\n"


def write_reports(catalog: Catalog, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out_dir / "catalog.json", out_dir / "catalog.md"
    json_path.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(catalog), encoding="utf-8")
    return json_path, md_path
