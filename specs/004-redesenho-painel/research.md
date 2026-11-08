# Research: Redesenho do Painel

## R1. Concha e troca parcial com `hx-boost`

- **Decision**: `#painel` (barra lateral + avisos + lista) é a unidade de troca. O contêiner tem
  `hx-boost="true" hx-target="#painel" hx-select="#painel" hx-swap="outerHTML"`. Links de categoria,
  site e paginação são `<a href>` comuns: sem JS funcionam como antes; com JS, o HTMX pede a página,
  recorta `#painel` e troca, e `hx-boost` já empurra o endereço para o histórico.
  O servidor devolve a página inteira sempre; `hx-select` recorta. Isso remove o ramo
  "fragmento quando HX-Request" e mantém um único template por rota.
- **Rationale**: uma regra só para tudo que muda junto (contagens, destaque, lista). O "voltar"
  funciona pelo histórico do HTMX.
- **Alternatives considered**: trocar só a lista e atualizar a barra por `hx-swap-oob` (dois
  pontos de verdade); SPA (contra o Princípio VI).

## R2. Busca fora de `#painel`

- **Decision**: o formulário de busca fica no topo, fora de `#painel`, para o campo não perder
  foco ao digitar. Ele leva `tipo` e `site` em campos ocultos com ids fixos; `_painel.html` os
  atualiza com `hx-swap-oob` a cada troca, para a busca respeitar a categoria atual.
  `hx-get="/" hx-target="#painel" hx-select="#painel" hx-swap="outerHTML" hx-push-url="true"`,
  disparo `input changed delay:300ms, search`.
- **Rationale**: busca e categoria combinadas (Clarifications) sem JS próprio.

## R3. Aviso de notas novas

- **Decision**: na primeira página sem busca nem filtro, `_painel.html` inclui
  `<div id="novas" hx-get="/novas?desde=<enviada_em da primeira nota>" hx-trigger="every 10s"
  hx-swap="outerHTML">`. `GET /novas` devolve o mesmo elemento: vazio (mas ainda perguntando)
  quando a contagem é 0, ou com o botão "N nota(s) nova(s) · mostrar" (`<a href="/">`, que
  `hx-boost` troca). `contar_novas` = `count(*) WHERE enviada_em > :desde`, pelo índice `nota_enviada`.
  Com o caderno vazio, `desde` é vazio e qualquer nota conta.
- **Rationale**: só o aviso é trocado; nenhum cartão é recriado (SC-001, SC-002).
- **Alternatives considered**: SSE/WebSocket (processo e código a mais para o mesmo efeito).

## R4. JavaScript mínimo em arquivo

- **Decision**: `static/painel.js`, carregado com `defer`, porque a CSP proíbe script inline:
  - atalhos: `keydown` em `document`; `/` ou `Ctrl+K` fora de campo editável e sem dialog aberto
    → `#q.focus()` com `preventDefault`; `Esc` em `#q` → limpa, dispara `search` e `blur()`;
  - foto ampliada: clique em `a.ampliar` → `preventDefault`, preenche `<dialog id="foto">` (img,
    legenda) e `showModal()`; `Esc` é nativo do dialog; clique no fundo (o próprio dialog) ou no
    botão fecha; no `close`, o foco volta para o link clicado.
  Sem JS, `a.ampliar` abre o arquivo original (FR-011).
- **Rationale**: `<dialog>` dá foco preso, `Esc` e fundo de graça (plataforma antes de código).

## R5. Cartões fantasmas por CSS

- **Decision**: `hx-indicator` no próprio `#painel`; o HTMX põe `htmx-request` nele durante a
  requisição. Dentro de `#painel` há um bloco `.fantasmas` (6 cartões vazios com brilho animado)
  escondido; com `.htmx-request`, ele aparece e a grade some, com `transition-delay: 150ms` para
  não piscar em respostas rápidas (FR-013). `prefers-reduced-motion` desliga o brilho.

