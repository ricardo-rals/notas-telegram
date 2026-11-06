# Data Model: Categorias por Tipo e Sites dos Links

A categoria de primeiro nível é o `nota.tipo` que já existe (001); nada muda nela.
A única novidade no banco é a tabela `nota_site`.

## nota_site (nova, migração `0002`)

| Coluna | Tipo | Regra |
|---|---|---|
| `nota_id` | INTEGER NOT NULL | FK → `nota.id` ON DELETE CASCADE |
| `site` | TEXT NOT NULL | domínio registrável normalizado (research R2), ou `''` = "Sem site identificado" |

- Chave primária `(nota_id, site)`: um site conta uma vez por nota (FR-006).
- Índice `nota_site_site (site, nota_id)`: filtro e contagem por site.

### Invariantes

1. Nota com `tipo = 'link'` tem **≥ 1** linha (FR-007, SC-001).
2. Nota com outro tipo tem **0** linhas (URL em legenda de mídia não conta).
3. `''` só aparece sozinho: se a nota tem ao menos um site válido, não tem a linha `''`.
4. As linhas são sempre o resultado de `sites_da_nota` sobre o conteúdo atual da nota
   (FR-012); são reescritas inteiras a cada gravação, nunca editadas em parte.

### Quem escreve

| Evento | Efeito em `nota_site` |
|---|---|
| Captura ao vivo (nova ou edição) | apaga as linhas da nota; insere `sites` se `tipo='link'` |
| Importação que cria nota | insere `sites` se `tipo='link'` |
| Importação de nota existente | nada (FR-019 da 001) |
| `registrar_falha` | nada (mantém o conteúdo anterior) |
| Migração `0002` / `reclassificar_sites` | recalcula todas as notas `link` (idempotente) |

## MensagemNormalizada (regras.py, em memória)

Ganha `urls: tuple[str, ...] = ()`, preenchido pelos dois adaptadores (research R3).

## Funções novas em `regras.py`

| Função | Entrada → saída |
|---|---|
| `site(url)` | URL → domínio registrável, IP, host sem ponto, ou `None` |
| `sites_da_nota(m)` | `MensagemNormalizada` → `frozenset[str]`; vazio vira `{''}`; só é chamado para `tipo='link'` |
| `sites_do_texto(texto)` | fallback por regex para notas sem `bruto` utilizável |

## Valores na interface

- Rótulo de `''`: "Sem site identificado". Na URL do painel: `site=-` (um hífen sozinho nunca
  é um nome de host válido, então não colide com site real).
