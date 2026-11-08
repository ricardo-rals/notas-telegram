---

description: "Task list for feature 003-cartoes-links-previa"
---

# Tasks: Cartões de Links com Prévia e Painel Renovado

**Input**: Design documents from `/specs/003-cartoes-links-previa/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/painel-http.md, contracts/config.md, quickstart.md

**Tests**: obrigatórios por TDD (Constituição, Princípio V) para parsing (`linhas_whatsapp`,
itens de link, metadados HTML), checagem de destino das prévias, acesso a dados e migração.
O painel segue o padrão da 001/002. Nenhum teste acessa a internet: as prévias são testadas
contra um servidor HTTP local, com a checagem de endereço local desligada só ali, por injeção.

**Organization**: tarefas agrupadas por história de usuário (US1–US5 da spec)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1–US5 da spec
- Caminhos relativos à raiz do repositório `notas-telegram/`

---

## Phase 1: Setup

- [X] T001 Declarar `httpx` nas dependências principais com `uv add httpx` (`pyproject.toml`, `uv.lock`); sai do grupo dev só se o uv mover sozinho, sem mudar a versão (plan, Technical Context)
- [X] T002 [P] Escrever em `tests/test_config.py` os testes de `PREVIAS_LINKS` (devem falhar): ausente → `previas_links is True`; `0` → `False`; `1` → `True`; `sim` → `ErroConfig` com o nome da variável (contracts/config.md)
- [X] T003 Adicionar `previas_links: bool = True` a `Config` em `src/notas/config.py`. Ler `PREVIAS_LINKS`: só `0` e `1` são válidos, outro valor dá erro de configuração. Acrescentar ao `.env.example`, com comentário, a linha `PREVIAS_LINKS=1` (`0` desliga toda requisição além do Telegram). T002 deve passar.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: regras puras dos itens de link e o novo esquema (`link`, `previa`, `previa_fts`, sem `nota_site`)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase.

- [X] T004 [P] Criar a fixture inventada `tests/fixtures/bot_api/whatsapp_9_links.json` (chat `-1001234567890`, remetente `111`, `message_id` 60). O texto tem 9 linhas, as mesmas URLs do pedido, cada uma prefixada por `[HH:MM, 05/11/2026] Usuario: `, com as horas `12:40 12:44 14:10 15:09 16:04 20:30 20:37 20:39 20:41`. A primeira URL é `https://imp.i384100.net/cbUijS`, as outras 8 são `https://www.instagram.com/...`. Cada URL tem uma entidade `url` com offset/length em UTF-16 (gerar por script, como na 002).
- [X] T005 [P] Escrever em `tests/test_regras.py` os testes de `linhas_whatsapp(texto)` (devem falhar):
  - `[12:40, 05/11/2026] Usuario: x` → `(0, <iso UTC de 05/11/2026 12:40 local>, "Usuario")`;
  - a ordem `[05/11/2026, 12:40]` e `[05/11/2026 12:40]` dá o mesmo resultado;
  - autor com espaço (`Ana Maria`);
  - `[25:99, 31/02/2026] X: y` → data `None`, autor `None`;
  - linha sem prefixo → `None, None`;
  - o índice de início de cada linha está correto num texto com `\n`.

  Para a data esperada, usar `datetime(2026,11,5,12,40).astimezone().astimezone(UTC).isoformat(timespec="seconds")`.
- [X] T006 [P] Escrever em `tests/test_regras.py` os testes de `posicoes` e `itens_de_link(m)` (devem falhar):
  - `whatsapp_9_links` → 9 `ItemLink`, posições 0..8, sites `["i384100.net"] + ["instagram.com"]*8`, cada um com a data e o autor `"Usuario"` da sua linha (SC-001);
  - `link_varios_sites` (002) → `posicoes` corretas apesar do emoji;
  - `link_text_link` → 1 item, com a data da mensagem e autor `None`;
  - URL repetida → 1 item;
  - duas URLs na mesma linha do WhatsApp → as duas com a data da linha;
  - nota de link sem URL extraível → 1 item sentinela (`url=""`, `site=""`, `posicao=0`);
  - `itens_do_texto("https://a.com\nhttps://b.com", enviada_em)` → 2 itens com `enviada_em`;
  - exportação (`exportacao_links/result.json`): `posicoes` calculadas pela soma dos `text_entities`.
