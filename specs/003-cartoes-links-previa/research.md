# Research: Cartões de Links com Prévia e Painel Renovado

Sem `NEEDS CLARIFICATION` no Technical Context. As decisões abaixo fecham as escolhas abertas.

## R1. Item de link substitui `nota_site`

- **Decision**: nova tabela `link` (um registro por URL distinta de uma nota de link). Ela
  passa a ser a fonte dos botões de site e da lista da aba Link. A migração `0003` cria `link`,
  reconstrói os itens de todas as notas e **remove `nota_site`**.
- **Rationale**: na 003, site é atributo de cada link, não da nota (FR-003), e a aba Link conta
  itens (FR-002). Manter `nota_site` ao lado de `link` seria guardar o mesmo dado duas vezes,
  e as duas cópias poderiam divergir.
- **Consequência na `0002`**: hoje a `0002` chama `repositorio.reclassificar_sites`, que vai
  deixar de existir (o risco anotado com `ponytail:` na 002). A `0002` passa a só criar a
  tabela, sem preencher. Como a `0003` reconstrói tudo a partir de `nota`, o resultado de
  `0001 → head` é o mesmo, e bot e painel só aceitam o banco em `head`.
- **Alternatives considered**: manter `nota_site` e acrescentar `link`: duplicação sem uso.

## R2. Posição de cada URL e linha do WhatsApp

- **Decision**: `MensagemNormalizada` ganha `posicoes: tuple[int, ...]`, paralelo a `urls`:
  o índice (em caracteres) onde cada URL começa no texto.
  - Bot API: entidade `url`/`text_link` → offset UTF-16 convertido para índice de caractere
    (`len(utf16[:off*2].decode("utf-16-le"))`).
  - Exportação: soma dos comprimentos dos `text_entities` anteriores.
  - Regex: `match.start()`.
- `linhas_whatsapp(texto) -> list[tuple[int, str | None, str | None]]`: para cada linha, o
  índice de início, a data (ISO UTC) e o autor, quando a linha casa com
  `^\[(?:(HH:MM), (DD/MM/AAAA)|(DD/MM/AAAA),? (HH:MM))\] ([^:\n]{1,60}): `. A data é
  validada por `datetime.strptime`; data impossível → `None`. A hora local vira UTC com
  `datetime.astimezone()`.
- Cada URL herda data/autor da linha que contém sua posição (`bisect`). Sem linha válida →
  data da mensagem, autor `None` (FR-016).
- **Rationale**: as posições já vêm de graça das entidades que a 002 lê. Ligar URL à linha
  pela posição funciona até para `text_link`, cujo endereço não está no texto.
- **Alternatives considered**: procurar a URL no texto com `find`: falha para `text_link` e
  quando a mesma URL aparece em duas linhas.

## R3. Quem busca as prévias

- **Decision**: uma thread daemon no **processo do painel**, iniciada em `criar_app` quando
  `PREVIAS_LINKS` está ligado. A cada 5 s ela pega até 5 prévias com `situacao='pendente'`
  ou com `tentar_depois_de` vencido, e busca uma de cada vez.
- **Rationale**: Princípio VI (sem processo novo). A captura no bot não espera nada (FR-007):
  o bot só grava `previa(url, 'pendente')`. O painel é onde a prévia importa, e já tem uma
  thread (a importação). Com WAL e `busy_timeout`, um escritor curto a mais não trava ninguém.
- **Alternatives considered**:
  - Tarefa assíncrona no bot: com só o painel aberto (ex.: depois de uma importação), nada
    seria buscado.
  - Processo `python -m notas.previas`: viola o Princípio VI sem necessidade medida.
- `ponytail:` uma thread e uma busca por vez. Se houver milhares de links pendentes depois de
  uma importação, o teto é ~1 prévia/s. Melhoria possível: um pool pequeno.

## R4. Buscar a página com segurança (FR-008, FR-009, FR-010)

- **Decision**: usar `httpx` (já instalado como dependência do python-telegram-bot; passa a ser
  declarado direto no `pyproject.toml`). Configuração e regras:
  - Cliente síncrono com `timeout=10 s`, `follow_redirects=False`, `User-Agent` honesto
    (`notas-telegram/0.3 (+prévia de link)`).
  - Redirecionamentos seguidos à mão, no máximo 5. **Cada** destino passa pela checagem abaixo.
  - Checagem de destino: o esquema é `http` ou `https`; `socket.getaddrinfo(host)`. Todos os
    IPs devolvidos precisam ser globais (`ipaddress.ip_address(ip).is_global`). Loopback,
    privado, link-local e reservado → recusado (`indisponivel`, motivo `endereço local`).
  - Página: só `Content-Type: text/html`. Lê no máximo 512 KB do corpo (`iter_bytes`) e
    decodifica pelo charset do cabeçalho, com `utf-8` e `errors="replace"` como padrão.
  - Imagem: mesma checagem de destino; só `image/*`; no máximo 5 MB. Salva em
    `MEDIA_DIR/previas/<sha1(url)>.<ext>`.
