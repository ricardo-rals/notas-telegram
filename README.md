# Notas

Caderno local a partir de um grupo privado do Telegram. Tudo que você manda no grupo vira uma
nota num SQLite no seu computador, com busca num painel em `http://127.0.0.1:8000`.
Sem LLM, sem API paga; a rede só é usada para falar com o Telegram.

## Preparar o Telegram

1. No @BotFather: `/newbot`, guarde o token; depois `/setprivacy` → **Disable**.
2. Adicione o bot ao grupo-caderno. O grupo precisa ser supergrupo (ID começa com `-100`).
3. Não poste como admin anônimo: essas mensagens são ignoradas.

## Rodar

```powershell
uv sync
Copy-Item .env.example .env        # preencha TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, ALLOWED_USER_ID
uv run --env-file .env alembic upgrade head
uv run --env-file .env python -m notas.bot      # terminal 1
uv run --env-file .env python -m notas.painel   # terminal 2
```

Mensagens perdidas (computador desligado por mais de ~24 h) entram pela exportação JSON do
Telegram Desktop, pelo painel em `/importar` ou com:

```powershell
uv run --env-file .env python -m notas.importacao "C:\caminho\da\exportacao"
```

## Abas e sites

O painel tem uma aba por tipo de nota, cada uma com a sua contagem. Na aba **Link**, há um botão
para cada site, agrupado pelo domínio principal: `www.`, `m.`, `music.youtube.com` etc. contam como
`youtube.com`, e `folha.uol.com.br` conta como `uol.com.br`. O domínio principal sai da lista
pública de sufixos, que vem dentro do pacote `publicsuffixlist` e não é baixada em execução.

Depois de atualizar o código, rode de novo `uv run --env-file .env alembic upgrade head`; é ele
que classifica as notas já guardadas. Para atualizar a lista de sufixos:

```powershell
uv lock --upgrade-package publicsuffixlist; uv sync
```

## Testes

```powershell
uv run pytest            # tudo
uv run pytest -m "not lento"
```

Roteiros de validação: [001](specs/001-captura-notas/quickstart.md) e [002](specs/002-categorias-sites/quickstart.md).
Princípios do projeto: [.specify/memory/constitution.md](.specify/memory/constitution.md).