- [X] T007 Em `src/notas/regras.py`:
  - acrescentar `posicoes: tuple[int, ...] = ()` a `MensagemNormalizada`. `_urls` passa a devolver pares `(url, posicao)` e os adaptadores preenchem `urls` e `posicoes`:
    - Bot API: `len(utf16[:off*2].decode("utf-16-le"))`;
    - exportação: soma dos comprimentos de `text` dos `text_entities` anteriores;
    - regex: `m.start()`;
    - a deduplicação mantém a primeira ocorrência.
  - implementar `linhas_whatsapp` com a regex de research R2 e `strptime` (data inválida → `None`);
  - implementar `ItemLink` (dataclass congelada: `posicao, url, site, data, autor`), `itens_de_link(m)` e `itens_do_texto(texto, enviada_em)`:
    - cada URL acha a sua linha com `bisect`;
    - o site vem de `site(url) or ""`;
    - o resultado nunca é vazio (sentinela);
    - nenhuma das duas levanta exceção.
  - manter `sites_da_nota`/`sites_do_texto` só se ainda usados; remover se não.

  T005 e T006 devem passar, e os testes de `urls` da 002 continuam passando.
- [X] T008 [P] Escrever em `tests/test_db.py` os testes da migração `0003` (devem falhar):
  - existem `link`, `previa` e `previa_fts`, e `nota_site` não existe;
  - `UNIQUE (nota_id, url)` e `UNIQUE (nota_id, posicao)` rejeitam duplicata;
  - `previa.situacao` tem CHECK `pendente, ok, indisponivel`;
  - apagar a nota apaga os seus `link` (CASCADE);
  - os índices `link_site_data`, `link_data` e `previa_fila` existem;
  - a FTS de `previa` encontra "Reunião" buscando "REUNIAO" depois de um UPDATE do título;
  - `downgrade 0002` recria `nota_site` e remove as tabelas novas.

  Remover ou ajustar os testes da 002 que dependiam de `nota_site` em `head` (`test_nota_site_*`, `test_migracao_0002_classifica_notas_antigas`). O teste de dados antigos passa a ser o T020.
- [X] T009 Em `alembic/versions/0002_nota_site.py`, remover a chamada a `reclassificar_sites` e o comentário `ponytail:`. No lugar, comentar que a `0003` reconstrói tudo e remove a tabela (research R1).

  Criar `alembic/versions/0003_link_previa.py` (`revision="0003"`, `down_revision="0002"`) com:
  - `link (id INTEGER PRIMARY KEY, nota_id INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE, posicao INTEGER NOT NULL, url TEXT NOT NULL, site TEXT NOT NULL, data TEXT NOT NULL, autor TEXT, UNIQUE(nota_id, url), UNIQUE(nota_id, posicao))`;
  - os índices `link_site_data (site, data DESC)` e `link_data (data DESC, posicao)`;
  - `previa (url TEXT PRIMARY KEY, situacao TEXT NOT NULL CHECK (situacao IN ('pendente','ok','indisponivel')), titulo TEXT, descricao TEXT, imagem TEXT, erro TEXT, definitiva INTEGER NOT NULL DEFAULT 0, tentativas INTEGER NOT NULL DEFAULT 0, buscada_em TEXT, tentar_depois_de TEXT)`;
  - o índice `previa_fila (situacao, tentar_depois_de)`;
  - `previa_fts` FTS5 `(titulo, descricao)` com `content='previa'` e `tokenize='unicode61 remove_diacritics 2'`, mais os triggers AFTER INSERT/DELETE/UPDATE OF titulo, descricao (como a `nota_fts` da 0001);
  - `DROP TABLE nota_site`.

  O `downgrade` faz o inverso e recria `nota_site` vazia (comentar que voltar à 002 exige reclassificar, fora do escopo).

  Em `src/notas/db.py`: trocar `NotaSite` por `Link` (`id, nota_id, posicao, url, site, data, autor`) e `Previa` (colunas acima). T008 deve passar.

**Checkpoint**: `uv run pytest tests/test_regras.py tests/test_db.py tests/test_config.py` passa. O resto da suíte pode falhar até a US1 trocar `NotaSite` por `Link`.

