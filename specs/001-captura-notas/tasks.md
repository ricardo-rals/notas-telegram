---

description: "Task list for feature 001-captura-notas"
---

# Tasks: Captura de Notas do Grupo do Telegram

**Input**: Design documents from `/specs/001-captura-notas/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Obrigatórios por TDD (Constituição, Princípio V) para regras de parsing/classificação,
acesso a dados e importação. Testes do painel também foram incluídos, porque o contrato HTTP
tem regras de segurança (Host/Origin). Os testes usam só mensagens inventadas em
`tests/fixtures/`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5 da spec)
- Caminhos relativos à raiz do repositório `notas-telegram/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicializar o projeto conforme plan.md

- [X] T001 Criar `pyproject.toml` com uv (`uv init --package --name notas --python 3.12`, layout `src/notas/`) e adicionar as dependências `python-telegram-bot>=21`, `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `sqlalchemy>=2`, `alembic` e, no grupo dev, `pytest` e `httpx`; configurar `[tool.pytest.ini_options] testpaths = ["tests"]`
- [X] T002 [P] Criar `.gitignore` contendo no mínimo `.env`, `data/`, `*.db`, `*.db-wal`, `*.db-shm`, `.venv/`, `__pycache__/`
- [X] T003 [P] Criar `.env.example` com `TELEGRAM_BOT_TOKEN=`, `ALLOWED_CHAT_ID=`, `ALLOWED_USER_ID=`, `DATABASE_PATH=`, `MEDIA_DIR=data/media`, `PAINEL_PORT=8000`, com comentários e sem nenhum valor real (contracts/cli-config.md)
- [X] T004 [P] Baixar uma vez o HTMX 2.x para `src/notas/static/htmx.min.js` (vendorizado; o painel nunca usa CDN, research R7)
- [X] T005 Inicializar o Alembic (`alembic init alembic`) e ajustar `alembic/env.py` para ler a URL de `notas.config` (`sqlite:///{DATABASE_PATH}`) e usar `render_as_batch=True`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configuração, banco e tipos compartilhados por todas as histórias

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Criar `tests/conftest.py` com fixtures: `config_teste` (DATABASE_PATH em `tmp_path`, MEDIA_DIR em `tmp_path/media`, ALLOWED_CHAT_ID=-1001234567890, ALLOWED_USER_ID=111), `banco` (roda `alembic upgrade head` no banco temporário e devolve uma sessão) e `carregar_fixture(nome)` que lê JSON de `tests/fixtures/`
- [X] T007 [P] Escrever `tests/test_config.py` (deve falhar): variável obrigatória ausente → erro com o nome dela; `DATABASE_PATH` dentro da pasta do repositório → erro; padrões `MEDIA_DIR=data/media`, `PAINEL_PORT=8000` e `DATABASE_PATH=%LOCALAPPDATA%\notas-telegram\notas.db`; `TELEGRAM_BOT_TOKEN` exigido só quando o bot pede
- [X] T008 [P] Implementar `src/notas/config.py`: dataclass `Config` com `carregar(exigir_token: bool)` lendo `os.environ` (research R8) e recusando `DATABASE_PATH` dentro do repositório (Princípio IV); fazer T007 passar
- [X] T009 Implementar em `src/notas/db.py` os modelos SQLAlchemy 2 `Nota` e `Importacao` exatamente como em data-model.md: `UNIQUE(chat_id, message_id)`; `tipo` com CHECK em `texto, link, foto, audio, video, documento, localizacao, contato, outro`; `situacao` com CHECK em `ok, grande_demais, sem_arquivo, falha`; `origem` com CHECK em `ao_vivo, importacao`; `texto NOT NULL` com padrão `''`; `erro` "obrigatório quando `situacao = falha`" (CHECK `situacao <> 'falha' OR erro IS NOT NULL`); `importacao.via` CHECK em `terminal, painel` e `status` CHECK em `rodando, concluida, falha`; mais o engine com pragmas `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON` e a função `exigir_revisao_atual()` que encerra pedindo `alembic upgrade head` se o banco estiver desatualizado
- [X] T010 Criar a migração `alembic/versions/0001_inicial.py`: tabelas `nota` e `importacao`; índices `(enviada_em DESC)` e `(tipo, enviada_em DESC)`; índice parcial `CREATE UNIQUE INDEX importacao_uma_por_vez ON importacao(status) WHERE status = 'rodando'`; `nota_fts` via `op.execute` com `fts5(texto, content='nota', content_rowid='id', tokenize='unicode61 remove_diacritics 2')` e triggers AFTER INSERT/UPDATE/DELETE; downgrade que remove tudo
- [X] T011 [P] Escrever `tests/test_db.py` (deve falhar antes de T009/T010): migração aplica em banco vazio; `UNIQUE(chat_id, message_id)` rejeita duplicata; CHECKs rejeitam tipo/situação inválidos e falha sem erro; a FTS encontra "Reunião" buscando "REUNIAO"; um segundo `importacao` com status `rodando` viola o índice
- [X] T012 Definir em `src/notas/regras.py` o dataclass congelado `MensagemNormalizada` com os campos de data-model.md (`chat_id, message_id, remetente_id, enviada_em, editada_em, texto, tem_url, midia, midia_tamanho, midia_nome, localizacao, contato`) e o resultado `Classificacao(tipo, texto)`, ainda sem lógica

