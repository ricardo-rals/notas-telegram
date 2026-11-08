# Data Model: Cartões de Links com Prévia

Migração `0003`: cria `link`, `previa` e `previa_fts`, reconstrói os itens a partir de `nota`
e remove `nota_site` (research R1). `nota` não muda.

## link (nova)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | INTEGER PK | |
| `nota_id` | INTEGER NOT NULL | FK → `nota.id` ON DELETE CASCADE |
| `posicao` | INTEGER NOT NULL | ordem na mensagem, 0.. |
| `url` | TEXT NOT NULL | como veio na mensagem (com parâmetros de rastreio); `''` só no item sentinela |
| `site` | TEXT NOT NULL | `regras.site(url)` ou `''` (Sem site identificado) |
| `data` | TEXT NOT NULL | ISO UTC: data da linha do WhatsApp ou `nota.enviada_em` |
| `autor` | TEXT NULL | autor da linha do WhatsApp; NULL fora do padrão |

- `UNIQUE (nota_id, url)` (FR-001: URL repetida na mesma mensagem = um item)
- `UNIQUE (nota_id, posicao)`
- Índices `link_site_data (site, data DESC)` e `link_data (data DESC, posicao)` (aba Link, FR-017)

### Invariantes

1. Nota `tipo='link'` tem ≥ 1 item. Sem nenhuma URL extraível, ela tem um item sentinela:
   `url=''`, `site=''`, `posicao=0`, e o cartão mostra o texto da nota.
2. Nota de outro tipo tem 0 itens.
3. Os itens são sempre reconstruídos inteiros a cada gravação da nota (captura, edição,
   importação nova, migração). `registrar_falha` não mexe neles.

## previa (nova)

| Coluna | Tipo | Regra |
|---|---|---|
| `url` | TEXT PK | mesma string de `link.url` (FR-005: uma prévia por URL) |
| `situacao` | TEXT NOT NULL | CHECK em `pendente`, `ok`, `indisponivel` |
| `titulo` | TEXT NULL | ≤ 200 caracteres |
| `descricao` | TEXT NULL | ≤ 300 caracteres |
| `imagem` | TEXT NULL | caminho relativo a `MEDIA_DIR`, ex. `previas/ab12….jpg` |
| `erro` | TEXT NULL | motivo quando `indisponivel` |
| `definitiva` | INTEGER NOT NULL DEFAULT 0 | 1 = não tentar de novo (endereço local, não HTML) |
| `tentativas` | INTEGER NOT NULL DEFAULT 0 | |
| `buscada_em` | TEXT NULL | ISO UTC |
| `tentar_depois_de` | TEXT NULL | ISO UTC; NULL = já pode buscar |

- Criada como `pendente` (INSERT OR IGNORE) para cada `link.url` não vazia, ao gravar itens.
- Uma prévia não é apagada quando o link some (é barato e evita buscar de novo se ele voltar).
- Índice `previa_fila (situacao, tentar_depois_de)`.

### Transições

```text
pendente ──ok──────────────▶ ok (fim)
pendente ──falha temporária─▶ indisponivel, tentativas+1, tentar_depois_de = agora + recuo
pendente ──recusa definitiva▶ indisponivel, definitiva=1 (fim)
indisponivel (não definitiva, tentar_depois_de vencido) ──▶ nova busca, mesmas saídas
```

Recuo: 1 h, 6 h, 24 h e depois 7 d (research R6).

## previa_fts (nova)

FTS5 `(titulo, descricao)`, `content='previa'`, `content_rowid='rowid'`, tokenizador
`unicode61 remove_diacritics 2`, com triggers de INSERT/UPDATE/DELETE, como a `nota_fts`.

## Removida

- `nota_site` (002): o dado passa a ser `link.site`.

## MensagemNormalizada (em memória)

+ `posicoes: tuple[int, ...]`, paralelo a `urls` (research R2).

## Funções novas em `regras.py`

| Função | Saída |
|---|---|
| `linhas_whatsapp(texto)` | `[(inicio, data_iso_utc ou None, autor ou None)]`, por linha |
| `itens_de_link(m)` | `[ItemLink(posicao, url, site, data, autor)]`; nunca vazio para nota de link (sentinela) |
| `itens_do_texto(texto, enviada_em)` | o mesmo, só pela regex (fallback sem `bruto`) |
| `pode_buscar_previa(url)` | `False` para esquema não http(s) ou host IP/sem ponto (a checagem de DNS fica em `previas.py`) |
