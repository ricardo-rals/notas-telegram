# Data Model: Redesenho do Painel

Sem migração e sem tabela nova. Duas visões calculadas na hora:

## Exportacao (em memória, `importacao.py`)

| Campo | Tipo | Regra |
|---|---|---|
| `pasta` | Path | filho direto de uma das pastas de downloads, com `result.json` |
| `nome` | str | `name` do `result.json`; vazio se ilegível |
| `data` | datetime | modificação da pasta (fuso local na exibição) |
| `mensagens` | int | `len(messages)`; 0 se ilegível |
| `situacao` | str | `importavel` · `outro_chat` · `ilegivel` |

## Contagem de notas novas (`repositorio.contar_novas`)

`count(nota) WHERE enviada_em > desde` (ISO UTC da primeira nota exibida; vazio = todas).
Usa o índice `nota_enviada` da 001.

## Contexto da barra lateral (`painel.py`)

- `categorias`: `[(valor, rótulo, contagem)]` = Todas + tipos com contagem > 0 (+ o selecionado).
- `falhas`: `contagens["falha"]`.