**Checkpoint**: `uv run pytest tests/test_config.py tests/test_db.py` passa; a base está pronta

---

## Phase 3: User Story 1 - Guardar o que mando no grupo (Priority: P1) 🎯 MVP

**Goal**: cada mensagem do dono vira uma nota com tipo, texto, data e link; mídia ≤ 20 MB baixada

**Independent Test**: enviar uma mensagem de cada tipo no grupo e conferir uma nota por mensagem, com tipo correto e arquivos elegíveis em `data/media` (quickstart §4)

### Tests for User Story 1 ⚠️ (escrever primeiro e ver falhar)

- [X] T013 [P] [US1] Criar fixtures inventadas da Bot API em `tests/fixtures/bot_api/`: `texto.json`, `link_entidade.json`, `link_text_link.json`, `foto_legenda.json` (com 3 tamanhos), `voz.json`, `audio.json`, `video.json`, `documento_pequeno.json`, `documento_25mb.json`, `animacao.json` (com `animation` e `document`), `figurinha.json`, `nota_video.json`, `enquete.json`, `localizacao.json`, `venue.json`, `contato.json`, `album_1.json`, `album_2.json` (mesmo `media_group_id`)
- [X] T014 [P] [US1] Escrever `tests/test_regras.py` com casos para `normalizar_bot_api(dict)` e `classificar(m)` seguindo a ordem de research R2: texto → `texto`; entidade `url` ou `text_link` → `link`; foto com legenda → `foto` com a legenda como texto; voz e áudio → `audio`; vídeo → `video`; animação → `outro` (não `documento`); figurinha, nota de vídeo e enquete → `outro`; localização e venue → `localizacao` com texto `"lat, lon"`; contato → `contato` com `"Nome Sobrenome, telefone"`; mensagem sem texto nem mídia → `outro`; e `link_mensagem(-1001234567890, 42) == "https://t.me/c/1234567890/42"`, com erro para chat sem prefixo `-100`
- [X] T015 [P] [US1] Escrever `tests/test_repositorio.py::test_salvar_ao_vivo_*` com `salvar_ao_vivo(sessao, nota_dados)`: grava todos os campos, com `origem='ao_vivo'`; repetir o mesmo `(chat_id, message_id)` mantém uma linha só (FR-009); `registrar_falha(...)` grava `situacao='falha'`, `erro`, `bruto` e `tipo='outro'` quando a classificação não rodou
- [X] T016 [P] [US1] Escrever `tests/test_bot.py` com `processar_mensagem(msg_dict, baixar)`, usando um `baixar` falso injetado (sem rede): foto ≤ 20 MB chama `baixar` e grava `arquivo_caminho` como `{message_id}_{file_unique_id}.jpg`; documento de 25 MB não chama `baixar` e grava `situacao='grande_demais'`; vídeo nunca chama `baixar`; `baixar` que lança exceção → nota com `situacao='falha'` e o texto do erro; foto usa o maior tamanho

