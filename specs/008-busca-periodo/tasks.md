# Tasks: Busca Ampliada e Filtro por Data e Hora

- [ ] T001 [US1] Testes de repositório: busca acha pelo título/descrição da prévia, autor, site, URL e nome de arquivo, em `buscar` e `buscar_links`; prefixo "lui" acha Luis e Luiz
- [ ] T002 [US1] Migração `p002_link_busca.py` e busca ampliada em `repositorio.py`. T001 deve passar
- [ ] T003 [US2] Testes de `regras.periodo_utc` (local → UTC, minuto inclusivo, inválido levanta) e de `buscar`/`buscar_links` com `de`/`ate`
- [ ] T004 [US2] `periodo_utc`, filtros `de`/`ate`. T003 deve passar
- [ ] T005 [US2] Testes do painel: inputs `datetime-local` no `#filtros`, atalhos, período mantido nos links de categoria/tag/site/paginação, 422 para data inválida, "limpar período"
- [ ] T006 [US2] Painel, templates e CSS. T005 deve passar
- [ ] T007 Teste `lento` (10.000 notas, 5.000 links com prévia: busca ampliada + período ≤ 1 s); README; aplicar `p002` no banco real; conferir "Montenegro" no painel
