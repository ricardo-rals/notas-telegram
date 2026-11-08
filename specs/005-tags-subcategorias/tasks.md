# Tasks: Tags por Hashtag e Subcategorias de Documentos

**Tests**: TDD (Princípio V).

## Phase 1: US1 Tags (P1)

- [X] T001 [US1] Testes de `regras.tags` (casos válidos, maiúsculas, repetição, `#` em URL, `c#`, `#123`, `##`, 41 caracteres) e de `regras.grupo_documento`
- [X] T002 [US1] Implementar `tags` e `GRUPOS_DOCUMENTO`/`grupo_documento` em `src/notas/regras.py`. T001 deve passar
- [X] T003 [US1] Testes de repositório: `salvar_ao_vivo`/`salvar_importada` gravam tags; edição substitui; `contar_tags` ordenado; `buscar(tag=)` e `buscar_links(tag=)`; migração `0005` preenche notas antigas
- [X] T004 [US1] `Tag` em `db.py`, migração `0005_tag.py`, `_gravar_tags`, `contar_tags`, filtro `tag` em `buscar` e `buscar_links`. T003 deve passar
- [X] T005 [US1] Testes do painel: seção Tags com contagens e `aria-current`; `?tag=` combina com tipo e busca; etiquetas no cartão; links de categoria preservam a tag; oculto `f-tag` na busca
- [X] T006 [US1] Painel e templates. T005 deve passar

## Phase 2: US2 Subcategorias de documento (P2)

- [X] T007 [US2] Testes: botões de grupo só em Documento, só grupos presentes, contagens, `?grupo=pdf` filtra
- [X] T008 [US2] `contar_grupos_documento`, filtro `grupo` em `buscar`, botões no template. T007 deve passar

## Phase 3: Polish

- [X] T009 Teste `lento`: 10.000 notas e 20.000 tags, `contar_tags` e `buscar(tag=)` ≤ 1 s
- [X] T010 README; `uv run pytest`; migrar uma cópia do banco real e conferir o painel

## Resultados (2026-11-08)

- `uv run pytest` → 275 passed (inclui os `lento`: 10.000 notas e 20.000 tags < 1 s).
- Cópia do banco real migrada para `0005` sem erro; nenhuma nota antiga tinha hashtag (0 tags).
- Ajuste no contrato da 004: a barra lateral passou a ser `<aside class="lateral">` com duas
  `<nav>` (Categorias e Tags), para não aninhar navegações.
