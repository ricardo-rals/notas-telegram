# Tasks: Armazenamento em PostgreSQL

- [X] T001 Adicionar `psycopg[binary]`; `.gitignore` com `*.dump` e `*.session`; `.env` local com `DATABASE_URL` e `TEST_DATABASE_URL`; `.env.example` sem valores
- [X] T002 Testes de config: `DATABASE_URL` obrigatório, só host local, senha fora da mensagem de erro; `TEST_DATABASE_URL` ≠ `DATABASE_URL` e terminando em `_test`
- [X] T003 `conftest.py`: banco de teste criado se faltar, esquema por sessão, `TRUNCATE` por teste
- [X] T004 Reescrever `tests/test_db.py` para PostgreSQL (tabelas, unicidade, checks, busca sem acento e com prefixo, uma importação por vez, revisão atual, banco sem migração recusado, cascade)
- [X] T005 `alembic/versions/p001_esquema.py`, `alembic/env.py`, `db.py`. T004 deve passar
- [X] T006 `repositorio.py` em PostgreSQL; a suíte da 001–006 volta a passar
- [X] T007 `tests/test_migrar_sqlite.py` (SQLite de revisão antiga e nova, ids preservados, links/tags/prévias, recusa com destino não vazio) e `src/notas/migrar_sqlite.py`
- [X] T008 `backup.py` com `pg_dump` (testes: arquivo gerado e restaurável em banco `_test` temporário; erro sem `pg_dump`)
- [X] T009 README; `alembic upgrade head` no banco `telegram`; migrar o SQLite real; conferir o painel

## Resultados (2026-11-10)

- `uv run --env-file .env pytest` → 296 passed contra PostgreSQL 18 (`telegram_test`), incluindo
  os `lento` (10.000 notas: buscas < 1 s; 5.000 mensagens importadas em 13 s).
- `alembic upgrade head` no banco `telegram`; `migrar_sqlite` copiou 7 notas e 9 prévias e refez
  10 links do SQLite real, que ficou intacto.
