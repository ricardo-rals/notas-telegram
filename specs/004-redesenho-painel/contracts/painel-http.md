# Contrato HTTP do painel (004)

Todas as rotas mantêm o middleware da 001/003 (Host, Origin, CSP).

## GET /

Parâmetros como na 003 (`q`, `tipo`, `site`, `pagina`). Sempre devolve a página inteira; o HTMX
recorta `#painel` (research R1). Estrutura garantida:

- `<form id="filtros">` no topo com `<input id="q" type="search" name="q">` e ocultos
  `<input id="f-tipo" name="tipo">`, `<input id="f-site" name="site">`.
- `<div id="painel" hx-boost="true" hx-target="#painel" hx-select="#painel" hx-swap="outerHTML">`:
  - `<nav aria-label="Categorias" class="lateral">` com `<a href>` por categoria, texto
    `Rótulo` e `<span class="n">N</span>`, `aria-current="page"` no atual;
  - `<a class="aviso-falhas" href="/?tipo=falha">N falha(s)</a>` só se houver falha;
  - `<div id="novas" …>` só na 1ª página sem `q`, `tipo` e `site`;
  - `<nav aria-label="Sites">` só em `tipo=link` (003);
  - `<div class="grade">` com `<article class="cartao nota tipo-<tipo>[ falha]">` ou os cartões de link;
  - `<div class="fantasmas" aria-hidden="true">`;
  - os ocultos `f-tipo`/`f-site` com `hx-swap-oob="true"`.
- `<dialog id="foto">` fora de `#painel`, com `<img>`, `<p class="legenda">` e `<button class="fechar">`.
- `<script src="/static/painel.js" defer>`.

`tipo` inválido → 422 (001). `pagina` além da última → 200 com o estado vazio de R10.

## GET /novas?desde=ISO

200 com `<div id="novas" hx-get="/novas?desde=…" hx-trigger="every 10s" hx-swap="outerHTML">`.
Com contagem > 0, contém `<a class="novas" href="/">N nota(s) nova(s) · mostrar</a>` (singular
para 1). `desde` ausente ou vazio = conta todas.

## GET /importar

Além do conteúdo da 001: `<section class="exportacoes">` com um item por exportação encontrada
(nome, data `dd/mm/aaaa`, `N mensagens`), e:
- `importavel` → `<form hx-post="/importar" hx-target="#status">` com `<input type="hidden"
  name="pasta" value="…">` e `<button>Importar</button>`;
- `outro_chat` → selo "outro chat", sem formulário;
- `ilegivel` → selo "exportação ilegível", sem formulário.
Sem exportações → instrução de como exportar. O campo manual da 001 continua.

## POST /importar

Inalterado (001).
