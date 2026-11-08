# Contrato: Configuração (mudanças da 003)

Base: [001 cli-config.md](../../001-captura-notas/contracts/cli-config.md).

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `PREVIAS_LINKS` | não | `1` | `1` liga a busca de prévias de links pelo painel; `0` desliga. Com `0`, nenhuma requisição além do Telegram sai da máquina (Princípio I, FR-006) |

- Valores aceitos: `0` ou `1`. Outro valor → erro de configuração com o nome da variável.
- O bot não lê esta variável: ele só registra as URLs como pendentes. Quem busca é o painel.
- `.env.example` ganha a linha, comentada, com o padrão.

## Comandos

Sem comando novo. A migração `0003` roda com o `alembic upgrade head` de sempre e reconstrói
os itens de link das notas antigas (FR-015).