---

## Phase 3: User Story 1 - Um item por link (Priority: P1) 🎯 MVP

**Goal**: a mensagem com 9 links vira 9 itens na aba Link, cada um no seu site, com data e autor da linha; nas outras abas, uma nota com mini-cartões

**Independent Test**: processar `whatsapp_9_links.json` e conferir 9 itens em `/?tipo=link` (8 em `instagram.com`) e uma nota com 9 mini-cartões em `/` (spec US1)

### Tests for User Story 1 ⚠️ (escrever primeiro e ver falhar)

- [X] T010 [P] [US1] Reescrever, em `tests/test_repositorio.py`, os testes da 002 que usavam `NotaSite` para usar `Link`, com a nova semântica: os botões contam itens (uma nota com 2 URLs de `youtube.com` conta 2). Acrescentar:
  - `salvar_ao_vivo(sessao, dados, itens=[...])` grava os itens;
  - uma edição com menos itens apaga os removidos (FR-004);
  - `tipo` não-link → 0 itens;
  - link sem itens informados → sentinela;
  - `salvar_importada` só grava ao criar;
  - `registrar_falha` mantém os itens;
  - `contar_por_tipo(sessao)["link"]` conta itens e as demais chaves contam notas (FR-002);
  - `buscar_links(sessao, site=None, q="", pagina=1) -> (list[(Link, Nota, Previa|None)], total)`: 50 por página, ordenados por `data DESC, posicao`, com `site` (`""` = sentinela), `q` casando com `nota_fts` **ou** `previa_fts`, e `site` inexistente → `([], 0)`;
  - `links_das_notas(sessao, ids) -> dict[int, list[(Link, Previa|None)]]` numa consulta só;
  - `reconstruir_links(conn)`, idempotente, a partir de `bruto` (fallback `itens_do_texto`), sem alterar nenhuma coluna de `nota`: substitui o `test_reclassificar_sites`.
- [X] T011 [P] [US1] Escrever em `tests/test_bot.py` e `tests/test_importacao.py`:
  - `processar_mensagem(whatsapp_9_links)` → 9 linhas em `link`, com datas distintas e autor `Usuario`;
  - editar a mensagem removendo 2 linhas → 7 itens;
  - importar `exportacao_links/` → itens com `facebook.com` e `youtube.com`, e a nota de texto sem itens.

  Ajustar os testes da 002 que liam `NotaSite`.
- [X] T012 [P] [US1] Escrever em `tests/test_db.py` o teste de migração com dados: `upgrade 0001` → inserir por SQL as notas de link com `bruto` de `whatsapp_9_links` e `link_varios_sites` e uma nota de texto → `upgrade head` → 9 + 3 itens, 0 para o texto, `nota_site` ausente; `downgrade 0002` + `upgrade head` → mesmos itens (FR-015).
- [X] T013 [P] [US1] Escrever em `tests/test_painel.py` (contracts/painel-http.md):
  - `/?tipo=link` com a mensagem de exemplo → 9 `<article class="cartao link">`, `instagram.com (8)`, aba `Link (9)`;
  - cada cartão mostra `05/11/2026 12:40 · Usuario` (data no fuso local);
  - `/` → 1 `<article class="cartao nota">` contendo 9 cartões de link, e aba `Todas (1)`;
  - `site=instagram.com` → 8 cartões;
  - paginação de itens: 52 itens → 50 na página 1;
  - nota de link sem URL → cartão sentinela com o texto da nota.

  Ajustar os testes de botões da 002 para a nova semântica.

### Implementation for User Story 1

- [X] T014 [US1] Em `src/notas/repositorio.py`:
  - trocar `_gravar_sites` por `_gravar_links(sessao, nota_id, tipo, itens)`: apaga e insere; só link; vazio → sentinela com `data = dados["enviada_em"]`;
  - `salvar_ao_vivo` e `salvar_importada` passam a receber `itens: list[ItemLink] = ()`;
  - reescrever `contar_sites` sobre `link` (contagem de itens, `''` por último);
  - `contar_por_tipo`: `link` = `count(*)` de `link`;
  - implementar `buscar_links` e `links_das_notas`;
  - `buscar(tipo="link")` deixa de ser usado pelo painel, mas continua válido;
  - trocar `reclassificar_sites`/`_sites_guardados` por `reconstruir_links(conn)` (mesma estrutura, gravando `ItemLink`).

  T010 deve passar.
