from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from src.services.analyzer import analyze as analyze_entries
from src.services.har_loader import load_har
from src.services.reporter import write_reports
from src.settings.settings import get_settings

app = typer.Typer(
    help="Grava requests do browser e gera catálogo de endpoints/fluxo.", no_args_is_help=True
)


@app.command()
def record(
    url: Annotated[str, typer.Option(help="URL inicial da aplicação")],
    name: Annotated[str, typer.Option(help="Nome do fluxo (prefixo do arquivo)")] = "flow",
    url_filter: Annotated[
        str | None, typer.Option(help="Glob/regex: grava só URLs que casam")
    ] = None,
    headless: bool = False,
) -> None:
    """Abre o browser e grava o fluxo em recordings/<name>_<timestamp>.har."""
    s = get_settings()
    har = s.recordings_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.har"
    from src.services.recorder import record_flow  # import tardio: analyze não exige Playwright

    record_flow(url, har, s.profile_dir, url_filter=url_filter, headless=headless)
    typer.echo(f"Gravação salva em {har} (contém cookies/tokens — não compartilhe).")
    typer.echo(f"Próximo passo: uv run python -m src.main analyze {har}")


@app.command()
def analyze(
    har: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Arquivo .har")],
    name: Annotated[str | None, typer.Option(help="Subpasta em output/")] = None,
    exclude_host: Annotated[
        list[str] | None, typer.Option(help="Host a ignorar (repetível)")
    ] = None,
) -> None:
    """Gera output/<name>/catalog.json e catalog.md a partir de um HAR."""
    s = get_settings()
    catalog = analyze_entries(load_har(har), har.name, s, exclude_host or [])
    json_path, md_path = write_reports(catalog, s.output_dir / (name or har.stem))
    typer.echo(
        f"{catalog.api_entries}/{catalog.total_entries} requests de API, "
        f"{len(catalog.endpoints)} endpoints, {len(catalog.dependencies)} dependências."
    )
    typer.echo(f"→ {md_path}\n→ {json_path}")


if __name__ == "__main__":
    app()
