# Data Model: Captura de Notas

Um arquivo SQLite (`DATABASE_PATH`). Datas em UTC, texto ISO 8601.

## nota

Uma mensagem do dono no grupo-caderno. O arquivo de mídia (no máximo um por mensagem) fica
na própria linha, sem tabela à parte.

| Campo | Tipo | Regra |
|---|---|---|
| id | INTEGER PK | autoincremento |
| chat_id | INTEGER | NOT NULL; igual a `ALLOWED_CHAT_ID` |
| message_id | INTEGER | NOT NULL; `UNIQUE(chat_id, message_id)` (FR-009, FR-019) |
| enviada_em | TEXT | NOT NULL |
| editada_em | TEXT | NULL até a primeira edição (FR-008) |
| tipo | TEXT | NOT NULL; CHECK em `texto, link, foto, audio, video, documento, localizacao, contato, outro` |
| texto | TEXT | NOT NULL, padrão `''`; corpo, legenda, coordenadas ou contato (FR-004, FR-005) |
| link | TEXT | NOT NULL; `https://t.me/c/{id_interno}/{message_id}` |
| arquivo_caminho | TEXT | NULL; relativo a `MEDIA_DIR` |
| arquivo_nome | TEXT | NULL; nome original, quando houver |
| arquivo_tamanho | INTEGER | NULL; bytes |
| situacao | TEXT | NOT NULL; CHECK em `ok, grande_demais, sem_arquivo, falha` |
| erro | TEXT | NULL; obrigatório quando `situacao = falha` |
| origem | TEXT | NOT NULL; CHECK em `ao_vivo, importacao` |
| bruto | TEXT | NULL; JSON original (update da Bot API ou item da exportação) |
| criada_em | TEXT | NOT NULL |

Índices: `UNIQUE(chat_id, message_id)`, `(enviada_em DESC)`, `(tipo, enviada_em DESC)`.

### Situação

```text
            captura/importação
                   │
     ┌─────────────┼──────────────┬──────────────┐
     ▼             ▼              ▼              ▼
    ok      grande_demais    sem_arquivo       falha
     ▲                                           │
     └──── edição reprocessada com sucesso ──────┘
```

- Edição ao vivo reprocessa a mensagem inteira e atualiza `tipo`, `texto`, arquivo,
  `situacao`, `erro` e `editada_em` na mesma linha (upsert).
- Importação nunca altera uma linha existente (`ON CONFLICT DO NOTHING`).
- Nenhuma transição apaga a linha (Princípio VIII).

## nota_fts (FTS5, conteúdo externo)

`CREATE VIRTUAL TABLE nota_fts USING fts5(texto, content='nota', content_rowid='id',
tokenize='unicode61 remove_diacritics 2')`, com triggers `AFTER INSERT/UPDATE/DELETE`
em `nota` para mantê-la sincronizada. Criada por SQL direto na migração.

## importacao

| Campo | Tipo | Regra |
|---|---|---|
| id | INTEGER PK | |
| pasta | TEXT | NOT NULL |
| via | TEXT | CHECK em `terminal, painel` |
| status | TEXT | CHECK em `rodando, concluida, falha` |
| iniciada_em | TEXT | NOT NULL |
| terminada_em | TEXT | NULL |
| criadas | INTEGER | padrão 0 |
| existentes | INTEGER | padrão 0 |
| ignoradas | INTEGER | padrão 0 |
| falhas | INTEGER | padrão 0 |
| erro | TEXT | NULL; motivo quando a importação inteira falha |

Índice único parcial: `CREATE UNIQUE INDEX importacao_uma_por_vez ON importacao(status)
WHERE status = 'rodando'` (FR-021). Execução `rodando` com mais de 1 h é marcada `falha`
antes de iniciar outra.

## MensagemNormalizada (em memória, não persistida)

Forma comum produzida pelos adaptadores da Bot API e da exportação, entrada das regras de
classificação:

`chat_id, message_id, remetente_id, enviada_em, editada_em, texto, tem_url (bool),
midia: foto | audio | video | documento | outro | None, midia_tamanho, midia_nome,
localizacao (lat, lon) | None, contato (nome, telefone) | None`
