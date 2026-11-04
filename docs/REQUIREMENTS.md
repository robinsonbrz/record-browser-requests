# Requisitos (anotações originais)

Preciso mapear todos os requests do browser, com todos os endpoints
Mapeando todos os GET, POST, e depois remontar esse fluxo para meu app

```python
from playwright.sync_api import sync_playwright


def record_emission_flow():
    with sync_playwright() as p:
        # 1. Iniciar o navegador
        browser = p.chromium.launch(
            headless=False
        )  # headless=False permite ao utilizador ver e operar

        # 2. Criar contexto e configurar gravação HAR
        context = browser.new_context(
            record_har_path="emissao_flow.har",  # Caminho do ficheiro HAR a gerar
            record_har_mode="full",  # "full" regista corpos de pedidos/respostas e tempos
            record_har_content="embed",  # Incorporar conteúdo de resposta no HAR, tornando o ficheiro autocontido
        )

        page = context.new_page()
        page.goto("https://a-tua-aplicacao-de-emissao.com")

        # 3. Neste ponto, o navegador está aberto. Podes operar manualmente, ou escrever código para clicar automaticamente
        # Aguardar que o utilizador conclua o fluxo de emissão...
        input(
            "Por favor, realiza uma operação de emissão no navegador; após concluir, pressiona Enter aqui para terminar a gravação..."
        )

        # 4. Fechar contexto, ficheiro HAR será escrito no disco
        context.close()
        browser.close()
        print("Gravação HAR concluída: emissao_flow.har")


if __name__ == "__main__":
    record_emission_flow()
```

Pontos-chave:

record_har_mode="full": Garante que o HAR contém informações completas de tempo e tamanho, não apenas o mínimo necessário para reprodução.

record_har_content="embed": Incorpora o conteúdo das respostas (como JSON) diretamente no ficheiro HAR, facilitando a análise posterior e não dependendo de ficheiros externos.

Momento de escrita do ficheiro: O ficheiro HAR só é escrito no disco após context.close() ser chamado. Se o programa falhar inesperadamente antes disso, poderás não obter nada, por isso é recomendável adicionar tratamento de exceções.

Otimização: Gravar Apenas Pedidos de API
A aplicação de emissão pode carregar muitos recursos estáticos (imagens, CSS, JS), tornando o HAR muito extenso. Podes usar o Pydoll e especificar a gravação apenas de pedidos XHR e Fetch, tornando o HAR muito mais limpo e facilitando a análise posterior de endpoints.

```python
# Exemplo de código Pydoll (conceptual)
from pydoll.browser.chromium import Chrome
from pydoll.protocol.network.types import ResourceType

async with Chrome() as browser:
    tab = await browser.start()
    # Gravar apenas pedidos XHR e Fetch
    async with tab.request.record(resource_types=[ResourceType.XHR, ResourceType.FETCH]) as capture:
        await tab.go_to("https://a-tua-aplicacao.com")
        # ... operações do utilizador ...
    capture.save("api_only.har")
```

O objetivo é a análise de todas as requisições gravadas para posterior repetição do fluxo.


