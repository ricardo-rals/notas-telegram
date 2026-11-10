# Tasks: Sincronização com Um Clique

- [ ] T001 Testes de `para_bot_api` com objetos Telethon inventados (texto+URL, link escondido, foto, voz, áudio, vídeo, nota de vídeo, figurinha, documento com nome, localização, local, contato, enquete, página web, sem remetente) e conferência via `normalizar_bot_api` + `classificar`
- [ ] T002 `para_bot_api`. T001 deve passar
- [ ] T003 Testes de `sincronizar` com cliente falso: `min_id` = última salva; só o grupo configurado; serviço pulado; terceiros ignorados; download; origem `sincronizacao`; contagens; segunda vez cria 0; erro no meio grava o que veio e marca falha
- [ ] T004 `origem` em `salvar_ao_vivo`/`processar_mensagem`; `sincronizar`. T003 deve passar
- [ ] T005 Testes de config (`TELEGRAM_API_ID` inteiro, sessão fora do repo) e do painel (`POST /sincronizar`: falta configuração, falta login, inicia com executor injetado, 409 com outra rodando; botão no topo; status "Sincronização")
- [ ] T006 Config, painel, templates, `main` (login e terminal). T005 deve passar
- [ ] T007 README (como criar o api_id e fazer login); `uv run --env-file .env pytest`