- [X] T015 [US1] Em `src/notas/bot.py` e `src/notas/importacao.py`, passar `itens=itens_de_link(m) if c.tipo == "link" else []` no lugar de `sites`. No ramo de falha da importação, `itens=[]`. T011 deve passar.
- [X] T016 [US1] Em `alembic/versions/0003_link_previa.py`, depois de criar as tabelas e antes do `DROP TABLE nota_site`, chamar `reconstruir_links(op.get_bind())`, com o comentário `# ponytail: importa código da aplicação; se regras mudar a ponto de quebrar banco novo, congelar a função aqui`. T012 deve passar.
- [X] T017 [US1] Criar `src/notas/templates/_cartao_link.html`: o cartão do contrato (`<article class="cartao link">`, `<a class="previa" href target="_blank" rel="noopener noreferrer">`, `<h3>` com o título da prévia ou a URL, meta `site · data local[ · autor] · abrir no Telegram`; sentinela → texto da nota sem link externo; nada com `|safe`).

  Criar `src/notas/templates/_links.html`: as abas e os sites como hoje, mais a grade `<div class="grade">` de cartões de link e a paginação.

  Em `src/notas/templates/_notas.html`: cada nota vira `<article class="cartao nota">` e inclui seus mini-cartões de link (`_cartao_link.html`) quando `tipo == 'link'`.
- [X] T018 [US1] Em `src/notas/painel.py`:
  - com `tipo == "link"`, usar `buscar_links` e o modelo `_links.html` (fragmento) dentro de `lista.html`;
  - nas outras abas, `buscar` + `links_das_notas` para os ids da página;
  - o contexto ganha `links_por_nota`;
  - o filtro `data_local` também é usado para `link.data`.

  T013 deve passar e a suíte inteira volta a passar.

**Checkpoint**: `uv run pytest` passa; o MVP (itens por link, sem prévia) está utilizável

---

## Phase 4: User Story 2 - Cartão com prévia da página (Priority: P1)

**Goal**: título, descrição e miniatura buscados uma vez por URL, em segundo plano, sem acessar a rede local; desligável

**Independent Test**: com um servidor HTTP local servindo as páginas de teste, gravar links para ele e conferir os cartões com prévia; com `previas_links=False`, nenhum acesso (spec US2)

### Tests for User Story 2 ⚠️

- [X] T019 [P] [US2] Criar `tests/fixtures/paginas/`, todas inventadas:
  - `og_completo.html`: `og:title`, `og:description` e `og:image=/img.png`, com charset `iso-8859-1` num título acentuado;
  - `so_twitter.html`;
  - `so_title.html`;
  - `sem_metadados.html`;
  - `malicioso.html`: `<title><script>alert(1)</script>Oi</title>` e `og:description` com `<b>`;
  - `img.png` (PNG 1×1 válido).
- [X] T020 [P] [US2] Escrever `tests/test_previas.py` (deve falhar).
  - `extrair_metadados(html, base_url)`:
    - a ordem de preferência de research R5 em cada fixture;
    - corte em 200 e 300 caracteres;
    - espaços normalizados;
    - a imagem resolvida com `urljoin`;
    - o malicioso devolve texto puro (`"<script>alert(1)</script>Oi"` como string, que o template vai escapar);
    - o parser para no `</head>`.
  - `destino_permitido(url, resolver)`, com um `resolver` falso injetado:
    - recusa `127.0.0.1`, `10.0.0.1`, `192.168.1.1`, `169.254.1.1`, `::1`, host que resolve para IP privado, esquema `ftp:`/`file:`;
    - aceita host que resolve só para IP global.
  - `buscar_previa(url, cliente, resolver, media_dir)` contra um servidor `http.server` local numa thread, com o resolver injetado aceitando `127.0.0.1` só no teste:
    - ok com título, descrição e imagem salva em `media_dir/previas/<sha1>.png`;
    - `Content-Type: application/pdf` → recusa definitiva;
    - 404 → falha temporária;
    - redirecionamento para `http://10.0.0.1/` → recusa definitiva (`endereço local`);
    - mais de 5 redirecionamentos → falha;
    - corpo de 2 MB → só 512 KB lidos, sem erro;
    - imagem de 6 MB → prévia ok sem imagem;
    - servidor que demora mais que o timeout (usar timeout de 0,5 s no teste) → falha temporária.
