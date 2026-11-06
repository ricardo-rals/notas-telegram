# Contrato: Comandos e Configuração

Todos os comandos rodam na raiz do repositório com `uv run --env-file .env`.

## Comandos

| Comando | Efeito | Saída / código |
|---|---|---|
| `python -m notas.bot` | Inicia o bot em long polling | Roda até Ctrl+C. Sai com código 1 se faltar configuração ou o chat não for supergrupo |
| `python -m notas.painel` | Inicia o painel em 127.0.0.1 | Roda até Ctrl+C |
| `python -m notas.importacao <pasta>` | Importa a exportação do Telegram Desktop | Mostra as contagens criadas/existentes/ignoradas/falhas. Código 0 se concluída; 1 se a exportação é inválida ou de outro chat; 2 se já há importação rodando |
| `alembic upgrade head` | Cria ou atualiza o banco em `DATABASE_PATH` | — |

Bot e painel executam `alembic upgrade head` ao iniciar? **Não**: a migração é um passo
explícito do quickstart, para que um processo não altere o esquema enquanto o outro roda.
Ao iniciar, os dois verificam se o banco está na última revisão e, se não estiver, encerram
pedindo a migração.

## Variáveis de ambiente (`.env`, modelo em `.env.example`)

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | só para o bot | — | Token do BotFather |
| `ALLOWED_CHAT_ID` | sim | — | ID do grupo-caderno (ex.: `-1001234567890`) |
| `ALLOWED_USER_ID` | sim | — | ID do dono |
| `DATABASE_PATH` | não | `%LOCALAPPDATA%\notas-telegram\notas.db` | Caminho do SQLite; MUST estar fora do repositório (o processo recusa um caminho dentro dele) |
| `MEDIA_DIR` | não | `data/media` | Pasta da mídia, ignorada pelo Git |
| `PAINEL_PORT` | não | `8000` | Porta do painel; o host é sempre 127.0.0.1 |

`.gitignore` MUST conter: `.env`, `data/`, `*.db`, `*.db-wal`, `*.db-shm`.
