# Implementation Plan: Captura de Notas do Grupo do Telegram

**Branch**: `001-captura-notas` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-captura-notas/spec.md`

## Summary

Um bot em long polling recebe as mensagens do dono no grupo-caderno. Regras determinísticas
classificam cada mensagem em um de 9 tipos, e o bot grava uma nota por mensagem num SQLite
local, baixando para `data/media` fotos, áudios e documentos de até 20 MB. Um painel
FastAPI + HTMX em 127.0.0.1 lista as notas com busca FTS5 (sem diferença de maiúsculas e
acentos) e filtro por tipo. Uma importação da exportação JSON do Telegram Desktop, pelo
terminal ou pelo painel, preenche lacunas com as mesmas regras, sem duplicar notas.

## Technical Context

**Language/Version**: Python 3.12, gerenciado com uv

**Primary Dependencies**: python-telegram-bot 21+, FastAPI, uvicorn, Jinja2, HTMX (arquivo
local), SQLAlchemy 2, Alembic, python-multipart (formulário do painel)

**Storage**: SQLite em arquivo único fora do repositório (WAL, FTS5); mídia em `data/media`
(ignorada pelo Git)

**Testing**: pytest (+ `fastapi.testclient`, que usa httpx, para o painel)

**Target Platform**: Windows 11, máquina do dono

**Project Type**: serviço local: bot + painel web + comando de importação

**Performance Goals**: nota no painel em ≤ 10 s após o envio (SC-004); busca ≤ 1 s com 10.000
notas (SC-005); importação de 5.000 mensagens < 2 min (SC-008)

**Constraints**: rede só com o Telegram; painel só em 127.0.0.1; sem LLM/API paga; download
≤ 20 MB (limite da Bot API)

**Scale/Scope**: 1 usuário, 1 grupo, até dezenas de milhares de notas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Situação | Como o plano atende |
|---|---|---|
| I. Tudo local | ✅ | Long polling; nenhuma chamada de rede além do Telegram; HTMX servido localmente; busca de título/miniatura de links fora desta fatia |
| II. Regra antes de modelo | ✅ | Classificação 100% por regras (research R2); nenhum ML |
| III. ML com avaliação | N/A | Sem modelo nesta fatia |
| IV. Privacidade | ✅ | SQLite fora do repo (o processo recusa caminho interno); `.env`, `data/`, `*.db` no `.gitignore`; fixtures inventadas; host fixo 127.0.0.1 + checagem de Host/Origin |
| V. Testes antes | ✅ | TDD obrigatório para `regras` (classificação e normalização das duas fontes), `repositorio` (upsert, ignorar duplicata, busca, trava de importação) e importação |
| VI. Simplicidade | ✅ com nota | Bot e painel são os únicos processos de longa duração; a importação pelo terminal é um comando curto e eventual, não um serviço. Sem fila: a importação no painel usa uma thread e a exclusão mútua é um índice do banco |
| VII. Só APIs oficiais | ✅ | Bot API + exportação JSON do Telegram Desktop |
| VIII. Falha visível | ✅ | Toda exceção vira nota `falha` com erro e JSON original; filtro "falhas" no painel; importação reporta falhas |

**Pós-design (Phase 1)**: reavaliado e sem violações. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/001-captura-notas/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── painel-http.md
│   └── cli-config.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml           # uv; dependências e config do pytest
.env.example
.gitignore
alembic.ini
alembic/
└── versions/            # 0001: nota, nota_fts + triggers, importacao
src/notas/
├── config.py            # dataclass lido de os.environ; valida DATABASE_PATH fora do repo
├── db.py                # engine (pragmas WAL/busy_timeout), modelos SQLAlchemy, checagem de revisão
├── regras.py            # MensagemNormalizada, adaptadores Bot API/exportação, classificar(), link
├── repositorio.py       # salvar_ao_vivo (upsert), salvar_importada (ignora), buscar, trava de importação
├── bot.py               # python -m notas.bot: handlers, download de mídia, falha visível
├── importacao.py        # python -m notas.importacao: lê result.json, copia mídia, contagens
├── painel.py            # python -m notas.painel: rotas, middleware Host/Origin, thread de importação
├── templates/           # base.html, lista.html, _notas.html, importar.html, _status.html
└── static/htmx.min.js
tests/
├── fixtures/            # updates da Bot API e mini-exportação, tudo inventado
├── test_regras.py
├── test_repositorio.py
├── test_importacao.py
└── test_painel.py
```

**Structure Decision**: projeto único, layout `src/`, um módulo por responsabilidade e sem
subpacotes. `regras.py` não importa nada do Telegram nem do banco, então é testável com
dicionários puros. `bot.py`, `importacao.py` e `painel.py` são as três portas de entrada
finas sobre `regras` + `repositorio`.

## Complexity Tracking

Sem violações a justificar.