- [X] T021 [P] [US2] Escrever em `tests/test_repositorio.py` os testes da fila:
  - `_gravar_links` cria `previa(url,'pendente')` para cada URL não vazia (INSERT OR IGNORE: a mesma URL em duas notas = 1 prévia, FR-005/SC-004);
  - `proximas_previas(sessao, agora, limite=5)` devolve pendentes e indisponíveis não definitivas com `tentar_depois_de <= agora`;
  - `registrar_previa(sessao, url, resultado, agora)`:
    - aplica as transições de data-model;
    - o recuo segue `1 h, 6 h, 24 h, 7 d, 7 d`;
    - uma recusa definitiva nunca volta à fila.
- [X] T022 [P] [US2] Escrever em `tests/test_painel.py`:
  - cartão com prévia `ok` → `<img src="/media/previas/…">`, `<h3>` com o título e a descrição;
  - o título malicioso aparece escapado (`&lt;script&gt;`);
  - cartão `pendente`/`indisponivel` → a URL no `<h3>`, sem `<img>`;
  - toda resposta tem o cabeçalho `Content-Security-Policy` exato de research R7;
  - `criar_app(cfg com previas_links=False)` não inicia a thread (verificar com um iniciador injetado ou com `threading.enumerate()` por nome `previas`).

### Implementation for User Story 2

- [X] T023 [US2] Criar `src/notas/previas.py` com:
  - `extrair_metadados` (`HTMLParser` da stdlib, research R5);
  - `destino_permitido(url, resolver=socket.getaddrinfo)`: todos os IPs `is_global`;
  - `buscar_previa(url, cliente, resolver, media_dir) -> ResultadoPrevia(situacao, definitiva, titulo, descricao, imagem, erro)`:
    - redirecionamentos manuais (no máximo 5), checando cada destino;
    - só `text/html`, até 512 KB, charset do cabeçalho ou utf-8 com `replace`;
    - imagem `image/*` até 5 MB, gravada em `previas/<sha1(url)>.<ext>`;
    - o timeout vem do cliente;
    - `User-Agent: notas-telegram/0.3 (+prévia de link)`.
  - `rodar_fila(engine, cfg, parar: threading.Event)`: laço a cada 5 s com `proximas_previas`, `buscar_previa` e `registrar_previa`, sessão própria. Exceção numa URL → registra falha temporária e segue.

  Deixar os comentários `ponytail:` de research R3 e R4. T020 deve passar.
- [X] T024 [US2] Em `src/notas/repositorio.py`, implementar `proximas_previas` e `registrar_previa`, e acrescentar o INSERT OR IGNORE de `previa` em `_gravar_links` e em `reconstruir_links`. T021 deve passar.
- [X] T025 [US2] Em `src/notas/painel.py`:
  - o middleware `so_local` acrescenta o cabeçalho CSP a toda resposta;
  - `criar_app(cfg, engine, iniciar_previas=True)`: se `cfg.previas_links` e `iniciar_previas`, inicia `threading.Thread(target=rodar_fila, name="previas", daemon=True)`; os testes passam `iniciar_previas=False` por padrão no fixture `cliente`.

  Em `src/notas/templates/_cartao_link.html`, mostrar `<img src="/media/{{ previa.imagem }}" alt="" loading="lazy">` e a descrição quando `previa.situacao == 'ok'`, e o texto "prévia indisponível" discreto quando `indisponivel`. T022 deve passar.

**Checkpoint**: com o painel rodando, links novos ganham prévia sozinhos; `PREVIAS_LINKS=0` não faz nenhuma requisição

---

## Phase 5: User Story 3 - Abrir o link e a mensagem original (Priority: P1)

**Goal**: título/miniatura abrem o link numa aba nova; "abrir no Telegram" continua; tudo pelo teclado

**Independent Test**: num cartão, conferir `href`/`target` dos dois links e a ordem de foco (spec US3)

