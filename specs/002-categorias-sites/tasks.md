---

description: "Task list for feature 002-categorias-sites"
---

# Tasks: Categorias por Tipo e Sites dos Links

**Input**: Design documents from `/specs/002-categorias-sites/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/painel-http.md, quickstart.md

**Tests**: obrigatórios por TDD (Constituição, Princípio V). Valem para a regra de site e a
extração de URLs (`regras`), para a gravação e reclassificação de `nota_site`
(`repositorio`) e para a migração. Os testes do painel seguem o padrão da 001. Os testes
usam só dados inventados.

**Organization**: tarefas agrupadas por história de usuário (US1–US4 da spec)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1–US4 da spec
- Caminhos relativos à raiz do repositório `notas-telegram/`

---

## Phase 1: Setup

- [X] T001 Adicionar a dependência `publicsuffixlist` com `uv add publicsuffixlist` (atualiza `pyproject.toml` e `uv.lock`). Conferir que nenhum código chama o `publicsuffixlist.update` (Princípio I, research R1)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: a regra de site, a extração de URLs e a tabela `nota_site`, usadas por US2, US3 e US4

**⚠️ CRITICAL**: US2–US4 só começam depois desta fase. A US1 depende só da Phase 1 e pode começar já.

- [X] T002 [P] Escrever em `tests/test_regras.py` o teste parametrizado de `site(url)`. Ele deve falhar. Casos e resultado esperado:
  - `https://www.youtube.com/x`, `https://m.youtube.com`, `https://music.youtube.com` e `HTTPS://YouTube.COM:8080/a` → `youtube.com`
  - `https://pt.wikipedia.org` → `wikipedia.org`
  - `https://folha.uol.com.br/a` → `uol.com.br`
  - `http://exemplo.co.uk` → `exemplo.co.uk`
  - `https://fulano.github.io/p` → `fulano.github.io`
  - `https://www.m.exemplo.com` → `exemplo.com`
  - `http://exemplo.com./` → `exemplo.com`
  - `exemplo.com.br/x` (sem esquema) → `exemplo.com.br`
  - `http://192.168.0.1:8000` → `192.168.0.1`
  - `http://[::1]/` → `::1`
  - `http://localhost:3000` → `localhost`
  - `https://xn--bcher-kva.de` e `https://www.BÜCHER.de` → `bücher.de`
  - `http://com.br` → `None`
  - `http://`, `https://` e `não é url` → `None`
- [X] T003 Implementar `site(url: str) -> str | None` em `src/notas/regras.py`, seguindo os passos 1–7 de research R2:
  1. `urlsplit`, prefixando `http://` quando a URL não tem esquema;
  2. `hostname`;
  3. remover o ponto final;
  4. `ipaddress` (IP → o próprio IP);
  5. host sem ponto → o próprio host;
  6. labels `xn--` → forma legível com o codec `idna`, label a label, mantendo o label original se o decode falhar;
  7. `PublicSuffixList().privatesuffix()`, numa instância de módulo criada uma vez.

  Toda exceção interna → `None`. T002 deve passar.
- [X] T004 [P] Criar as fixtures inventadas em `tests/fixtures/bot_api/` (chat `-1001234567890`, remetente `111`, como as existentes):
  - `link_varios_sites.json`: texto `"🎉 https://www.youtube.com/a e https://m.youtube.com/b e https://instagram.com/c"`, com entidades `url`. O emoji antes da URL testa os offsets em UTF-16.
  - `link_sem_esquema.json`: texto `"veja exemplo.com.br"`, com entidade `url` só sobre `exemplo.com.br`.
  - `link_idn.json`: entidade `text_link` com `url` `https://xn--bcher-kva.de/`.

  Criar também `tests/fixtures/exportacao_links/result.json` (supergrupo `1234567890`, dono `user111`), com três mensagens:
  1. uma com `text_entities` do tipo `text_link` e `href` `https://m.facebook.com/evento`;
  2. uma com `text_entities` do tipo `link` e texto `https://www.youtube.com/x`;
  3. uma de texto puro, sem URL.
