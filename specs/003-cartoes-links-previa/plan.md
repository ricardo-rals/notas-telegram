# Implementation Plan: Cartões de Links com Prévia e Painel Renovado

**Branch**: `003-cartoes-links-previa` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-cartoes-links-previa/spec.md`

## Summary

Cada URL de uma nota de link vira um **item de link** (tabela `link`), com posição, site, data e
autor. A data e o autor vêm da linha do WhatsApp quando ela segue o padrão
`[hh:mm, dd/mm/aaaa] Nome:`. A tabela `link` substitui a `nota_site` da 002. A aba Link passa a
listar itens. As outras abas continuam listando notas, com os links em mini-cartões.

As prévias (título, descrição, miniatura) são buscadas por uma thread no processo do painel,
com `httpx`. Antes de cada acesso, inclusive nos redirecionamentos, o destino é checado contra
endereços locais. O HTML é lido com `html.parser` da stdlib, e o resultado fica no banco e em
`MEDIA_DIR/previas`. Um cabeçalho CSP impede o painel de carregar qualquer coisa de fora.

Uma rota `/baixar/{id}` entrega arquivos com o nome original. O visual vira cartões em CSS grid,
legível de 360 px até telas largas.

## Technical Context

**Language/Version**: Python 3.12, uv

**Primary Dependencies**: as da 002. `httpx` passa a ser declarado direto (já estava instalado,
como dependência do python-telegram-bot). Parser HTML da stdlib.

**Storage**: o mesmo SQLite. Migração `0003`: `link`, `previa`, `previa_fts`; remove `nota_site`.
Miniaturas em `MEDIA_DIR/previas/`.

**Testing**: pytest. Servidor HTTP local (`http.server` em thread) para os testes de prévia;
a checagem de endereço local é desligada só nesses testes, por injeção.

**Target Platform**: Windows 11, máquina do dono

**Project Type**: serviço local: bot + painel (sem processo novo)

**Performance Goals**: aba/troca ≤ 1 s com 10.000 notas e 5.000 itens (SC-005); prévia em ≤ 1 min
para 95% dos links novos com site respondendo (SC-002)

**Constraints**: busca desligável sem nenhuma requisição externa (SC-003); nenhuma página da
rede local acessada (FR-009); nada de fora renderizado como HTML (FR-010)

**Scale/Scope**: 1 usuário; dezenas de milhares de notas; milhares de URLs únicas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Situação | Como o plano atende |
|---|---|---|
| I. Tudo local | ✅ | A busca de título e miniatura é o item (b) permitido. `PREVIAS_LINKS=0` desliga tudo, e a thread nem inicia. Sem LLM, sem API paga |
| II. Regra antes de modelo | ✅ | Linhas do WhatsApp por regex + `strptime`; metadados por tags `og:`/`twitter:`; nenhum ML |
| III. ML com avaliação | N/A | Sem modelo |
| IV. Privacidade | ✅ | Prévias no mesmo banco fora do repositório e em `MEDIA_DIR` (ignorada pelo Git); painel em 127.0.0.1; testes só com páginas locais inventadas |
| V. Testes antes | ✅ | TDD em `linhas_whatsapp`, `itens_de_link`, parser e checagem de destino de `previas`, gravação de `link` e migração `0003` |
| VI. Simplicidade | ✅ com nota | Sem processo novo: a busca é uma thread no painel (research R3). Sem fila externa: a fila é a própria tabela `previa` |
| VII. Só APIs oficiais | ✅ | O Telegram é acessado como antes. As páginas dos links não são apps de mensagem, e só as tags públicas de compartilhamento são lidas |
| VIII. Falha visível | ✅ | Falha de prévia fica em `previa.erro`, e o cartão mostra "prévia indisponível". Falha de mensagem segue a 001 |

**Dependência**: `httpx` não é nova no ambiente (já vem com o python-telegram-bot). Ela é
declarada para não depender de um detalhe de outro pacote.

**Pós-design (Phase 1)**: reavaliado. A remoção de `nota_site` e a mudança na `0002` (research R1)
não violam princípios. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/003-cartoes-links-previa/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── painel-http.md
│   └── config.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml                 # + httpx declarado
.env.example                   # + PREVIAS_LINKS=1
alembic/versions/
├── 0002_nota_site.py          # passa a só criar a tabela (sem reclassificar)
└── 0003_link_previa.py        # nova: link, previa, previa_fts; reconstrói itens; drop nota_site
src/notas/
├── config.py                  # + previas_links: bool
├── db.py                      # NotaSite → Link, Previa
├── regras.py                  # + posicoes, linhas_whatsapp, itens_de_link, itens_do_texto, pode_buscar_previa
├── previas.py                 # novo: parser de metadados, checagem de destino, buscar(), thread do painel
├── repositorio.py             # _gravar_sites → _gravar_links; contar_sites/buscar sobre link; buscar_links; fila de prévias; reconstruir_links
├── bot.py / importacao.py     # passam itens em vez de sites
├── painel.py                  # CSP, /baixar/{id}, aba Link em itens, inicia a thread de prévias
└── templates/
    ├── base.html              # CSS de cartões, grid, foco visível
    ├── _notas.html            # cartão de nota; mini-cartões de link
    ├── _links.html            # novo: lista de cartões de link (aba Link)
    └── _cartao_link.html      # novo: um cartão de link, usado nos dois lugares
tests/
├── fixtures/bot_api/whatsapp_9_links.json   # a mensagem de exemplo, inventada
├── fixtures/paginas/                        # HTML de teste: og completo, só title, malicioso, sem metadados
├── test_regras.py · test_previas.py (novo) · test_repositorio.py · test_db.py · test_painel.py · test_bot.py · test_importacao.py
```

**Structure Decision**: um módulo novo, `previas.py`, porque a busca na rede é uma
responsabilidade separada, com regras de segurança próprias. Ele fica fora de `regras.py` para
que `regras` continue sem rede, banco ou Telegram. O resto é extensão dos módulos da 001/002.

## Complexity Tracking

Sem violações a justificar.
