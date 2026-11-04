# record-browser-requests

Grava todos os requests do browser durante um fluxo manual (ex. emissão) e gera um catálogo de
endpoints, a sequência do fluxo e as dependências entre requests — insumo para remontar o fluxo
em outro app.

## Setup
```bash
uv sync
uv run playwright install chromium
```

## 1. Gravar
```bash
uv run python -m src.main record --url https://sua-app.com --name emissao
# opcional: só a API → --url-filter "**/api/**"
```
Abre o Chromium com perfil persistente em `.browser-profile/` (o login fica salvo entre
gravações). Faça login, execute o fluxo e pressione **Enter** no terminal. O HAR vai para
`recordings/emissao_<timestamp>.har`.

> ⚠️ `recordings/` e `.browser-profile/` contêm cookies e tokens reais. Estão no `.gitignore` —
> não compartilhe esses arquivos.

## 2. Analisar
```bash
uv run python -m src.main analyze recordings/emissao_<timestamp>.har [--exclude-host cdn.x.com]
```
Gera em `output/<nome>/`:
- `catalog.md` — tabela de endpoints, fluxo cronológico + diagrama mermaid, dependências
  (ex. `response.body.access_token → request.header:authorization`), schemas e exemplos.
- `catalog.json` — o mesmo em formato estruturado.

Mantém só XHR/Fetch (e POSTs de formulário); descarta estáticos, preflight `OPTIONS` e hosts de
telemetria. Paths são agrupados por template (`/orders/123` → `/orders/{id}`). Tokens, cookies,
senhas, JWTs e CPF/CNPJ são redigidos em toda a saída.

## Configuração
Variáveis com prefixo `RBR_` sobrescrevem [src/settings/settings.py](src/settings/settings.py)
(ex. `RBR_OUTPUT_DIR`, `RBR_RECORDINGS_DIR`, `RBR_PROFILE_DIR`).

## Testes
```bash
uv run pytest && uv run ruff check .
```