- [X] T005 [P] Escrever testes em `tests/test_regras.py` para `MensagemNormalizada.urls`. Eles devem falhar.
  - Bot API:
    - `link_entidade.json` → `("https://exemplo.com",)`;
    - `link_text_link.json` → `("https://exemplo.com/x",)`;
    - `link_varios_sites.json` → as 3 URLs, na ordem;
    - `link_sem_esquema.json` → `("exemplo.com.br",)`;
    - `texto.json` → `()`.
  - Exportação: as mensagens de `exportacao_links/result.json` → `("https://m.facebook.com/evento",)`, `("https://www.youtube.com/x",)` e `()`.
  - Mensagem sem entidades com `https://a.com` no texto → regex → `("https://a.com",)`.
  - URL repetida aparece uma vez só.
- [X] T006 Adicionar `urls: tuple[str, ...] = ()` a `MensagemNormalizada` em `src/notas/regras.py` e preencher nos dois adaptadores (research R3):
  - `normalizar_bot_api`:
    - `text_link` → `e["url"]`;
    - `url` → recorte de `texto.encode("utf-16-le")[off*2:(off+len)*2].decode("utf-16-le")`.
  - `normalizar_exportacao`:
    - `text_link` → `href`;
    - `link` → `text`.
  - Sem entidades: `URL.findall(texto)`.
  - Deduplicar mantendo a ordem. T005 deve passar.
- [X] T007 [P] Escrever testes em `tests/test_regras.py` para `sites_da_nota(m)` e `sites_do_texto(texto)`. Eles devem falhar.
  - `link_varios_sites.json` → `frozenset({"youtube.com", "instagram.com"})`.
  - Só URLs sem site (`http://com.br`) → `frozenset({""})`.
  - Mistura de site válido e inválido → só o válido, sem `""` (data-model, invariante 3).
  - `sites_do_texto("ver https://www.x.com.br e https://x.com.br/2")` → `{"x.com.br"}`.
  - `sites_do_texto("")` → `{""}`.
- [X] T008 Implementar `sites_da_nota(m: MensagemNormalizada) -> frozenset[str]` e `sites_do_texto(texto: str) -> frozenset[str]` em `src/notas/regras.py`. Ambas aplicam `site()` a cada URL e descartam `None`. Resultado vazio → `frozenset({""})`. Nenhuma das duas levanta exceção (FR-014). T007 deve passar.
- [X] T009 [P] Escrever em `tests/test_db.py` os testes da migração `0002`. Eles devem falhar.
  - A tabela `nota_site` existe depois de `upgrade head`.
  - A chave primária `(nota_id, site)` rejeita uma linha duplicada.
  - `site` é `NOT NULL`.
  - Apagar a nota apaga as linhas dela (`ON DELETE CASCADE`).
  - O índice `nota_site_site` existe.
  - `alembic downgrade 0001` remove a tabela.
- [X] T010 Criar `alembic/versions/0002_nota_site.py` (`revision = "0002"`, `down_revision = "0001"`) com:
  - `CREATE TABLE nota_site (nota_id INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE, site TEXT NOT NULL, PRIMARY KEY (nota_id, site))`;
  - `CREATE INDEX nota_site_site ON nota_site (site, nota_id)`;
  - um `downgrade` que faz `DROP TABLE nota_site`.

  Adicionar o modelo `NotaSite` (`nota_id`, `site`) em `src/notas/db.py`, com um comentário dizendo que `site = ''` significa "Sem site identificado". T009 deve passar. Os testes existentes (`test_revisao_atual_ok`) continuam passando.

**Checkpoint**: `uv run pytest tests/test_regras.py tests/test_db.py` passa

---

## Phase 3: User Story 1 - Navegar por abas de tipo (Priority: P1) 🎯 MVP

**Goal**: o `<select>` de tipo vira abas com contagens do caderno inteiro

**Independent Test**: com notas inventadas de vários tipos, abrir `/`, clicar em cada aba e conferir que a lista e a contagem batem (spec US1)

### Tests for User Story 1 ⚠️ (escrever primeiro e ver falhar)

