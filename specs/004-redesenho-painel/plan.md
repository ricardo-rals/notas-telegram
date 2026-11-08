# Implementation Plan: Redesenho do Painel

**Branch**: `004-redesenho-painel` | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-redesenho-painel/spec.md`

## Summary

Só o painel muda. A página vira uma "concha" em CSS grid: barra lateral com as categorias
(contagens da 002/003) e área principal com uma grade de cartões. A região `#painel` (barra
lateral + lista) é trocada inteira pelo HTMX com `hx-boost`, então cada clique atualiza contagens,
destaque e lista de uma vez, com o endereço e o "voltar" do navegador em sincronia.

A atualização automática da lista sai. No lugar, um elemento pequeno pergunta a `/novas?desde=`
a cada 10 s quantas notas são mais novas que a primeira exibida e só mostra o aviso. Um arquivo
`static/painel.js` (servido localmente, CSP `script-src 'self'`) cuida dos atalhos `/`, `Ctrl+K` e
`Esc` e da foto ampliada num `<dialog>` nativo. Cartões fantasmas são CSS puro sobre a classe
`htmx-request`.

A página de importação procura pastas `ChatExport*` com `result.json` em `Downloads` e
`Downloads\Telegram Desktop` e lista as exportações com um botão Importar, que reusa o
`POST /importar` da 001.

## Technical Context

**Language/Version**: Python 3.12, uv

**Primary Dependencies**: as da 003 (FastAPI, Jinja2, HTMX 2 vendorizado). Nenhuma nova.
Fonte Inter (OFL) vendorizada em `static/fontes/`.

**Storage**: o mesmo SQLite; sem migração. Nenhuma tabela nova.

**Testing**: pytest + TestClient. Pasta de downloads falsa em `tmp_path`, injetada em `criar_app`.
O JS é pequeno e testado pela estrutura do HTML (atributos e ids que ele usa) e na validação
manual do quickstart.

**Target Platform**: Windows 11, navegador moderno do dono (Chromium/Firefox atuais)

**Project Type**: serviço local: bot + painel (sem processo novo)

**Performance Goals**: troca de categoria e busca ≤ 1 s com 10.000 notas (SC-005); `/novas` é uma
contagem por índice (`nota_enviada`), barata a cada 10 s; varredura de exportações ≤ 2 s (FR-016)

**Constraints**: nada carregado de fora (CSP da 003, SC-008); funciona sem JS para ver, filtrar e
paginar; contraste ≥ 4,5:1 nos dois temas

**Scale/Scope**: 1 usuário; 9 cartões por tipo; ~6 templates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Situação | Como o plano atende |
|---|---|---|
| I. Tudo local | ✅ | Fonte, CSS e JS servidos pelo próprio painel; "Abrir no mapa" é só um link; nenhuma requisição nova para fora |
| II. Regra antes de modelo | ✅ | Selo de extensão, tamanho legível e coordenadas saem por regra; nenhum ML |
| III. ML com avaliação | N/A | Sem modelo |
| IV. Privacidade | ✅ | Painel continua em 127.0.0.1 com Host/Origin checados; a varredura lê só as duas pastas de downloads e nada é enviado; testes com pasta falsa |
| V. Testes antes | ✅ | TDD em `/novas`, varredura de exportações, filtros de cartão (extensão, tamanho, mapa, contato) e estados vazios |
| VI. Simplicidade | ✅ | Sem framework de front; um arquivo JS curto; sem processo novo; sem tabela nova |
| VII. Só APIs oficiais | ✅ | Exportação do Telegram Desktop como na 001 |
| VIII. Falha visível | ✅ | Falhas viram um aviso permanente no topo enquanto existirem; exportação ilegível aparece marcada, não some |

**Pós-design (Phase 1)**: reavaliado; sem violações. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/004-redesenho-painel/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/painel-http.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/notas/
├── painel.py                 # contexto da barra lateral, /novas, filtros de cartão, varredura de exportações
├── importacao.py             # + encontrar_exportacoes(pastas, chat_id, limite_s)
├── repositorio.py            # + contar_novas(sessao, desde)
├── static/
│   ├── painel.css            # reescrito: concha, barra lateral, cartões por tipo, fantasmas, dialog
│   ├── painel.js             # novo: atalhos, foto ampliada
│   └── fontes/               # novo: InterVariable.woff2 + LICENSE.txt (OFL)
└── templates/
    ├── base.html             # topo com busca, concha, <dialog>, painel.js
    ├── lista.html            # inclui _painel.html
    ├── _painel.html          # novo: barra lateral + aviso de falhas + aviso de notas novas + lista
    ├── _notas.html           # grade de cartões e estados vazios
    ├── _cartao_nota.html     # novo: um cartão por tipo
    ├── _cartao_link.html     # mantido (003)
    ├── _novas.html           # novo: o aviso de notas novas (e o elemento que pergunta)
    └── importar.html         # lista de exportações encontradas + campo manual
tests/
├── test_painel.py            # barra lateral, falhas, cartões por tipo, /novas, estados vazios, importar
└── test_importacao.py        # encontrar_exportacoes
```

**Structure Decision**: tudo dentro dos módulos existentes. `encontrar_exportacoes` fica em
`importacao.py`, ao lado de `ler_exportacao`, que ele reaproveita para validar o chat.

## Complexity Tracking

Sem violações a justificar.
