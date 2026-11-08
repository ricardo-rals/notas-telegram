# Feature Specification: Cartões de Links com Prévia e Painel Renovado

**Feature Branch**: `003-cartoes-links-previa`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Melhorar a apresentação das notas no painel e a leitura de links. 1) Uma mensagem com vários links (ex.: lista colada do WhatsApp no formato "[12:40, 05/11/2026] Usuario: https://...", uma por linha) mostra um item separado por link, cada um no seu site, em vez de um bloco de texto. 2) Cada link aparece num cartão com prévia da página (título, descrição curta e miniatura), buscada uma vez e guardada no computador; a busca pode ser desligada na configuração. 3) O cartão abre o link direto no site e mantém o link para a mensagem original no Telegram. 4) Fotos, áudios e documentos baixados ganham um botão de baixar o arquivo. 5) Visual geral: layout em cartões, hierarquia clara, bom em tela estreita, continua utilizável pelo teclado. Fora do escopo: abrir encurtadores para descobrir o destino, baixar vídeos, reproduzir o conteúdo do Instagram dentro do painel."

## Clarifications

### Session 2026-11-06

- Q: Linhas no formato do WhatsApp (`[12:40, 05/11/2026] Usuario: …`): data e autor de cada
  linha ou data da mensagem? → A: ler data e autor de cada linha e mostrar no cartão; linha
  fora do padrão usa a data da mensagem (FR-016, FR-017).
- Q: Fora da aba Link, a lista mostra um item por link ou uma nota por mensagem? → A: uma nota
  por mensagem, com os links dela em cartões dentro dela; só a aba Link lista um item por link
  (FR-002).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Um item por link, mesmo numa mensagem com vários (Priority: P1)

Colo no grupo uma lista de links, por exemplo copiada do WhatsApp, com uma linha por link no
formato `[12:40, 05/11/2026] Usuario: https://...`. No painel, em vez de um bloco de texto
com tudo junto, vejo um item separado para cada link, e cada item fica no botão do seu site.

**Why this priority**: é o problema concreto de hoje. Uma lista de 9 links aparece como uma
nota só, não dá para ver nem filtrar cada link.

**Independent Test**: enviar a mensagem de exemplo com 9 links (1 de `i384100.net` e 8 do
Instagram) e conferir que a aba Link mostra 9 itens, 8 no botão `instagram.com` e 1 em
`i384100.net`.

**Acceptance Scenarios**:

1. **Given** a mensagem de exemplo com 9 links, **When** abro a aba Link, **Then** vejo 9 itens,
   um por link, na ordem em que aparecem na mensagem.
2. **Given** a mesma mensagem, **When** clico em `instagram.com`, **Then** vejo só os 8 links do
   Instagram, e o botão mostra 8.
3. **Given** um item de link, **When** olho o item, **Then** vejo o endereço, o site e de qual
   mensagem ele veio.
4. **Given** a mensagem com 9 links, **When** edito a mensagem removendo 2 links, **Then** sobram
   7 itens.
5. **Given** uma mensagem com um único link e texto em volta, **When** abro o painel, **Then** vejo
   um item de link e o texto da mensagem continua visível.
6. **Given** a mesma URL repetida duas vezes na mesma mensagem, **When** abro o painel, **Then**
   aparece um item só.
7. **Given** linhas no formato do WhatsApp, **When** olho o item de cada link, **Then** ele mostra
   a data e o autor da sua linha (ex.: "05/11/2026 12:40 · Usuario"), e a aba Link ordena os
   itens por essa data, do mais recente para o mais antigo.
8. **Given** uma linha com link sem o prefixo `[data, hora] autor:`, **When** olho o item, **Then**
   ele usa a data da mensagem do Telegram e não mostra autor.
9. **Given** a mensagem de exemplo, **When** abro a aba "Todas", **Then** vejo uma nota só, com os
   9 links em cartões dentro dela.

---

### User Story 2 - Cartão com prévia da página (Priority: P1)

Cada link aparece num cartão com o título da página, uma descrição curta e uma miniatura,
como num aplicativo de mensagens. A prévia é buscada uma vez e fica guardada no meu
computador. Posso desligar a busca na configuração.

**Why this priority**: sem a prévia, uma lista de links do Instagram é uma fileira de códigos
que não dizem nada; a prévia é o que torna o caderno legível.