- [X] T011 [P] [US1] Escrever em `tests/test_repositorio.py` o teste de `contar_por_tipo(sessao) -> dict[str, int]`:
  - 7 fotos, 3 áudios e 1 link com `situacao='falha'` → `{"foto": 7, "audio": 3, "link": 1, "falha": 1, "todas": 11}`;
  - tipos sem nota → `0`, com todas as 9 chaves presentes;
  - a soma dos 9 tipos é igual a `todas` (SC-006).
- [X] T012 [P] [US1] Escrever em `tests/test_painel.py` os testes das abas (contracts/painel-http.md §Resposta 1):
  - `GET /` tem `<nav aria-label="Tipos">` com 11 links na ordem Todas, Texto, Link, Foto, Áudio, Vídeo, Documento, Localização, Contato, Outro, Falhas, cada um com a contagem, ex. `Foto (7)`;
  - a aba ativa tem `aria-current="page"` (`/` → Todas; `/?tipo=foto` → Foto);
  - as contagens não mudam com `q=palavra`;
  - os links das abas levam o `q` atual e não levam `site` nem `pagina`;
  - a página não tem mais `<select name="tipo">`;
  - o formulário tem `<input type="hidden" name="tipo">`;
  - o fragmento HTMX (`HX-Request`) também contém as abas;
  - aba com 0 aparece como `(0)`.

  Ajustar `test_busca_e_filtro` e qualquer teste que dependa do `<select>`.

### Implementation for User Story 1

- [X] T013 [US1] Implementar `contar_por_tipo(sessao)` em `src/notas/repositorio.py` com `SELECT tipo, count(*) … GROUP BY tipo`, mais `count(*) WHERE situacao='falha'` e o total. Preencher com 0 os tipos de `TIPOS` que não vierem. T011 deve passar.
- [X] T014 [US1] Em `src/notas/painel.py`:
  - passar `contagens=contar_por_tipo(sessao)` e a lista ordenada de abas (`[("", "Todas")] + FILTROS`) para o contexto;
  - ajustar `consulta` para incluir `site` (vazio por enquanto);
  - manter o 422 para `tipo` inválido.
- [X] T015 [US1] Em `src/notas/templates/lista.html` e `src/notas/templates/_notas.html`:
  - trocar o `<select>` por `<input type="hidden" name="tipo" value="{{ tipo }}">` e remover `change from:select` do `hx-trigger`;
  - no topo de `_notas.html`, criar `<nav aria-label="Tipos">` com um `<a href="/?{{ urlencode(q, tipo) }}">Rótulo (n)</a>` por aba e `aria-current="page"` na ativa.

  A aba fica dentro do fragmento que já atualiza a cada 10 s. Adicionar CSS mínimo em `src/notas/templates/base.html` (`nav.abas a[aria-current]` em negrito, com borda inferior). T012 deve passar.

**Checkpoint**: `uv run pytest tests/test_repositorio.py tests/test_painel.py` passa; o painel funciona por abas, sem nada de site ainda

---

## Phase 4: User Story 2 - Filtrar links por site (Priority: P1)

**Goal**: na aba Link, um botão por site com contagem, combinável com a busca

**Independent Test**: com notas de link e linhas `nota_site` inseridas direto pela sessão, abrir `/?tipo=link` e conferir os botões e o filtro (spec US2)

### Tests for User Story 2 ⚠️

- [X] T016 [P] [US2] Escrever em `tests/test_repositorio.py` os testes de `contar_sites(sessao) -> list[tuple[str, int]]` e `buscar(…, site=…)`. Inserir `Nota` + `NotaSite` direto pela sessão:
  - 3 notas em `youtube.com`, 1 em `instagram.com`, 1 em `ac.com` e 1 em `''` → `[("youtube.com", 3), ("ac.com", 1), ("instagram.com", 1), ("", 1)]`, ordenado por quantidade decrescente e depois por nome; o `''` vem sempre por último.
  - Uma nota em dois sites conta 1 em cada.
  - Linhas de notas com tipo diferente de `link` não contam.
  - `buscar(tipo="link", site="youtube.com")` → só as 3.
  - `site=""` (sentinela) → a nota sem site.
  - `site="nao-existe.com"` → `([], 0)`.
  - `site` combinado com `q` → interseção.
  - `site` com `tipo="foto"` → ignorado.