### Implementation for User Story 1

- [X] T017 [US1] Implementar em `src/notas/regras.py` `normalizar_bot_api(dict) -> MensagemNormalizada`, `classificar(m) -> Classificacao` (ordem de research R2; regex `https?://\S+` só se não houver entidades) e `link_mensagem(chat_id, message_id)`; sem nenhum import de telegram ou do banco; fazer T014 passar
- [X] T018 [US1] Implementar em `src/notas/repositorio.py` `salvar_ao_vivo` (INSERT … ON CONFLICT(chat_id, message_id) DO UPDATE) e `registrar_falha`; fazer T015 passar
- [X] T019 [US1] Implementar em `src/notas/bot.py` a função pura `processar_mensagem(msg_dict, baixar)`: normaliza, classifica, decide o download (foto/áudio/voz/documento com `file_size <= 20*1024*1024`; vídeo nunca), monta a nota e chama o repositório; qualquer exceção vira `registrar_falha` com o JSON original em `bruto` (research R9); fazer T016 passar
- [X] T020 [US1] Completar `src/notas/bot.py` com o `main()` de `python -m notas.bot`: `Config.carregar(exigir_token=True)`; `exigir_revisao_atual()`; recusar iniciar se `ALLOWED_CHAT_ID` não começar com `-100`; `Application` com `MessageHandler(filters.Chat(ALLOWED_CHAT_ID) & filters.User(ALLOWED_USER_ID) & filters.UpdateType.MESSAGE, ...)`; `baixar` real com `bot.get_file()` + `download_to_drive()` em `MEDIA_DIR` (criando a pasta); `run_polling(allowed_updates=["message", "edited_message"])`; error handler global que registra no log sem o texto da mensagem; se nem `registrar_falha` conseguir gravar (banco inacessível), o log MUST trazer `chat_id`/`message_id` e a orientação "recupere pela importação (python -m notas.importacao)" (spec Edge Cases, achado C1)
- [X] T021 [US1] Adicionar `if __name__ == "__main__": main()` em `src/notas/bot.py` (sem `__main__.py` de pacote) e validar `uv run --env-file .env python -m notas.bot` contra o grupo (quickstart §4, linhas sem edição)

**Checkpoint**: mensagens do grupo viram notas no banco; `uv run pytest` passa

---

## Phase 4: User Story 2 - Ver e buscar minhas notas (Priority: P1)

**Goal**: painel em 127.0.0.1 com lista paginada, busca sem diferença de maiúsculas e acentos, filtro por tipo e prévia de mídia

**Independent Test**: com notas inventadas gravadas direto no banco, abrir o painel, buscar, filtrar e paginar (quickstart §5); não depende do bot

### Tests for User Story 2 ⚠️

- [X] T022 [P] [US2] Escrever `tests/test_repositorio.py::test_buscar_*` com `buscar(sessao, q, tipo, pagina)`: 120 notas → página 1 com 50 em ordem `enviada_em DESC` e um total para a paginação; "reunião" encontra "Reunião" e "reuniao"; várias palavras exigem todas (E lógico); entrada com `"`, `*`, `-`, `(` não gera erro de FTS; `tipo='foto'` filtra; `tipo='falha'` filtra por `situacao='falha'`; busca + tipo combinam; página além da última → lista vazia
- [X] T023 [P] [US2] Escrever `tests/test_painel.py` com `TestClient`: `GET /` responde 200 com as notas; `Host: exemplo.com` → 400; POST com `Origin: http://malicioso.com` → 403; `tipo=xyz` → 422; `pagina=0` → 422; sem resultados → "Nenhuma nota encontrada"; com `HX-Request` → só o fragmento da lista; foto com arquivo → `<img loading="lazy"`; áudio → `<audio controls`; documento → link com o nome original; `grande_demais` e `sem_arquivo` → aviso; falha → classe de destaque e texto do erro; `GET /media/../.env` → recusado; `GET /media/inexistente.jpg` → 404

### Implementation for User Story 2

