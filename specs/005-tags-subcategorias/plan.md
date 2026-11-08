# Implementation Plan: Tags por Hashtag e Subcategorias de Documentos

**Branch**: `005-tags-subcategorias` | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)

## Summary

`regras.tags(texto)` extrai hashtags por regex, removendo antes as URLs. Uma tabela `tag
(nota_id, nome)` guarda o resultado; `salvar_ao_vivo` e `salvar_importada` a regravam junto com os
links. A migração `0005` cria a tabela e preenche a partir de `nota.texto`. No painel, a barra
lateral ganha a seção Tags; `?tag=` filtra `buscar` e `buscar_links`. Os grupos de documento são
um dicionário extensão → grupo em `regras.py`; o filtro é um `OR` de `LIKE '%.ext'` sobre
`lower(arquivo_nome)`, e as contagens são feitas em Python sobre os nomes dos documentos.

## Technical Context

**Language/Version**: Python 3.12, uv · **Dependencies**: nenhuma nova · **Storage**: SQLite,
migração `0005` (`tag`, índice `tag_nome`) · **Testing**: pytest (TDD em `tags`, `grupo_documento`,
gravação, migração e painel) · **Performance**: filtro por tag via `nota.id IN (SELECT nota_id
FROM tag WHERE nome = ?)` com índice; contagem `GROUP BY nome` (SC-003)

## Constitution Check

| Princípio | Situação |
|---|---|
| I. Tudo local | ✅ nada de rede |
| II. Regra antes de modelo | ✅ regex e tabela de extensões; a categorização é do próprio dono |
| III. ML | N/A |
| IV. Privacidade | ✅ mesmo banco; fixtures inventadas |
| V. Testes antes | ✅ |
| VI. Simplicidade | ✅ uma tabela, sem coluna derivada para o grupo de documento |
| VII/VIII | ✅ inalterados |

## Project Structure

```text
alembic/versions/0005_tag.py     # tabela tag + preenchimento
src/notas/regras.py              # tags(), GRUPOS_DOCUMENTO, grupo_documento()
src/notas/db.py                  # Tag
src/notas/repositorio.py         # _gravar_tags, contar_tags, contar_grupos_documento, filtros tag/grupo
src/notas/painel.py              # ?tag=, ?grupo=, contexto
src/notas/templates/             # seção Tags, botões de grupo, etiquetas no cartão
tests/                           # test_regras, test_repositorio, test_db, test_painel
```

## Complexity Tracking

Sem violações.