- [X] T017 [P] [US2] Escrever em `tests/test_painel.py` os testes dos botões (contracts/painel-http.md §Resposta 2):
  - `/?tipo=link` tem `<nav aria-label="Sites">` com "Todos os sites" primeiro e depois `youtube.com (3)`;
  - `/?tipo=foto` não tem esse nav;
  - `/?tipo=link&site=youtube.com` lista só as notas do YouTube, o botão tem `aria-current="page"` e o `href` dele aponta para `/?tipo=link` com o `q` atual (desmarcar);
  - `site=-` mostra "Sem site identificado" e as notas sem site;
  - `site=nao-existe.com` → 200 com "Nenhuma nota encontrada" (FR-015);
  - o formulário leva `<input type="hidden" name="site">`;
  - a paginação preserva `site`.

### Implementation for User Story 2

- [X] T018 [US2] Em `src/notas/repositorio.py`:
  - adicionar o parâmetro `site: str | None = None` a `buscar`. Só quando `tipo == "link"` e `site is not None`, aplicar `Nota.id.in_(select(NotaSite.nota_id).where(NotaSite.site == site))`.
  - implementar `contar_sites(sessao)` com um `JOIN nota ON nota.id = nota_site.nota_id WHERE nota.tipo = 'link' GROUP BY site ORDER BY count(*) DESC, site`.

  T016 deve passar.
- [X] T019 [US2] Em `src/notas/painel.py`:
  - ler a query `site: str = ""` e traduzir: `"-"` → `""` (sentinela), vazio → `None`, outro valor → como veio, sem validar (FR-015);
  - quando `tipo == "link"`, passar `sites=contar_sites(sessao)` para o contexto;
  - incluir `site` em `consulta`, e o rótulo `"Sem site identificado"` para `""`.
- [X] T020 [US2] Em `src/notas/templates/_notas.html`, logo abaixo das abas e só quando `tipo == 'link'`, criar `<nav aria-label="Sites">`:
  - "Todos os sites" primeiro;
  - depois um `<a>` por site (`site=-` para `""`), com contagem e `aria-current="page"` no ativo;
  - o link do site ativo aponta para "Todos os sites".

  Em `src/notas/templates/lista.html`, adicionar `<input type="hidden" name="site" value="{{ site_param }}">`. T017 deve passar.

**Checkpoint**: abas e botões funcionando com dados inseridos à mão; falta a gravação automática (US3/US4)

---

## Phase 5: User Story 3 - Notas antigas também classificadas (Priority: P1)

**Goal**: `alembic upgrade head` classifica por site todas as notas de link já guardadas (FR-011)

**Independent Test**: banco na revisão 0001 com links inventados → `upgrade head` → todos aparecem nos botões de site (spec US3)

### Tests for User Story 3 ⚠️

- [X] T021 [P] [US3] Escrever em `tests/test_repositorio.py` os testes de `reclassificar_sites(conn)`. As notas são inseridas com `bruto` das fixtures de T004 e das existentes:
  - `link_varios_sites` (`origem='ao_vivo'`) → `youtube.com` e `instagram.com`;
  - `link_idn` → `bücher.de`;
  - mensagem de `exportacao_links` (`origem='importacao'`) → `facebook.com`;
  - nota `link` com `bruto=NULL` e texto `"https://m.x.com.br"` → `x.com.br` (fallback `sites_do_texto`);
  - nota `link` com `bruto` inválido (`"{"`) → fallback pelo texto, sem exceção;
  - nota `foto` com URL na legenda → 0 linhas;
  - nota `link` cujo site já estava errado em `nota_site` → linhas corrigidas.

  Rodar duas vezes deve dar as mesmas linhas (FR-011). Um snapshot de todas as colunas de `nota` antes e depois deve ser idêntico (FR-013, SC-004).
- [X] T022 [P] [US3] Escrever em `tests/test_db.py` o teste da migração com dados (quickstart §2):
  1. `command.upgrade(cfg, "0001")`;
  2. inserir por SQL 3 notas `link` (com `bruto` de fixture) e 1 `texto`;
  3. `upgrade head`;
  4. conferir que toda nota `link` tem ≥ 1 linha em `nota_site` (SC-001) e que a nota `texto` tem 0;
  5. `downgrade 0001` + `upgrade head` → mesmas linhas.

