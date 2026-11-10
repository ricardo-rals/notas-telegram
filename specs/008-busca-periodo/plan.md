# Implementation Plan: Busca Ampliada e Filtro por Data e Hora

**Branch**: `008-busca-periodo` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

## Summary

Migração `p002`: coluna gerada `link.busca` (`autor`, `site` e a URL com `/ . ? = & -` trocados
por espaço) com índice GIN. `repositorio.buscar` casa `nota.busca` **ou** `nota.id IN (links
cuja link.busca ou previa.busca casa)`; `buscar_links` casa nota, prévia ou link. `de`/`ate`
viram ISO UTC (`regras.periodo_utc`) e filtram `nota.enviada_em` (ou `link.data`) por comparação
de texto, já que tudo é gravado como ISO UTC `+00:00`. No painel, o formulário de busca do topo
ganha dois `<input type="datetime-local">` e os atalhos; `href` passa a carregar `de`/`ate`.

## Constitution Check (2.0.0)

I ✅ nada de rede · II ✅ regra (sem ML, sem fuzzy) · IV ✅ · V ✅ TDD em `periodo_utc`, busca e
painel · VI ✅ uma coluna gerada, nenhum processo novo.

## Project Structure

```text
alembic/versions/p002_link_busca.py
src/notas/regras.py        # periodo_utc
src/notas/repositorio.py   # busca ampliada, de/ate
src/notas/painel.py        # de/ate, atalhos, href
src/notas/templates/lista.html, _painel.html, static/painel.css
tests/test_regras.py, test_repositorio.py, test_painel.py
```