- `ponytail:` checar o IP antes de conectar deixa a janela de DNS rebinding entre a checagem e
  a conexão. Para um caderno pessoal, isso é aceitável. Melhoria possível: um transport que
  conecta no IP já checado.
- **Alternatives considered**:
  - `requests`: dependência nova para o que `httpx` já faz.
  - Seguir redirecionamentos automaticamente: o destino final escaparia da checagem.

## R5. Ler título, descrição e imagem

- **Decision**: `html.parser.HTMLParser` da stdlib, numa classe pequena em `previas.py` que
  coleta `<meta property|name>` e o primeiro `<title>`. Ordem de preferência:
  - título: `og:title` → `twitter:title` → `<title>`;
  - descrição: `og:description` → `twitter:description` → `description`;
  - imagem: `og:image` → `twitter:image`, resolvida com `urljoin`.
  - O parser para no `</head>`. Espaços são normalizados. Corte em 200 caracteres (título) e
    300 (descrição).
- **Rationale**: regra determinística (Princípio II), sem dependência. O que vem da página é
  texto puro: o Jinja escapa tudo e o painel nunca usa `|safe` (FR-010).
- **Alternatives considered**: BeautifulSoup/lxml: dependência para meia dúzia de tags.

## R6. Novas tentativas

- **Decision**: `previa.tentativas` cresce a cada falha. `tentar_depois_de = agora + [1 h, 6 h,
  24 h, 7 d][min(tentativas-1, 3)]`. Recusas definitivas (endereço local, esquema não http,
  conteúdo não HTML) não são tentadas de novo. Com `PREVIAS_LINKS` desligado, a thread nem
  inicia.
- **Rationale**: atende "nova tentativa depois de um intervalo, nunca em loop" com uma coluna.

## R7. O painel nunca carrega nada de fora (FR-010)

- **Decision**: o middleware que já existe acrescenta o cabeçalho
  `Content-Security-Policy: default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'`.
  As miniaturas são servidas de `/media/previas/`.
- **Rationale**: mesmo que algum texto escapasse, o navegador recusa scripts e imagens externas.
  Já existe CSS inline em `base.html`, por isso `style-src` permite inline. HTMX 2 não precisa de `eval`.

## R8. Botão Baixar com nome certo e arquivo ausente (FR-012)

- **Decision**: rota `GET /baixar/{nota_id}`, que devolve `FileResponse` com
  `Content-Disposition: attachment; filename*=UTF-8''<arquivo_nome ou arquivo_caminho>`. O
  caminho é resolvido dentro de `MEDIA_DIR`, e caminho fora dela é recusado. Arquivo ausente
  → 404 com página HTML curta "Arquivo não encontrado" e link de volta.
- **Rationale**: o atributo `download` é ignorado em alguns casos e, com o arquivo ausente,
  baixaria a página de erro como se fosse o arquivo. Uma rota pequena resolve os dois.

## R9. Busca por título da prévia (caso de borda da spec)

- **Decision**: FTS5 `previa_fts(titulo, descricao)` com `content='previa'` e o mesmo
  tokenizador da `nota_fts` (sem diferença de maiúsculas e acentos), mantida por triggers. Na
  aba Link, um item aparece se o texto da nota **ou** a prévia da sua URL casa com a busca.

## R10. Layout

- **Decision**: CSS puro em `base.html`, sem framework:
  - aba Link: `display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr))`;
  - demais abas: uma coluna de cartões de nota, com os links em mini-cartões numa grade
    interna;
  - abas e botões de site: `flex-wrap`;
  - `:focus-visible` com contorno de 2 px;
  - `img { aspect-ratio: 1.91/1; object-fit: cover }` com altura fixa, para o cartão não pular;
  - `overflow-wrap:anywhere` nos endereços, para não haver rolagem horizontal em 360 px.
- **Rationale**: tudo nativo do navegador (Princípio VI, e a regra "CSS antes de JS").
