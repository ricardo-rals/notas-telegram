# Contrato: Painel HTTP (mudanças da 002)

Base: [001 painel-http.md](../../001-captura-notas/contracts/painel-http.md). Só `GET /` muda;
as demais rotas, o middleware de Host/Origin e o bind em 127.0.0.1 ficam como estão.

## GET `/`

| Query | Valores | Padrão |
|---|---|---|
| `q` | texto livre | vazio |
| `tipo` | um dos 9 tipos, `falha`, ou vazio (= aba "Todas") | vazio |
| `site` | domínio (ex. `youtube.com`), `-` (= "Sem site identificado") ou vazio (= todos os sites) | vazio |
| `pagina` | inteiro ≥ 1 | 1 |

### Regras

- `tipo` inválido ou `pagina < 1` → **422**, como na 001.
- `site` só filtra quando `tipo=link`; com outro `tipo` é ignorado.
- `site` com valor que não existe → lista vazia com "Nenhuma nota encontrada", **200** (FR-015).
- `q`, `tipo` e `site` combinam (FR-008).
- Ordenação, 50 por página e atualização a cada 10 s (só página 1) seguem a 001.

### Resposta (página completa e fragmento HTMX)

O fragmento (`HX-Request` presente) passa a conter abas + botões de site + lista, para que as
contagens se atualizem junto com a lista.

1. **Abas** (`<nav aria-label="Tipos">`), nesta ordem: Todas, Texto, Link, Foto, Áudio, Vídeo,
   Documento, Localização, Contato, Outro, Falhas. Cada uma: `<a href>` com o `q` atual, rótulo e
   contagem do caderno inteiro, ex. `Foto (7)`. A ativa tem `aria-current="page"`. Aba com 0 aparece.
2. **Botões de site** (`<nav aria-label="Sites">`), só quando `tipo=link`: "Todos os sites" primeiro,
   depois um `<a href>` por site, `youtube.com (3)`, ordenado por quantidade decrescente e nome;
   "Sem site identificado (n)" vem sempre por último, quando n > 0. O site ativo tem
   `aria-current="page"` e o link dele aponta para "Todos os sites" (clicar de novo desmarca).
3. **Lista**: igual à 001.

Contagens de abas e botões ignoram `q` e `pagina` (FR-002).

### Formulário de busca

O `<select name="tipo">` sai. O formulário leva `tipo` e `site` como `<input type="hidden">`, então
buscar mantém a aba e o site atuais. Os links das abas levam o `q` atual e descartam `site` e `pagina`.