- [X] T026 [P] [US3] Escrever em `tests/test_painel.py`:
  - cartão com prévia: exatamente um `<a class="previa" href="{url}" target="_blank" rel="noopener noreferrer">`, envolvendo `<img>` e `<h3>`;
  - cartão sem prévia: o mesmo `<a>` com a URL como texto;
  - cada cartão tem `<a href="https://t.me/c/…">abrir no Telegram</a>`;
  - nenhum `tabindex` positivo na página;
  - o sentinela não tem link externo.
- [X] T027 [US3] Ajustar `src/notas/templates/_cartao_link.html`, se necessário, para T026 passar: um único link externo por cartão, para não duplicar paradas de Tab, e o link do Telegram depois dele na ordem do HTML.

---

## Phase 6: User Story 4 - Baixar os arquivos (Priority: P2)

**Goal**: botão "Baixar" em foto, áudio e documento com arquivo, salvando com o nome original

**Independent Test**: `GET /baixar/{id}` devolve o arquivo com `Content-Disposition` certo; sem arquivo → 404 amigável (spec US4)

- [X] T028 [P] [US4] Escrever em `tests/test_painel.py` (contracts/painel-http.md, `/baixar`):
  - documento `boleto.pdf` → 200, `Content-Disposition: attachment; filename*=UTF-8''boleto.pdf`, e o corpo é o arquivo;
  - nome com acento (`relatório.pdf`) codificado em `filename*`;
  - foto sem `arquivo_nome` → usa `arquivo_caminho`;
  - nota inexistente, nota sem arquivo e arquivo apagado do disco → 404 com "Arquivo não encontrado" e link para `/`;
  - `arquivo_caminho` igual a `../fora.txt` → 404;
  - o botão `<a href="/baixar/{id}">Baixar</a>` aparece em foto, áudio e documento com arquivo, e não aparece em vídeo, `grande_demais` e `sem_arquivo`.
- [X] T029 [US4] Em `src/notas/painel.py`, implementar `GET /baixar/{nota_id}` (research R8):
  - resolver `cfg.media_dir / arquivo_caminho` e recusar o que ficar fora de `media_dir.resolve()`;
  - devolver `FileResponse(..., filename=nome)`, porque o Starlette já gera o `filename*` UTF-8;
  - 404 com o template novo `src/notas/templates/nao_encontrado.html`.

  Em `src/notas/templates/_notas.html`, acrescentar o botão "Baixar" na linha de ações e manter a miniatura e o player como estão. T028 deve passar.

---

## Phase 7: User Story 5 - Painel em cartões, legível em qualquer largura (Priority: P2)

**Goal**: hierarquia clara, grade responsiva, foco visível, claro/escuro (FR-013, FR-014)

**Independent Test**: janelas de 360 px e 1280 px e navegação só por teclado (quickstart §5)

- [X] T030 [P] [US5] Escrever em `tests/test_painel.py` os testes estruturais:
  - `<meta name="viewport" content="width=device-width, initial-scale=1">` presente;
  - o CSS contém `:focus-visible`, `grid-template-columns: repeat(auto-fill, minmax(260px, 1fr))` e `overflow-wrap: anywhere`;
  - no cartão de nota, a ordem no HTML é conteúdo → `.meta` → `.acoes`;
  - nota `falha` tem a classe `falha` e o erro.
- [X] T031 [US5] Reescrever o `<style>` de `src/notas/templates/base.html` (research R10), sem JS novo:
  - variáveis de cor para claro e escuro (`prefers-color-scheme`), com contraste ≥ 4,5:1 no texto;
  - `.cartao` com borda, raio e padding;
  - `.grade` com `repeat(auto-fill, minmax(260px, 1fr))`;
  - imagem do cartão com `aspect-ratio: 1.91/1; object-fit: cover; width: 100%`;
  - `h3` limitado a 3 linhas com `line-clamp`, descrição a 2;
  - `nav.abas` com `flex-wrap`;
  - `:focus-visible { outline: 2px solid; outline-offset: 2px }`;
  - `overflow-wrap: anywhere` em URLs e textos;
  - `max-width` do `body` maior na aba Link (classe no `<main>`).

  Ajustar `lista.html`/`_notas.html` para a ordem conteúdo → meta → ações. T030 deve passar.