- [X] T024 [US2] Implementar `buscar` em `src/notas/repositorio.py`: cada palavra de `q` vira token entre aspas (aspas internas duplicadas) juntado por espaço, JOIN com `nota_fts`, paginação de 50 com `LIMIT/OFFSET`; fazer T022 passar
- [X] T025 [P] [US2] Criar os templates em `src/notas/templates/`: `base.html` (inclui `/static/htmx.min.js`), `lista.html` (formulário de busca + select dos 9 tipos e "falhas", `hx-get="/" hx-target="#notas" hx-trigger="input changed delay:300ms, change"`; sem busca nem filtro na página 1, `#notas` também recebe `hx-trigger="every 10s"` — FR-010/SC-004), `_notas.html` (itens e paginação; data no fuso local do computador; miniatura com `alt` = legenda ou "foto"; player; link do documento; avisos; destaque de falha; link "abrir no Telegram")
- [X] T026 [US2] Implementar `src/notas/painel.py`: app FastAPI, middleware que valida `Host` em `127.0.0.1:{porta}`/`localhost:{porta}` (400) e `Origin` em POST (403), `GET /` validando `tipo` e `pagina` (422), `StaticFiles` em `/static` e em `/media` (apontando para `MEDIA_DIR`), detecção de `HX-Request` para devolver só `_notas.html`; `main()` com `exigir_revisao_atual()` e `uvicorn.run(app, host="127.0.0.1", port=cfg.painel_port)`, host fixo no código; fazer T023 passar

**Checkpoint**: US1 + US2 = caderno utilizável (MVP)

---

## Phase 5: User Story 3 - Edição atualiza a nota (Priority: P2)

**Goal**: editar a mensagem atualiza a mesma nota

**Independent Test**: enviar, editar e conferir uma nota só, com o texto novo e a data de edição (quickstart §4, linha de edição)

### Tests for User Story 3 ⚠️

- [X] T027 [P] [US3] Criar `tests/fixtures/bot_api/editada_texto.json` e `editada_com_url.json` (mesmo `message_id` de `texto.json`, com `edit_date`)
- [X] T028 [P] [US3] Adicionar a `tests/test_bot.py`: processar `texto.json` e depois `editada_texto.json` → 1 nota, texto novo, `editada_em` preenchido; edição que inclui URL → tipo `link`; edição de mensagem nunca capturada → cria a nota; edição cujo download falha → nota com `situacao='falha'` e erro (data-model, "Situação")

### Implementation for User Story 3

- [X] T029 [US3] Ajustar `normalizar_bot_api` em `src/notas/regras.py` para ler `edit_date` em `editada_em`, e garantir que `salvar_ao_vivo` em `src/notas/repositorio.py` atualize `tipo, texto, arquivo_*, situacao, erro, editada_em` no conflito, sem alterar `enviada_em`, `criada_em` e `origem`
- [X] T030 [US3] Registrar em `src/notas/bot.py` o handler de `filters.UpdateType.EDITED_MESSAGE` (mesmos filtros de chat e usuário) reutilizando `processar_mensagem` com `update.edited_message`; fazer T028 passar

**Checkpoint**: edições refletem no painel sem duplicar notas

---

## Phase 6: User Story 4 - Ignorar o que não é meu (Priority: P2)

**Goal**: nenhuma nota a partir de outro remetente ou outro chat

**Independent Test**: mensagem de outra conta no grupo e minha em outro grupo → zero notas novas (quickstart §4, última linha)

### Tests for User Story 4 ⚠️

- [X] T031 [P] [US4] Criar `tests/fixtures/bot_api/outro_usuario.json`, `outro_chat.json`, `admin_anonimo.json` (remetente `GroupAnonymousBot` 1087968824, `sender_chat` = grupo)
- [X] T032 [P] [US4] Escrever em `tests/test_regras.py` testes de `e_do_dono(m, chat_id, user_id)`: dono no grupo → True; outro usuário, outro chat ou admin anônimo → False; e em `tests/test_bot.py`: `processar_mensagem` com essas fixtures não grava nada, nem nota de falha (SC-003)

### Implementation for User Story 4

