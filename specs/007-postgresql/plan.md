# Implementation Plan: Armazenamento em PostgreSQL

**Branch**: `007-postgresql` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

## Summary

Driver `psycopg` 3. Nova cadeia Alembic com uma migração `p001` que cria o esquema inteiro das
fatias 001–006 em PostgreSQL; as migrações SQLite saem (ficam no histórico do Git). A busca troca
FTS5 por colunas `tsvector` geradas (`nota.busca`, `previa.busca`) com a configuração de busca
`notas` = `simple` + `unaccent`, e índices GIN; a consulta vira `palavra:* & palavra:*`.
`repositorio` troca `sqlite.insert` por `postgresql.insert` (mesma API de `ON CONFLICT`).
`migrar_sqlite.py` lê o SQLite com `sqlite3` (só as colunas que existirem) e grava no PostgreSQL.
`backup.py` chama `pg_dump -Fc` com a senha em `PGPASSWORD`.

## Technical Context

Python 3.12 · SQLAlchemy 2 + `psycopg[binary]` · PostgreSQL 18 local · testes em `telegram_test`
(criado pelo `conftest` se faltar), esquema recriado uma vez por sessão e `TRUNCATE` entre testes.

## Constitution Check (v2.0.0)

| Princípio | Situação |
|---|---|
| I | ✅ banco local, nenhuma rede nova |
| IV | ✅ só `127.0.0.1`/`localhost`; senha só no `.env`; testes em banco `_test` |
| V | ✅ testes de esquema, busca, migração do SQLite e config antes do código |
| VI | ✅ um banco PostgreSQL, nenhum processo novo |
| VIII | ✅ falha de conexão e de backup visíveis |

## Project Structure

```text
alembic/env.py, alembic/versions/p001_esquema.py   # nova cadeia (remove 0001–0005)
src/notas/config.py      # database_url (+ checagem de host), pg_bin
src/notas/db.py          # criar_engine(url), BigInteger, migrar(url), exigir_revisao_atual
src/notas/repositorio.py # postgresql.insert, busca tsvector
src/notas/migrar_sqlite.py  # novo
src/notas/backup.py      # pg_dump
src/notas/{bot,painel,importacao}.py  # criar_engine(cfg.database_url)
tests/conftest.py        # banco _test, truncate
tests/test_db.py         # reescrito para PostgreSQL; test_migrar_sqlite.py novo
```

## Complexity Tracking

Sem violações (constituição 2.0.0).
