# Contrato: Painel HTTP (mudanças da 003)

Base: [001](../../001-captura-notas/contracts/painel-http.md) e [002](../../002-categorias-sites/contracts/painel-http.md).
Continuam valendo: bind em 127.0.0.1, checagem de Host/Origin, parâmetros `q`, `tipo`,
`site` e `pagina`, e atualização a cada 10 s só na página 1.

## Todas as respostas

Novo cabeçalho (research R7):

```text
Content-Security-Policy: default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'
```

## GET `/`

### Aba Link (`tipo=link`)

- A lista é de **itens de link**: 50 por página, ordenados por `link.data` decrescente e depois
  por `posicao` (FR-017).
- O contador da aba Link e os botões de site contam itens (FR-002, FR-003).
- `site` filtra por `link.site` (`-` = sentinela `''`).
- `q` casa com o texto da nota **ou** com o título/descrição da prévia (research R9).
- Cada item é um **cartão de link** (abaixo).

### Demais abas

- A lista é de **notas**, como na 001/002, e as contagens são de notas.
- Uma nota de link mostra seus itens como mini-cartões de link dentro do cartão da nota.

### Cartão de link

```html
<article class="cartao link">
  <a class="previa" href="{url}" target="_blank" rel="noopener noreferrer">
    <img src="/media/previas/…" alt="">            <!-- só se previa.imagem -->
    <h3>{titulo ou url}</h3>
  </a>
  <p class="descricao">{descricao}</p>             <!-- só se houver -->
  <p class="meta">{site ou "Sem site identificado"} · {data local}[ · {autor}]
     · <a href="{nota.link}" target="_blank" rel="noopener">abrir no Telegram</a></p>
</article>
```

- `titulo`, `descricao`, `autor` e `url` são sempre escapados. Nada vindo da página é
  renderizado como HTML (FR-010).
- Sem prévia (pendente ou indisponível): `<h3>` mostra a URL, e não há `<img>` (FR-011).
- O item sentinela (`url=''`) mostra o texto da nota no lugar do título, sem link externo.

### Cartão de nota

Ordem: conteúdo (texto / mídia / mini-cartões de link) → linha de meta (tipo · data ·
editada · abrir no Telegram) → ações (Baixar). Nota `falha` mantém o destaque e o erro (FR-013).

## GET `/baixar/{nota_id}` (nova)

| Caso | Resposta |
|---|---|
| Nota existe, tem `arquivo_caminho`, e o arquivo existe dentro de `MEDIA_DIR` | 200, o arquivo, com `Content-Disposition: attachment; filename*=UTF-8''{arquivo_nome ou arquivo_caminho}` |
| Nota não existe ou não tem arquivo | 404, página "Arquivo não encontrado" com link para `/` |
| Arquivo ausente do disco | 404, mesma página |
| Caminho resolvido fora de `MEDIA_DIR` | 404 |

O botão "Baixar" (`<a href="/baixar/{id}">Baixar</a>`) aparece só em foto, áudio e documento
com `arquivo_caminho` (FR-012).