### Implementation for User Story 3

- [X] T023 [US3] Implementar `reclassificar_sites(conn: Connection) -> int` em `src/notas/repositorio.py` (research R4). Ela recebe uma conexão para servir à migração e aos testes. Para cada `id, origem, bruto, texto` com `tipo='link'`:
  - fazer `json.loads(bruto)`;
  - normalizar com `normalizar_bot_api` (origem `ao_vivo`) ou com `normalizar_exportacao(item, chat_id)` (origem `importacao`);
  - calcular `sites_da_nota`;
  - em qualquer exceção, ou com `bruto` nulo, usar `sites_do_texto(texto)`.

  Depois, numa transação: `DELETE FROM nota_site WHERE nota_id IN (SELECT id FROM nota WHERE tipo <> 'link')`, apagar as linhas das notas link e inserir as novas. Devolver quantas notas foram classificadas. T021 deve passar.
- [X] T024 [US3] Em `alembic/versions/0002_nota_site.py`, depois de criar a tabela, chamar `reclassificar_sites(op.get_bind())`. Deixar o comentário `# ponytail: importa código da aplicação; se regras mudar a ponto de quebrar banco novo, congelar a função aqui`. T022 deve passar.

**Checkpoint**: `uv run --env-file .env alembic upgrade head` numa cópia de banco da 001 deixa todos os links nos botões

---

## Phase 6: User Story 4 - Novas notas, edições e importações entram no site certo (Priority: P2)

**Goal**: captura ao vivo, edição e importação gravam `nota_site` na mesma transação da nota (FR-012, research R5)

**Independent Test**: processar `link_varios_sites.json`, depois uma edição trocando o site, depois importar `exportacao_links/`. Conferir as linhas de `nota_site` a cada passo (spec US4).

### Tests for User Story 4 ⚠️

- [X] T025 [P] [US4] Escrever em `tests/test_repositorio.py` os testes de gravação:
  - `salvar_ao_vivo(sessao, dados, sites={"a.com"})` com `tipo='link'` → 1 linha;
  - de novo com `sites={"b.com"}` (edição) → só `b.com`;
  - de novo com `tipo='texto'` e `sites=frozenset()` → 0 linhas;
  - `salvar_importada(…, sites={"c.com"})` cria as linhas, e a mesma importação de novo (nota existente) não altera nada;
  - `registrar_falha` sobre nota link existente mantém as linhas dela.
- [X] T026 [P] [US4] Escrever em `tests/test_bot.py`:
  - `processar_mensagem(link_varios_sites)` → `nota_site` = `{youtube.com, instagram.com}`;
  - `editada_com_url.json` → a nota vira link com o site da URL (acceptance 3);
  - uma edição de `link_varios_sites` com texto `https://m.facebook.com/evento` → só `facebook.com` (acceptance 2);
  - foto com URL na legenda → 0 linhas.
- [X] T027 [P] [US4] Escrever em `tests/test_importacao.py`: importar `tests/fixtures/exportacao_links/` cria as notas com `facebook.com` e `youtube.com` em `nota_site`, e a nota de texto puro fica sem linhas. As fixtures e contagens existentes de `exportacao_ok` não mudam.

### Implementation for User Story 4

- [X] T028 [US4] Em `src/notas/repositorio.py`:
  - `salvar_ao_vivo(sessao, dados, sites=frozenset())`: usar `.returning(Nota.id)` no upsert, apagar as linhas `nota_site` da nota e inserir `sites` só se `dados["tipo"] == "link"`, tudo antes do `commit` único;
  - `salvar_importada(sessao, dados, sites=frozenset())`: depois do insert que criou, usar `RETURNING id` e inserir as linhas; se não criou, não tocar em nada.

  `registrar_falha` fica sem mudança. T025 deve passar.
- [X] T029 [US4] Em `src/notas/bot.py`, `processar_mensagem` passa `sites=sites_da_nota(m) if c.tipo == "link" else frozenset()` para `salvar_ao_vivo`. T026 deve passar.
- [X] T030 [US4] Em `src/notas/importacao.py`, `_processar_item` calcula os sites do mesmo jeito (vazio no ramo de falha) e passa para `salvar_importada`. T027 deve passar.

