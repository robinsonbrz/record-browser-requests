from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


def record_flow(
    url: str,
    har_path: Path,
    profile_dir: Path,
    url_filter: str | None = None,
    headless: bool = False,
) -> Path:
    """Abre o Chromium com perfil persistente (login reaproveitado) e grava tudo em HAR.

    O HAR só é escrito no disco quando o context fecha — por isso o try/finally.
    """
    har_path.parent.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            record_har_path=str(har_path),
            record_har_mode="full",
            record_har_content="embed",
            record_har_url_filter=url_filter,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(url)
            except PlaywrightError as exc:
                print(
                    f"Aviso: falha ao abrir {url} ({exc.message.splitlines()[0]}). "
                    "Navegue manualmente no browser."
                )
            try:
                input(
                    "Faça login e conclua o fluxo no browser; depois pressione Enter aqui "
                    "para encerrar a gravação... "
                )
            except (KeyboardInterrupt, EOFError):
                print("\nInterrompido — salvando o que foi gravado.")
        finally:
            context.close()
    return har_path