- [X] T033 [US4] Implementar `e_do_dono` em `src/notas/regras.py` e chamá-la no início de `processar_mensagem` em `src/notas/bot.py`, além dos `filters` do PTB (defesa em profundidade; o mesmo predicado será usado pela importação); mensagem ignorada não é registrada nem no log com conteúdo; fazer T032 passar

**Checkpoint**: captura ao vivo completa (US1, US3 e US4)

---

## Phase 7: User Story 5 - Preencher lacunas com a exportação do Telegram Desktop (Priority: P3)

**Goal**: importar `result.json` sem duplicar, pelo terminal e pelo painel, com contagens e uma importação por vez

**Independent Test**: mini-exportação inventada com 10 mensagens do dono (3 já no banco) e 2 de outra pessoa → 7 criadas, 3 existentes, 2 ignoradas; repetir → 0 criadas (quickstart §6)

### Tests for User Story 5 ⚠️

- [X] T034 [P] [US5] Criar `tests/fixtures/exportacao_ok/result.json` (chat `id` 1234567890, `type` `private_supergroup`; mensagens do dono `from_id` `user111` cobrindo texto, link via `text_entities`, foto, voz, documento, vídeo, localização, contato, figurinha, uma com `edited_unixtime`, uma mensagem `service` e duas de `user222`) com arquivos pequenos falsos em `photos/` e `files/`; mais `tests/fixtures/exportacao_sem_midia/result.json` (com `"(File not included. Change data exporting settings to download.)"`), `tests/fixtures/exportacao_outro_chat/result.json` e `tests/fixtures/exportacao_quebrada/result.json` (JSON inválido); a `exportacao_ok` inclui também um item do dono malformado (ex.: `date_unixtime` não numérico)
- [X] T035 [P] [US5] Escrever em `tests/test_regras.py` testes de `normalizar_exportacao(item, chat_id)`: cada item gera a mesma `Classificacao` que o equivalente da Bot API em T014 (FR-018); `date_unixtime` → `enviada_em` UTC; `edited_unixtime` → `editada_em`; `text` em lista de entidades vira texto plano
- [X] T036 [P] [US5] Escrever `tests/test_importacao.py` com `importar(pasta, via, sessao, cfg)`: contagens criadas/existentes/ignoradas/falhas = 7/3/2/1 na exportação ok, com o item malformado virando nota `situacao='falha'` com erro e sem impedir as demais; segunda execução → criadas 0; uma nota existente não é alterada (FR-019); mídia ≤ 20 MB copiada para `MEDIA_DIR`; outras pessoas sem cópia de mídia; "File not included" → `situacao='sem_arquivo'`; outro chat → erro sem tocar no banco; JSON quebrado ou pasta sem `result.json` → erro claro; com uma importação `rodando` → `ImportacaoEmAndamento`; uma `rodando` com mais de 1 h é marcada `falha` e a nova prossegue; 5.000 mensagens sintéticas sem mídia em < 120 s (SC-008)

### Implementation for User Story 5

- [X] T037 [US5] Implementar `normalizar_exportacao` em `src/notas/regras.py` (campos de research R6) e reaproveitar `e_do_dono` com `from_id == f"user{ALLOWED_USER_ID}"`; fazer T035 passar
- [X] T038 [US5] Implementar em `src/notas/repositorio.py` `salvar_importada` (INSERT … ON CONFLICT DO NOTHING, devolvendo se criou), `iniciar_importacao` (marca `falha` as `rodando` com mais de 1 h e insere `rodando`; IntegrityError → `ImportacaoEmAndamento`), `concluir_importacao` e `ultima_importacao`
- [X] T039 [US5] Implementar `src/notas/importacao.py`: `importar(...)` lê e valida `result.json` (chat igual a `ALLOWED_CHAT_ID` sem o `-100`), processa cada mensagem na sua própria transação (falha de uma vira nota `falha` e não desfaz as outras), copia a mídia ≤ 20 MB antes do INSERT e a apaga se o INSERT não criar a nota, para `MEDIA_DIR` com o nome `{message_id}_{nome_original}`, conta criadas/existentes/ignoradas/falhas e grava na tabela `importacao`; `main()` de `python -m notas.importacao <pasta>` com códigos de saída 0/1/2 (contracts/cli-config.md); fazer T036 passar
- [X] T040 [US5] Adicionar a `tests/test_painel.py`: `GET /importar` mostra o formulário; `POST /importar` com pasta válida → 202; com importação rodando → 409; pasta sem `result.json` → 422; `GET /importar/status` traz as contagens ao terminar
- [X] T041 [US5] Implementar em `src/notas/painel.py` as rotas `/importar`, `POST /importar` (roda `importar(..., via='painel')` numa `threading.Thread` com sessão própria) e `/importar/status`, e os templates `src/notas/templates/importar.html` e `_status.html` (com `hx-get="/importar/status" hx-trigger="every 2s"` enquanto `rodando`); fazer T040 passar