- [X] T032 [US5] Validar manualmente o quickstart.md §5 (360 px, 1280 px, Tab, claro e escuro) e registrar o resultado no fim de `quickstart.md`

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T033 [P] Escrever em `tests/test_repositorio.py` um teste `@pytest.mark.lento`: 10.000 notas, das quais 2.500 de link com 2 URLs cada (5.000 itens em 200 sites), e metade das prévias `ok`. `contar_por_tipo`, `contar_sites`, `buscar_links(site=…, q=…)` e `buscar` + `links_das_notas` levam ≤ 1 s cada (SC-005); `reconstruir_links` leva < 60 s.
- [X] T034 [P] Atualizar o `README.md`:
  - cartões e prévias;
  - `PREVIAS_LINKS` e o que é acessado na rede quando a variável está ligada;
  - Instagram pode negar a prévia;
  - rodar `alembic upgrade head` depois de atualizar;
  - link para o quickstart da 003.
- [X] T035 Revisar o diff:
  - nenhum dado real, token ou banco;
  - fixtures inventadas;
  - nenhum teste acessa a internet (rodar `uv run pytest` sem rede, ou conferir que todo `buscar_previa` em teste usa o servidor local);
  - nenhum `|safe` nos templates.

  Depois, `uv run pytest` e `uv run pytest -m lento`.
- [X] T036 Executar o quickstart.md §2–§4 numa cópia do banco e com a mensagem de exemplo, e registrar os resultados

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)** → **Foundational (2)** → **US1 (3)** → US2, US3, US4, US5 → **Polish (8)**
- Na Phase 2: T007 depende de T004–T006; T009 depende de T008 e de T007 (o modelo usa `ItemLink` só na US1, mas a migração já precisa existir)

### User Story Dependencies

- **US1 (P1)**: Phase 2. Troca `NotaSite` por `Link` em todo o código e por isso vem antes de tudo
- **US2 (P1)**: US1 (`_gravar_links`, `_cartao_link.html`) e Setup (T003, `previas_links`)
- **US3 (P1)**: US1 (cartão). Pequena; pode ir junto com US2, mas os dois tocam `_cartao_link.html`, então em sequência
- **US4 (P2)**: só US1 (cartão de nota); independente de US2/US3
- **US5 (P2)**: depois de US1–US4, porque reescreve o CSS sobre os templates finais

### Within Each User Story

- Fixtures e testes → ver falhar → implementação → testes passando
- `regras` / `previas` → `repositorio` → portas de entrada (`bot`, `importacao`, `painel`) → templates

### Parallel Opportunities

- Setup: T002 com T001
- Phase 2: T004, T005, T006 e T008 juntos
- US1: T010–T013 (testes) juntos
- US2: T019–T022 juntos; T023 (`previas.py`) em paralelo com T024 (`repositorio.py`)
- US4 (T028–T029) em paralelo com US2/US3: arquivos diferentes, exceto `_notas.html`/`painel.py`, então coordenar T025 e T029
- Polish: T033 e T034 juntos

---

## Parallel Example: Phase 2

```text
Task: "T004 fixture whatsapp_9_links.json"
Task: "T005 testes de linhas_whatsapp em tests/test_regras.py"
Task: "T008 testes da migração 0003 em tests/test_db.py"
```

## Parallel Example: User Story 2

```text
Task: "T019 páginas de teste em tests/fixtures/paginas/"
Task: "T020 testes de previas.py em tests/test_previas.py"
Task: "T021 testes da fila em tests/test_repositorio.py"
```

---

## Implementation Strategy

### MVP First

1. Setup + Foundational + US1: a lista do WhatsApp vira 9 itens com data e autor, sem prévia
2. **PARAR e validar** com quickstart §2–§3 (itens 1–3)

### Incremental Delivery

1. MVP (US1)
2. \+ US3: abrir link e Telegram, que é barato e completa o cartão
3. \+ US2: prévias, a maior parte do risco (rede e segurança)
4. \+ US4: baixar
5. \+ US5: CSS final
6. Polish

---

## Notes

- `link.site = ''` ↔ `site=-` na URL ↔ "Sem site identificado" (como na 002)
- As contagens da aba Link passam a contar links, não mensagens (Q2 = A). Os testes da 002 que contavam notas por site são ajustados em T010/T013
- Commit após cada tarefa ou grupo lógico (`/speckit-git-commit` ou manual)
