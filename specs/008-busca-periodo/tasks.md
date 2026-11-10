# Tasks: Busca Ampliada e Filtro por Data e Hora

- [X] T001 [US1] Testes de repositório: busca acha pelo título/descrição da prévia, autor, site, URL e nome de arquivo, em `buscar` e `buscar_links`; prefixo "lui" acha Luis e Luiz
- [X] T002 [US1] Migração `p002_link_busca.py` e busca ampliada em `repositorio.py`. T001 deve passar
- [X] T003 [US2] Testes de `regras.periodo_utc` (local → UTC, minuto inclusivo, inválido levanta) e de `buscar`/`buscar_links` com `de`/`ate`
- [X] T004 [US2] `periodo_utc`, filtros `de`/`ate`. T003 deve passar
- [X] T005 [US2] Testes do painel: inputs `datetime-local` no `#filtros`, atalhos, período mantido nos links de categoria/tag/site/paginação, 422 para data inválida, "limpar período"
- [X] T006 [US2] Painel, templates e CSS. T005 deve passar
- [X] T007 Teste `lento` (10.000 notas, 5.000 links com prévia: busca ampliada + período ≤ 1 s); README; aplicar `p002` no banco real; conferir "Montenegro" no painel

## Resultados (2026-11-10)

- `uv run --env-file .env pytest` → 302 passed (inclui `lento`: busca ampliada + período < 1 s
  com 10.000 notas e 5.000 links com prévia).
- Banco real em `p002`. No painel real: "montenegro" acha as notas pelo título da prévia do
  Instagram; "lui" acha "Luis"; "ementa" acha o PDF pelo nome do arquivo.