**Independent Test**: com a busca ligada e páginas de teste locais que têm título, descrição e
imagem, capturar links para elas e conferir que os cartões mostram os três; desligar a busca
e conferir que nenhuma página é acessada.

**Acceptance Scenarios**:

1. **Given** a busca de prévia ligada, **When** um link novo é guardado, **Then** em até 1 minuto
   o cartão mostra título, descrição curta e miniatura da página.
2. **Given** uma prévia já buscada, **When** recarrego o painel ou reinicio o sistema, **Then** a
   prévia aparece sem acessar a página de novo.
3. **Given** uma página que não responde, exige login ou não tem informação de prévia, **When** a
   busca termina, **Then** o cartão mostra o endereço e o site, sem título nem imagem, e o painel
   não fica travado.
4. **Given** a busca de prévia desligada, **When** links são guardados ou o painel é aberto,
   **Then** nenhuma requisição sai para os sites, e os cartões mostram endereço e site.
5. **Given** links guardados antes desta funcionalidade, **When** a busca está ligada, **Then** as
   prévias deles também são buscadas, aos poucos, sem atrapalhar o uso.
6. **Given** a mesma URL em duas notas diferentes, **When** as prévias são buscadas, **Then** a
   página é acessada uma vez só.

---

### User Story 3 - Abrir o link e a mensagem original (Priority: P1)

No cartão, clico no título ou na miniatura e o link abre direto no site, numa aba nova.
Ao lado, continua existindo o link para a mensagem original no Telegram.

**Why this priority**: o painel serve para chegar ao conteúdo; abrir o link é a ação principal
do cartão.

**Independent Test**: num cartão qualquer, ativar o link principal e o link do Telegram, pelo
mouse e pelo teclado, e conferir os destinos.

**Acceptance Scenarios**:

1. **Given** um cartão, **When** clico no título ou na miniatura, **Then** o endereço do link abre
   numa aba nova.
2. **Given** um cartão, **When** clico em "abrir no Telegram", **Then** a mensagem de onde veio o
   link abre no Telegram.
3. **Given** um cartão sem prévia, **When** olho o cartão, **Then** o próprio endereço é o link
   clicável.
4. **Given** só o teclado, **When** navego pelos cartões, **Then** alcanço e ativo os dois links de
   cada cartão.

---

### User Story 4 - Baixar os arquivos (Priority: P2)

Fotos, áudios e documentos que foram baixados para o computador têm um botão "Baixar" que
salva o arquivo com o nome original.

**Why this priority**: hoje a foto abre em tamanho grande e o áudio toca, mas não há uma ação
clara para salvar o arquivo em outro lugar.

**Independent Test**: com notas de foto, áudio e documento com arquivo, clicar em "Baixar" em
cada uma e conferir que o navegador salva o arquivo com o nome certo.

**Acceptance Scenarios**:

1. **Given** uma foto com arquivo, **When** clico em "Baixar", **Then** o navegador salva o arquivo
   em vez de abrir a imagem.
2. **Given** um documento com nome original, **When** clico em "Baixar", **Then** o arquivo salvo
   tem esse nome.
3. **Given** um áudio, **When** olho a nota, **Then** o player continua na página e o botão
   "Baixar" fica ao lado.
4. **Given** uma nota sem arquivo (vídeo, acima de 20 MB ou não veio na exportação), **When** olho
   a nota, **Then** não há botão "Baixar", e o aviso do motivo continua como hoje.

---

### User Story 5 - Painel em cartões, legível em qualquer largura (Priority: P2)

Todas as notas viram cartões com hierarquia clara: primeiro o conteúdo (prévia, texto ou
mídia), depois o tipo, a data e as ações. O painel funciona bem numa janela estreita ou no
celular conectado ao mesmo computador, e continua utilizável só com o teclado.

**Why this priority**: melhora tudo, mas o caderno já funciona sem ela; as histórias
anteriores entregam o valor principal.

**Independent Test**: abrir o painel numa janela de 360 px de largura e numa de 1280 px,
percorrer abas, botões de site e cartões só com o teclado e conferir que nada fica cortado,
sobreposto ou inacessível.

**Acceptance Scenarios**:

1. **Given** uma janela de 360 px, **When** abro o painel, **Then** não há rolagem horizontal, e
   abas e botões de site quebram linha ou rolam sem esconder nada.
2. **Given** uma janela larga, **When** abro a aba Link, **Then** os cartões aproveitam a largura
   (mais de um por linha).