## R6. Fonte e tokens

- **Decision**: Inter variável (`InterVariable.woff2`, OFL 1.1) em `static/fontes/`, com
  `font-display: swap` e a licença ao lado. Tokens de cor da 003 mantidos (escuro primeiro, claro
  por `prefers-color-scheme: light`); contraste conferido: `--texto` #ededef e `--fraco` #9a9aa3
  sobre `--fundo` #0b0b0c e `--superficie` #141416 ≥ 4,5:1; claro #16161a e #5d5d66 sobre #ffffff ≥ 4,5:1.
- **Rationale**: tipografia própria sem CDN (Princípio I, SC-008).

## R7. Cartão por tipo

- **Decision**: `_cartao_nota.html` com um ramo por tipo; filtros Jinja em `painel.py`:
  - `extensao(nome)` → sufixo em maiúsculas sem ponto, até 5 letras, ou "ARQ";
  - `tamanho(bytes)` → "230 KB", "1,4 MB" (base 1024, vírgula decimal);
  - `mapa(texto)` → `https://www.openstreetmap.org/?mlat=LAT&mlon=LON#map=16/LAT/LON`, ou None
    se o texto não for "lat, lon" com números válidos;
  - `contato(texto)` → (nome, telefone) pela última vírgula; telefone vira `tel:` só com dígitos e `+`;
  - foto: `<a class="ampliar" href="/media/x">` envolvendo `<img>`; o painel confere se o arquivo
    existe (no máximo 50 por página) e, se não, mostra o espaço "imagem indisponível".
  Texto com até 140 caracteres ganha a classe `curto` (fonte maior).

## R8. Barra lateral e avisos

- **Decision**: lista `categorias` = Todas + tipos com contagem > 0 (+ o tipo do endereço, se
  ausente), na ordem de `ROTULOS`. "Falhas" sai das abas: `contagens["falha"] > 0` mostra um
  aviso no topo de `#painel` com link `?tipo=falha`. Em ≤ 720 px a barra vira `display:flex;
  overflow-x:auto` acima da lista. A barra é `<nav aria-label="Categorias">`; o item atual tem
  `aria-current="page"`.

## R9. Exportações em Downloads

- **Decision**: `encontrar_exportacoes(pastas, chat_id, limite_s=2.0) -> list[Exportacao]`:
  - para cada pasta base existente, os filhos diretos que são diretórios com `result.json`
    (nomes `ChatExport*` primeiro, mas qualquer filho com `result.json` conta);
  - lê o JSON com `json.loads` e extrai `name`, `id` (via `chat_id_exportacao`) e
    `len(messages)`; erro de leitura → situação `ilegivel`; chat ≠ configurado → `outro_chat`;
  - para ao passar de `limite_s` (relógio monotônico), devolvendo o que leu;
  - ordena por data de modificação da pasta, mais recente primeiro; nunca levanta.
  `criar_app(..., pastas_exportacao=None)`: padrão `[~/Downloads/Telegram Desktop, ~/Downloads]`;
  testes injetam `tmp_path`.
  ponytail: lê o `result.json` inteiro para contar mensagens; com exportações de centenas de MB,
  contar só o necessário com um parser incremental.
- **Rationale**: é onde o Telegram Desktop salva por padrão; o botão Importar posta a mesma `pasta`
  para o `POST /importar` existente, sem rota nova.

## R10. Estados vazios

- **Decision**: em `_notas.html`, por ordem:
  1. `contagens.todas == 0` e sem busca → "Seu caderno está vazio" + instrução + link `/importar`;
  2. com busca e 0 resultados → "Nada encontrado para “q”" + `<a href="?tipo=…">Limpar busca</a>`;
  3. `pagina > paginas` e `total > 0` → "Não há mais notas aqui" + link para a primeira página;
  4. categoria sem notas → "Nenhuma nota de <tipo> ainda".