**Checkpoint**: `uv run pytest` passa por inteiro

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T031 [P] Adicionar testes `@pytest.mark.lento` em `tests/test_repositorio.py`:
  - com 10.000 notas (metade link, distribuídas em 200 sites), `contar_por_tipo`, `contar_sites` e `buscar(tipo="link", site=…, q=…)` levam ≤ 1 s cada (SC-003);
  - `reclassificar_sites` sobre as mesmas 10.000 notas leva < 60 s (SC-004).
- [X] T032 [P] Atualizar o `README.md` do projeto:
  - abas e botões de site;
  - depois de atualizar o código, rodar `uv run --env-file .env alembic upgrade head`, que classifica as notas antigas;
  - a lista de sufixos se atualiza com `uv lock --upgrade-package publicsuffixlist`.
- [X] T033 Revisar o diff:
  - nenhum dado real, token ou banco;
  - as fixtures novas são todas inventadas;
  - `publicsuffixlist` não é usado com download.

  Depois, rodar `uv run pytest` e `uv run pytest -m lento`.
- [X] T034 Executar manualmente o quickstart.md §2–§4 e marcar os resultados

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)** → **Foundational (2)** → US2, US3, US4 → **Polish (7)**
- **US1** depende só do Setup (não usa sites) e pode começar em paralelo com a Phase 2
- Dentro da Phase 2: T003 depende de T001/T002; T006 de T004/T005; T008 de T003/T006/T007; T010 de T009

### User Story Dependencies

- **US1 (P1)**: independente (abas por tipo)
- **US2 (P1)**: Phase 2 (`NotaSite`) e US1 (as abas, porque o nav de sites fica abaixo delas e os dois mexem em `_notas.html` e `painel.py`)
- **US3 (P1)**: Phase 2 (`sites_da_nota`, tabela); independente de US1/US2. Sem US2, se verifica pelo banco
- **US4 (P2)**: Phase 2; independente de US2/US3. Sem US2, se verifica pelo banco

### Within Each User Story

- Testes → ver falhar → implementação → testes passando
- `regras` → `repositorio` → portas de entrada (`bot`, `importacao`, `painel`)

### Parallel Opportunities

- US1 (T011–T015) inteira em paralelo com a Phase 2 (T002–T010): arquivos diferentes, exceto `tests/test_repositorio.py`/`test_painel.py`, que a Phase 2 não toca
- Phase 2: T002, T004, T005, T007 e T009 (testes e fixtures) juntos
- Depois da Phase 2: US3 e US4 em paralelo com US2, mas as três tocam `src/notas/repositorio.py`, então T018, T023 e T028 vão em sequência
- Testes [P] de cada história juntos

---

## Parallel Example: Phase 2

```text
Task: "T002 testes de site() em tests/test_regras.py"
Task: "T004 fixtures em tests/fixtures/bot_api/ e tests/fixtures/exportacao_links/"
Task: "T009 testes da migração 0002 em tests/test_db.py"
```

## Parallel Example: User Story 4

```text
Task: "T025 testes de gravação em tests/test_repositorio.py"
Task: "T026 testes do bot em tests/test_bot.py"
Task: "T027 testes da importação em tests/test_importacao.py"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 + US1: abas por tipo, já útil sozinha
2. Phase 2 + US2 + US3: botões de site com o histórico inteiro classificado (é o pedido central)
3. **PARAR e validar** com quickstart §2–§3

### Incremental Delivery

1. MVP (US1 + US2 + US3)
2. \+ US4: notas novas, edições e importações entram no site sozinhas. Sem US4, o que entrar depois do upgrade fica sem site até rodar a reclassificação. Por isso US4 vem logo em seguida, antes de usar o bot de novo.
3. Polish

---

## Notes

- `site = ''` no banco ↔ `site=-` na URL ↔ "Sem site identificado" na tela (data-model)
- Commit após cada tarefa ou grupo lógico; o hook opcional `speckit.git.commit` está disponível
- Nenhuma tarefa usa dados reais
