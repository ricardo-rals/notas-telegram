# Contrato: Painel HTTP

Servidor em `http://127.0.0.1:{PAINEL_PORT}` (padrão 8000). Respostas HTML. Rotas marcadas
com HTMX devolvem só um fragmento quando o cabeçalho `HX-Request` está presente.

Toda requisição com `Host` fora de `127.0.0.1:{porta}` / `localhost:{porta}` → **400**.
Todo POST com `Origin` diferente do painel → **403**.

| Método | Rota | Entrada | Saída |
|---|---|---|---|
| GET | `/` | query `q` (texto), `tipo` (um dos 9 tipos ou `falha`), `pagina` (≥1, padrão 1) | Página com até 50 notas, da mais recente para a mais antiga; HTMX: só a lista |
| GET | `/media/{caminho}` | — | Arquivo de `MEDIA_DIR`; 404 se não existe; caminho fora da pasta é recusado |
| GET | `/importar` | — | Formulário com o campo da pasta e o status da última importação |
| POST | `/importar` | form `pasta` (caminho local) | 202 + fragmento de status; 409 se já há importação rodando; 422 se a pasta não tem `result.json` |
| GET | `/importar/status` | — | Fragmento com status e contagens (consultado pelo HTMX a cada 2 s até terminar) |

## Regras da lista (`GET /`)

- `q` vazio → sem filtro de texto. `q` preenchido → busca FTS5, cada palavra entre aspas,
  todas obrigatórias (E lógico), sem diferença de maiúsculas e acentos.
- `tipo=falha` filtra por `situacao = falha`, não por tipo.
- `q` e `tipo` combinam (FR-012).
- Valores inválidos de `tipo` ou `pagina` → 422.
- Nenhum resultado → mensagem "Nenhuma nota encontrada".

## Cada nota exibida (FR-013)

Data local, tipo, texto, link "abrir no Telegram". Mais, conforme o caso:
- foto com arquivo → `<img loading="lazy">` em link para o original;
- áudio com arquivo → `<audio controls>`;
- documento com arquivo → link com o nome original;
- `grande_demais` / `sem_arquivo` → aviso do motivo;
- `falha` → destaque visual e o texto do erro.
