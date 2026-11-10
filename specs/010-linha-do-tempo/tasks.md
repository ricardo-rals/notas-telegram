# Tasks: Aba Todas como Linha do Tempo

- [X] T001 Testes de `repositorio.buscar_linha_do_tempo` (itens planos, ordem, filtros q/tag/período, paginação, total) e `contar_por_tipo["todas"]` em itens
- [X] T002 `buscar_linha_do_tempo` (UNION ALL de notas sem link e itens de link). T001 deve passar
- [X] T003 Testes do painel: nenhum cartão aninhado, títulos de dia, aviso de notas novas, estados vazios
- [X] T004 Painel, `_notas.html`, filtro `dia_rotulo`, CSS dos títulos. T003 deve passar
- [X] T005 Teste `lento`; suíte; conferir no painel real (screenshot)

## Resultados (2026-11-10)

- `uv run --env-file .env pytest` → 328 passed (inclui `lento`: linha do tempo < 1 s com 10.000 notas).
- Painel real (screenshot): títulos HOJE / 6 DE NOVEMBRO / 5 DE NOVEMBRO; a lista do WhatsApp
  virou 9 cartões de link soltos; nenhum cartão aninhado; Todas conta 20 itens.
- Ajuste extra: na linha do tempo o cartão mostra só a hora (o dia já está no título).