3. **Given** só o teclado, **When** uso Tab, **Then** o foco é sempre visível e segue a ordem: busca,
   abas, sites, cartões.
4. **Given** uma nota com falha, **When** olho a lista, **Then** ela continua destacada e mostra o
   erro, como na 001.
5. **Given** tema claro ou escuro do sistema, **When** abro o painel, **Then** texto e cartões têm
   contraste legível nos dois.

---

### Edge Cases

- Mensagem com 50 links: 50 itens, todos nos seus sites; a paginação continua em 50 itens.
- Link escondido em texto formatado (`text_link`): vira item como os demais.
- Linha do WhatsApp sem link (só texto): continua no texto da nota, não vira item de link.
- Linha do WhatsApp com dois links: os dois itens herdam a data e o autor da linha.
- Data impossível na linha (`[25:99, 31/02/2026]`): tratada como fora do padrão (FR-016).
- Busca por palavra na aba Link: retorna os itens das notas cujo texto contém a palavra (ou cujo
  título de prévia contém, se houver).
- Prévia com título enorme ou descrição longa: cortada com reticências no cartão.
- Miniatura muito grande ou formato estranho: o cartão mantém o tamanho; imagem que não carrega
  dá lugar ao cartão sem imagem.
- Página que redireciona (inclusive encurtadores): a prévia mostra o que a página final mostrar,
  mas o item continua no site escrito na mensagem (a regra de site da 002 não muda).
- Página que demora: a busca desiste após um tempo limite e marca a prévia como indisponível;
  nova tentativa só depois de um intervalo, nunca em loop.
- Página com conteúdo malicioso na prévia (HTML ou script no título): o painel mostra só texto,
  nunca executa nada da página.
- Busca de prévia ligada sem internet: os cartões ficam sem prévia e a busca tenta de novo mais
  tarde, sem erro na tela.
- Endereço de rede local ou do próprio computador (`localhost`, `192.168.x.x`): a prévia não é
  buscada.
- Nota de link com falha de processamento: continua aparecendo como falha (Princípio VIII).
- Arquivo apagado da pasta local: o botão "Baixar" leva a uma mensagem de arquivo não encontrado,
  sem quebrar a página.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada URL distinta de uma nota de link MUST virar um item de link próprio, na ordem
  em que aparece na mensagem; URLs repetidas na mesma mensagem viram um item só.
- **FR-002**: Na aba Link, a lista, as contagens dos botões de site e a paginação MUST contar
  itens de link (não notas). Nas demais abas e na busca fora da aba Link, a lista MUST continuar
  mostrando uma nota por mensagem, com os itens de link dela em cartões dentro da nota; as
  contagens das abas de tipo continuam contando notas, exceto a aba Link, que conta itens.
- **FR-003**: Cada item de link MUST pertencer ao site da sua URL pela regra da 002; o botão de um
  site MUST mostrar só os itens daquele site.
- **FR-004**: Edição da mensagem MUST refazer os itens de link a partir do texto novo; links
  removidos somem, links novos aparecem.
- **FR-005**: Para cada URL, o sistema MUST buscar uma única vez título, descrição curta e
  miniatura da página e guardar no computador, inclusive a imagem; a mesma URL em notas
  diferentes usa a mesma prévia.
- **FR-006**: A busca de prévias MUST poder ser desligada na configuração. Desligada, nenhuma
  requisição além do Telegram sai da máquina (Princípio I).
- **FR-007**: A busca de prévias MUST NOT atrasar a captura das mensagens nem o carregamento do
  painel; o cartão aparece sem prévia e é completado quando ela chega.
- **FR-008**: Falha ao buscar a prévia (página fora do ar, login exigido, sem metadados, tempo
  esgotado) MUST deixar o cartão sem prévia, registrar o motivo e permitir nova tentativa depois
  de um intervalo; MUST NOT impedir a gravação da nota.
- **FR-009**: Endereços de rede local, do próprio computador ou com esquema diferente de http/https
  MUST NOT ter prévia buscada.
- **FR-010**: O painel MUST mostrar textos da prévia só como texto e MUST NOT executar nem
  carregar nada da página no navegador além da miniatura já guardada no computador.
- **FR-011**: O cartão MUST abrir o endereço do link numa aba nova pelo título, pela miniatura ou,
  sem prévia, pelo próprio endereço; e MUST manter o link "abrir no Telegram" para a mensagem
  original.
