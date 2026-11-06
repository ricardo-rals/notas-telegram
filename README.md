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

## Testes

```powershell
uv run pytest            # tudo
uv run pytest -m "not lento"
```

Roteiro completo de validação: [specs/001-captura-notas/quickstart.md](specs/001-captura-notas/quickstart.md).
Princípios do projeto: [.specify/memory/constitution.md](.specify/memory/constitution.md).
