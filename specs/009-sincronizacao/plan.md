# Implementation Plan: Sincronização com Um Clique

**Branch**: `009-sincronizacao` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

## Summary

`notas/sincronizacao.py` com Telethon (MTProto oficial):

- `para_bot_api(msg, chat_id)`: converte a mensagem do Telethon no dicionário da API de bots
  (texto/legenda, entidades de URL, foto, voz, áudio, vídeo, nota de vídeo, figurinha, GIF,
  documento, localização, local, contato, enquete, dado). Assim a sincronização reaproveita
  `bot.processar_mensagem` inteiro, e as regras ficam idênticas (FR-002). `file_id` = `tg:<id>`.
- `sincronizar(imp_id, cliente, engine, cfg)`: `min_id` = maior `message_id` do grupo;
  `iter_messages(grupo, min_id=…, reverse=True)`; pula `MessageService`; baixa com
  `cliente.download_media`; conta criadas/ignoradas/falhas; `concluir_importacao`.
- O cliente é injetável: os testes usam um falso com mensagens inventadas.
- `main`: `login` (interativo, uma vez) e sincronização pelo terminal.

Painel: `POST /sincronizar` (thread + `asyncio.run`), botão no topo, status em `#status`.
`salvar_ao_vivo` e `processar_mensagem` ganham `origem` (padrão `ao_vivo`).

## Constitution Check (2.0.0)

I ✅ só fala com o Telegram · II ✅ regras da 001 · IV ✅ sessão e `api_hash` fora do Git ·
V ✅ conversão e sincronização testadas com cliente falso · VI ✅ thread no painel, nenhum
processo novo · VII ✅ MTProto oficial, `api_id` do dono, só leitura do grupo configurado ·
VIII ✅ falhas viram notas; erro da sincronização fica na importação.

## Project Structure

```text
src/notas/sincronizacao.py  # novo
src/notas/config.py         # api_id, api_hash, telegram_sessao
src/notas/bot.py, repositorio.py  # origem
src/notas/painel.py, templates/{base,_status}.html
tests/test_sincronizacao.py, test_painel.py, test_config.py
```