**Checkpoint**: todas as histórias funcionando de forma independente

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T042 [P] Criar `README.md` com instruções curtas e um link para `specs/001-captura-notas/quickstart.md`, incluindo `/setprivacy` → Disable, supergrupo e admin não anônimo
- [X] T043 [P] Escrever `tests/test_privacidade.py`: nenhum arquivo versionado (`git ls-files`, se houver repositório) casa `*.db`, `.env` ou `data/`; nenhuma fixture contém um token no formato `\d+:[A-Za-z0-9_-]{35}`; todos os `chat_id` das fixtures são o grupo inventado
- [X] T044 Gerar 10.000 notas sintéticas num teste marcado `@pytest.mark.lento` em `tests/test_repositorio.py` e verificar que `buscar` responde em < 1 s (SC-005)
- [ ] T045 Rodar `uv run pytest` completo e a validação manual de `specs/001-captura-notas/quickstart.md` §2–§7

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)** → **Foundational (2)** → histórias → **Polish (8)**
- T005 depende de T001; T009/T010 dependem de T005 e T008; T006 depende de T010

### User Story Dependencies

- **US1 (P1)**: depende só da Phase 2
- **US2 (P1)**: depende só da Phase 2 (testa com notas gravadas direto pelo repositório); pode correr em paralelo com US1
- **US3 (P2)**: depende de US1 (`processar_mensagem`, `salvar_ao_vivo`)
- **US4 (P2)**: depende de US1 (`processar_mensagem`)
- **US5 (P3)**: depende de US1 (`classificar`, nota) e, para T040/T041, de US2 (painel); T037–T039 (terminal) dependem só de US1

### Within Each User Story

- Fixtures e testes → ver falhar → implementação → testes passando
- `regras` → `repositorio` → portas de entrada (`bot`, `painel`, `importacao`)

### Parallel Opportunities

- Setup: T002, T003 e T004 juntos
- Foundational: T007 + T011 (testes) e T008 em paralelo com T009
- Depois da Phase 2: US1 e US2 em paralelo (arquivos diferentes, exceto `repositorio.py`, então fazer T018 e T024 em sequência)
- Dentro de cada história, as tarefas de fixture e teste marcadas [P]

---

## Parallel Example: User Story 1

```text
Task: "T013 fixtures da Bot API em tests/fixtures/bot_api/"
Task: "T014 testes de regras em tests/test_regras.py"
Task: "T015 testes de salvar_ao_vivo em tests/test_repositorio.py"
Task: "T016 testes de processar_mensagem em tests/test_bot.py"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2
2. US1 + US4 (captura sem nunca guardar mensagem de terceiros; US4 é pequena e é privacidade)
3. US2 (painel)
4. **PARAR e validar** com quickstart §4–§5 e §7

### Incremental Delivery

1. MVP (US1 + US4 + US2)
2. \+ US3 (edição)
3. \+ US5 pelo terminal (T034–T039), depois pelo painel (T040–T041)
4. Polish

---

## Notes

- `checklists/revisao.md` tem 28 itens ainda não revisados; os mais relevantes para estas tarefas (CHK002, CHK009, CHK010, CHK016) já foram decididos no plano e refletidos em T019, T020, T028 e T036
- Commit após cada tarefa ou grupo lógico
- Nenhuma tarefa usa dados reais; tokens e IDs só no `.env`