- **FR-012**: Fotos, áudios e documentos com arquivo local MUST ter um botão "Baixar" que salva o
  arquivo com o nome original (ou o nome guardado, se não houver original); notas sem arquivo
  MUST NOT ter o botão.
- **FR-013**: Todas as notas MUST aparecer como cartões, com o conteúdo primeiro e depois tipo,
  data e ações; notas com falha continuam destacadas com o erro.
- **FR-014**: O painel MUST funcionar sem rolagem horizontal de 360 px a 1920 px de largura e
  MUST ser utilizável só pelo teclado, com foco visível.
- **FR-016**: Uma linha que começa com `[DD/MM/AAAA, HH:MM]` ou `[HH:MM, DD/MM/AAAA]` seguido de
  `autor:` MUST ter data e autor lidos e associados aos links daquela linha; linha fora do padrão,
  ou com data inválida, MUST usar a data da mensagem e nenhum autor. A data lida está no fuso do
  computador.
- **FR-017**: Na aba Link, os itens MUST ser ordenados pela sua data (a da linha, se houver, senão a
  da mensagem), da mais recente para a mais antiga; empate pela posição na mensagem.
- **FR-015**: Links guardados antes desta funcionalidade MUST virar itens de link e, com a busca
  ligada, ter as prévias buscadas aos poucos, sem intervenção do dono.

### Key Entities

- **Item de link**: uma URL distinta dentro de uma nota de link. Atributos: nota de origem, posição
  na mensagem, endereço, site (regra da 002), data (da linha do WhatsApp ou da mensagem) e autor
  (só quando veio da linha).
- **Prévia**: informações de uma página, compartilhadas por todos os itens com a mesma URL.
  Atributos: título, descrição curta, miniatura guardada no computador, situação (pendente, ok,
  indisponível), motivo da falha, data da busca e da próxima tentativa.
- **Nota** (001): continua sendo uma por mensagem; passa a ter zero ou mais itens de link.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A mensagem de exemplo com 9 links resulta em exatamente 9 itens, 8 em `instagram.com`
  e 1 em `i384100.net`.
- **SC-002**: Com a busca ligada e o site respondendo, 95% dos links novos têm prévia em até 1
  minuto após a captura.
- **SC-003**: Com a busca desligada, 0 requisições saem para sites além do Telegram durante a
  captura e o uso do painel.
- **SC-004**: Cada URL é acessada no máximo uma vez para obter a prévia, fora as novas tentativas
  depois de falha.
- **SC-005**: O painel com 10.000 notas e 5.000 itens de link carrega e troca de aba em até 1
  segundo, com ou sem prévias pendentes.
- **SC-006**: Em 360 px e em 1280 px, todas as ações (abas, sites, abrir link, abrir no Telegram,
  baixar) são alcançáveis pelo teclado, e não há rolagem horizontal.
- **SC-007**: O dono encontra e abre um link específico do Instagram, a partir da página inicial,
  em menos de 15 segundos.

## Assumptions

- A nota continua sendo uma por mensagem (FR-009 da 001); os itens de link ficam dentro dela.
  Só a forma de listar muda.
- A busca de prévia vem **ligada** por padrão, porque o dono pediu prévias; ela pode ser desligada
  numa linha da configuração.
- A prévia usa só as informações que a própria página declara para compartilhamento (título,
  descrição, imagem). O conteúdo da página não é lido nem guardado além disso.
- Instagram e outros sites podem negar a prévia sem login. Nesses casos o cartão fica sem prévia,
  o que é esperado e não é erro.
- Encurtadores: a prévia segue o redirecionamento como qualquer navegador faria, mas o site do
  item não muda (a descoberta do destino para agrupar continua fora do escopo).
- A prévia não é atualizada sozinha depois de obtida; uma prévia velha não é problema para um
  caderno pessoal.
- As miniaturas ficam na mesma pasta local de mídia, ignorada pelo Git, e seguem o mesmo limite
  de tamanho da 001.
- Parâmetros de rastreio nas URLs (`?srtk=…`, `?xtok=…`) são mantidos como vieram; duas URLs que
  diferem só neles contam como dois itens.
- Vídeos continuam sem download, e conteúdo do Instagram não é reproduzido dentro do painel.
- O celular acessa o painel só se o dono configurar isso por conta própria; o painel continua
  escutando apenas no próprio computador (Princípio IV). "Tela estreita" é validada com a janela
  do navegador estreita.
- Os testes usam páginas de prévia locais e inventadas; nenhum teste acessa a internet.
