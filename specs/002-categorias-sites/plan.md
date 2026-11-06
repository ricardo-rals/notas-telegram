# Implementation Plan: Categorias por Tipo e Sites dos Links

**Branch**: `002-categorias-sites` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-categorias-sites/spec.md`

## Summary

O tipo que já existe é a categoria. O `<select>` de tipo vira uma fileira de abas com
contagens. A subcategoria é o site: para cada nota de link, os adaptadores existentes
extraem as URLs (entidades `url`/`text_link` e regex). `regras.site()` reduz cada URL ao
domínio registrável com a lista pública de sufixos local (`publicsuffixlist`). O resultado
é gravado numa tabela `nota_site` na mesma transação da nota. A migração `0002` cria a
tabela e reclassifica as notas antigas a partir do JSON original que toda nota já guarda
em `bruto`. O painel mostra, na aba Link, um botão por site com contagem.

## Technical Context

**Language/Version**: Python 3.12, uv

**Primary Dependencies**: as da 001 + `publicsuffixlist` (nova; justificada em research R1)

**Storage**: o mesmo SQLite; nova tabela `nota_site` (migração Alembic `0002`)

**Testing**: pytest; TDD em `regras` (site, URLs) e `repositorio` (gravação de sites, reclassificação)

**Target Platform**: Windows 11, máquina do dono

**Project Type**: serviço local: bot + painel web + comando de importação (sem mudança)

**Performance Goals**: aba/site ≤ 1 s com 10.000 notas (SC-003); reclassificação de 10.000 notas < 1 min (SC-004)

**Constraints**: identificação do site sem rede (FR-010); nenhum dado da nota alterado pela classificação (FR-013)

**Scale/Scope**: 1 usuário, dezenas de milhares de notas, centenas de sites distintos

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Situação | Como o plano atende |
|---|---|---|
| I. Tudo local | ✅ | A lista de sufixos vem dentro do pacote; nenhuma chamada de rede; destino de encurtadores não é resolvido |
| II. Regra antes de modelo | ✅ | Site = regra determinística (urlsplit + lista de sufixos); nenhum ML |
| III. ML com avaliação | N/A | Sem modelo |
| IV. Privacidade | ✅ | Nada novo sai da máquina; fixtures inventadas; painel continua em 127.0.0.1 |
| V. Testes antes | ✅ | Testes de `site()`, extração de URLs, gravação de `nota_site` e `reclassificar_sites` escritos e falhando antes do código |
| VI. Simplicidade | ✅ | Nenhum processo novo; reclassificação dentro da migração que o dono já roda; uma tabela, sem fila |
| VII. Só APIs oficiais | ✅ | Usa só o que Bot API e exportação já entregam |
| VIII. Falha visível | ✅ | Link sem site vai para "Sem site identificado", nunca some; erro ao calcular site não impede gravar a nota |

**Nova dependência** (Fluxo de Desenvolvimento): `publicsuffixlist`. Medida que a motivou: a
regra C exige a lista pública de sufixos (~10 mil regras com curingas e exceções). Sem ela,
`folha.uol.com.br` viraria `com.br`. O pacote é puro Python, sem dependências próprias, e não
acessa rede em execução (research R1).

**Pós-design (Phase 1)**: reavaliado e sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/002-categorias-sites/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── painel-http.md   # só o que muda em GET /
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml           # + publicsuffixlist
alembic/versions/
└── 0002_nota_site.py    # nova: tabela nota_site + chama reclassificar_sites
src/notas/
├── db.py                # + modelo NotaSite
├── regras.py            # + MensagemNormalizada.urls, site(), sites_da_nota(), sites_do_texto()
├── repositorio.py       # salvar_* gravam sites; buscar(site=…); contagens; reclassificar_sites()
├── bot.py               # passa sites para salvar_ao_vivo
├── importacao.py        # passa sites para salvar_importada
├── painel.py            # parâmetro site, contagens no contexto
└── templates/
    ├── lista.html       # form sem <select>, campos ocultos tipo/site
    └── _notas.html      # + abas e botões de site no topo do fragmento
tests/
├── fixtures/bot_api/    # + link com vários sites, link sem esquema, domínio com acento
├── test_regras.py       # + site() parametrizado, urls dos dois adaptadores
├── test_repositorio.py  # + nota_site em criar/editar/importar, reclassificar idempotente
├── test_db.py           # + migração 0002 sobre banco da 0001 com notas
└── test_painel.py       # + abas, botões, site=-, site inexistente, contagens
```

**Structure Decision**: mesma estrutura da 001, sem módulo novo. A regra de site fica em
`regras.py`, porque é regra determinística sem banco nem Telegram. A gravação e a
reclassificação ficam em `repositorio.py`.

## Complexity Tracking

Sem violações a justificar.
