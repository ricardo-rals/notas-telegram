# Tasks: Redesenho do Painel

**Input**: Design documents from `/specs/004-redesenho-painel/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/painel-http.md

**Tests**: TDD (Princípio V) nos filtros de cartão, `/novas`, varredura de exportações e estrutura HTML.

## Phase 1: Setup

- [ ] T001 Baixar `InterVariable.woff2` e a licença OFL para `src/notas/static/fontes/` (research R6); se a rede falhar, seguir com a fonte do sistema e registrar em quickstart

## Phase 2: Foundational

- [ ] T002 Escrever em `tests/test_painel.py` os testes da concha (devem falhar): `#painel` com `hx-boost`/`hx-target`/`hx-select`; `#filtros` fora de `#painel` com `#q`, `#f-tipo`, `#f-site`; `<dialog id="foto">`; `<script src="/static/painel.js" defer>`; ocultos com `hx-swap-oob` dentro de `#painel`
- [ ] T003 Reescrever `src/notas/templates/base.html`, `lista.html` e criar `_painel.html` (contrato `GET /`); `painel.py` sempre devolve a página inteira (research R1). T002 deve passar e a suíte da 001–003 continuar verde

## Phase 3: US1 Barra lateral (P1)

- [ ] T004 [US1] Testes: só tipos com notas + Todas, contagens em `<span class="n">`, `aria-current`, tipo do endereço sem notas aparece, sem entrada "Falhas"; aviso `aviso-falhas` com contagem só quando há falha
- [ ] T005 [US1] `painel.py`: `categorias` e `falhas` no contexto (research R8); `_painel.html` com `<nav aria-label="Categorias" class="lateral">` e o aviso. T004 deve passar

## Phase 4: US2 Cartão por tipo (P1)

- [ ] T006 [P] [US2] Testes dos filtros `extensao`, `tamanho`, `mapa`, `contato` (research R7), incluindo entradas inválidas
- [ ] T007 [P] [US2] Testes de cartão: foto com `a.ampliar` + `img`; foto com arquivo ausente → "imagem indisponível" sem `<img>`; documento com selo "PDF", nome e "230 KB"; localização com link OSM `target="_blank"`; contato com `tel:`; texto curto com classe `curto`; vídeo com aviso; ordem conteúdo → meta → ações mantida
- [ ] T008 [US2] Filtros em `painel.py` e `_cartao_nota.html`; `_notas.html` usa a grade. T006 e T007 devem passar

## Phase 5: US3 Aviso de notas novas (P1)

- [ ] T009 [P] [US3] Testes: `contar_novas` em `tests/test_repositorio.py`; `GET /novas` (0 → elemento sem link, ainda com `hx-trigger="every 10s"`; 1 → "1 nota nova · mostrar"; 3 → "3 notas novas"); `#novas` só na 1ª página sem filtro, com `desde` = `enviada_em` da primeira nota; a lista não tem mais `every 10s` em `#notas`
- [ ] T010 [US3] `repositorio.contar_novas`, rota `/novas`, `_novas.html`. T009 deve passar

## Phase 6: US4 + US5 Atalhos e foto ampliada (P2)

- [ ] T011 [US4] [US5] Criar `src/notas/static/painel.js` (research R4); teste que `/static/painel.js` é servido e contém os handlers de `/`, `Ctrl+K`, `Escape` e `showModal`

## Phase 7: US6 Estados vazio e carregamento (P2)

- [ ] T012 [US6] Testes dos quatro estados vazios (research R10) e do bloco `.fantasmas` com `aria-hidden`
- [ ] T013 [US6] `_notas.html` com os estados; CSS dos fantasmas. T012 deve passar

## Phase 8: US7 Importar com um clique (P3)

- [ ] T014 [P] [US7] Testes de `encontrar_exportacoes` em `tests/test_importacao.py`: ordem por data, outro chat, ilegível, pasta base inexistente, filho sem `result.json` ignorado, limite de tempo respeitado (limite 0 → lista vazia sem erro)
- [ ] T015 [P] [US7] Testes de `GET /importar` com `pastas_exportacao` injetado: formulário só nas importáveis; selos; instrução quando não há nenhuma
- [ ] T016 [US7] `importacao.encontrar_exportacoes`, `criar_app(..., pastas_exportacao)`, `importar.html`. T014 e T015 devem passar

## Phase 9: Polish

- [ ] T017 Reescrever `src/notas/static/painel.css` (concha, barra lateral ≤ 720 px, cartões por tipo, dialog, fantasmas, reduced-motion, fonte); teste estrutural mantém `:focus-visible`, `minmax(260px, 1fr)` e `overflow-wrap: anywhere`
- [ ] T018 Atualizar `README.md` (barra lateral, atalhos, importar com um clique)
- [ ] T019 `uv run pytest` completo; validação manual do quickstart §2 numa cópia do banco, registrada no fim de `quickstart.md`

## Dependencies

Setup → Foundational (T002–T003) → US1 → US2 → US3 → US4/5 → US6 → US7 → Polish. T017 pode
começar junto com US2, mas fecha por último.
