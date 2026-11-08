# Quickstart: validar Cartões de Links com Prévia

Pré-requisito: ambiente da 002 funcionando. Dados só inventados; nenhum teste acessa a internet.

## 1. Testes automáticos

```powershell
uv run pytest
uv run pytest -m lento     # SC-005: 10.000 notas e 5.000 itens
```

Cobertura esperada:

- `linhas_whatsapp`: as duas ordens de data/hora, autor com espaço, data impossível, linha sem
  prefixo, linha com dois links.
- `itens_de_link`: a mensagem de exemplo (9 links → 9 itens, 8 `instagram.com`), URL repetida,
  `text_link`, edição removendo links, sentinela.
- `previas`:
  - parser HTML com `og:*`, só `twitter:*`, só `<title>`, nenhum metadado, HTML malicioso no
    título (sai como texto);
  - checagem de destino recusa `127.0.0.1`, `10.x`, `192.168.x`, `169.254.x`, `[::1]` e
    redirecionamento para eles;
  - limites de tamanho e de tempo;
  - recuo das tentativas.

  Tudo isso contra um servidor HTTP local de teste, liberado só nesses testes.
- Painel: cartões, `/baixar/{id}` (nome certo, 404 amigável), CSP presente, aba Link em itens,
  "Todas" em notas.

## 2. Migração das notas antigas

```powershell
# numa CÓPIA do banco (DATABASE_PATH apontando para ela)
uv run --env-file .env alembic upgrade head
```

Esperado: toda nota de link tem ≥ 1 item, `nota_site` não existe mais, e as contagens dos
botões de site agora contam links (ver [data-model.md](data-model.md)).

## 3. Mensagem de exemplo

Mandar no grupo a lista de 9 links do pedido, com o prefixo `[hh:mm, dd/mm/aaaa] Nome:`.

1. Aba Link: 9 cartões; `instagram.com (8)`, `i384100.net (1)`.
2. Cada cartão mostra a data e o autor da sua linha, e os cartões estão ordenados por essa data.
3. Aba "Todas": uma nota só, com 9 mini-cartões.
4. Em até 1 min, os cartões com prévia disponível mostram título e imagem. Os do Instagram podem
   ficar sem prévia (esperado, ver spec Assumptions).
5. Clicar no título abre o link numa aba nova; "abrir no Telegram" abre a mensagem.

## 4. Prévia desligada

`PREVIAS_LINKS=0` no `.env`, reiniciar o painel e mandar um link novo. O cartão aparece só com o
endereço. Opcional: no Monitor de Recursos do Windows, aba Rede, o processo do painel não abre
conexão para fora.

## 5. Baixar e layout

- Foto, áudio e documento com arquivo: "Baixar" salva o arquivo com o nome original. Apagar o
  arquivo da pasta e clicar de novo mostra "Arquivo não encontrado".
- Janela com 360 px de largura: sem rolagem horizontal. Com Tab, o foco visível passa por
  busca → abas → sites → cartões.
- Tema claro e escuro do Windows: texto legível nos dois.

## Resultados (2026-11-08)

Numa cópia do banco real (10 itens de link, 1 foto, 1 documento), painel na porta 8766:

- §1: `uv run pytest` → 228 passed (inclui os `lento`; 10.000 notas, todas as consultas < 1 s).
- §2: a cópia já estava em `0003`, mas **sem nenhuma `previa`**: a 0003 rodou antes da fila
  existir. Corrigido com a migração `0004`, que enfileira as URLs sem prévia (teste
  `test_migracao_0004_enfileira_previas_de_links_antigos`).
- §3: aba Link com 10 cartões, `instagram.com (9)` e `i384100.net (1)`. Em ~30 s, as 9 prévias
  ficaram `ok`, 8 com miniatura (uma do Instagram veio só com o título "Instagram").
- §4: coberto por `test_thread_de_previas_so_quando_ligada`; com `PREVIAS_LINKS=0`, a thread não sobe.
- §5: `/baixar/6` → PDF com o nome original; `/baixar/5` → foto; id inexistente → 404 com
  "Arquivo não encontrado". CSP presente em todas as respostas. O layout em 360 px e o
  contraste nos dois temas foram reavaliados no redesenho da 004.
