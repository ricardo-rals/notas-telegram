# Feature Specification: Categorias por Tipo e Sites dos Links

**Feature Branch**: `002-categorias-sites`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Organizar as notas por categoria e subcategoria. O painel ganha uma aba para cada tipo (link, foto, áudio, documento etc.). Dentro de Links, um botão para cada site, agrupando pelo domínio (instagram.com, facebook.com, youtube.com...). Subdomínios como www e m contam como o mesmo site. As notas já guardadas também são classificadas."

## Clarifications

### Session 2026-11-06

- Q: Só `www.`/`m.` são removidos ou todo subdomínio vira o domínio principal? → A: Todo
  subdomínio vira o domínio registrável, respeitando sufixos como `.com.br` (FR-005).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegar por abas de tipo (Priority: P1)

Abro o painel e, em vez de escolher o tipo numa lista, vejo uma aba para cada tipo de nota
(Todas, Texto, Link, Foto, Áudio, Vídeo, Documento, Localização, Contato, Outro, Falhas).
Clico numa aba e vejo só as notas daquele tipo. Cada aba mostra quantas notas tem.

**Why this priority**: é a categoria de primeiro nível; organiza todo o caderno e já entrega
valor sem a parte de sites.

**Independent Test**: com notas inventadas de vários tipos, abrir o painel, clicar em cada aba
e conferir que só aparecem notas daquele tipo e que a contagem da aba bate com a lista.

**Acceptance Scenarios**:

1. **Given** notas de vários tipos, **When** abro o painel, **Then** a aba "Todas" está
   selecionada e mostra todas as notas, como hoje.
2. **Given** 7 fotos e 3 áudios, **When** olho as abas, **Then** "Foto" mostra 7 e "Áudio" mostra 3.
3. **Given** a aba "Foto" selecionada, **When** busco uma palavra, **Then** aparecem só fotos que
   contêm a palavra.
4. **Given** a aba "Foto" selecionada, **When** recarrego a página ou abro de novo o endereço
   copiado, **Then** a mesma aba continua selecionada.
5. **Given** um tipo sem nenhuma nota, **When** olho as abas, **Then** a aba aparece com 0 e, ao
   abrir, a página informa que nada foi encontrado.

---

### User Story 2 - Filtrar links por site (Priority: P1)

Na aba Links, vejo um botão para cada site que aparece nos meus links (instagram.com,
youtube.com, facebook.com...), com a quantidade de notas de cada um. Clico em "youtube.com"
e vejo só os links do YouTube. Endereços com `www.` ou `m.` na frente contam como o mesmo site.

**Why this priority**: é o pedido central (subcategoria); links são o tipo mais difícil de
achar sem agrupamento.

**Independent Test**: com links inventados para `https://www.youtube.com/...`,
`https://m.youtube.com/...` e `https://instagram.com/...`, abrir a aba Links e conferir que
existem os botões "youtube.com (2)" e "instagram.com (1)" e que cada um filtra corretamente.

**Acceptance Scenarios**:

1. **Given** links para `www.youtube.com`, `m.youtube.com` e `youtube.com`, **When** abro a aba
   Links, **Then** existe um único botão "youtube.com" com 3 notas.
2. **Given** links de vários sites, **When** abro a aba Links, **Then** os botões aparecem do site
   com mais notas para o com menos; empate em ordem alfabética.
3. **Given** o botão "instagram.com" selecionado, **When** busco uma palavra, **Then** aparecem só
   links do Instagram que contêm a palavra.
4. **Given** o botão "instagram.com" selecionado, **When** clico de novo nele ou em "Todos os
   sites", **Then** volto a ver todos os links.
5. **Given** uma nota com links para youtube.com e instagram.com, **When** abro qualquer um dos
   dois botões, **Then** a nota aparece nos dois e conta uma vez em cada.
6. **Given** um link cujo site não pode ser identificado, **When** abro a aba Links, **Then** ele
   aparece sob o botão "Sem site identificado" e nunca some da aba.
7. **Given** um site selecionado, **When** recarrego a página, **Then** a mesma aba e o mesmo site
   continuam selecionados.

---

### User Story 3 - Notas antigas também classificadas (Priority: P1)

As notas que já estavam guardadas antes desta funcionalidade aparecem nos botões de site
da mesma forma que as novas, sem eu precisar fazer nada além de atualizar o sistema.

**Why this priority**: o caderno já tem histórico; sem isso os botões de site mostrariam só
uma parte dos links e enganariam.

**Independent Test**: com um banco contendo links inventados gravados antes da atualização,
atualizar o sistema e conferir que todos os links antigos aparecem sob o botão do site certo.

**Acceptance Scenarios**:

1. **Given** 200 links guardados antes da atualização, **When** atualizo o sistema e abro a aba
   Links, **Then** os 200 aparecem distribuídos nos botões de site, nenhum fica de fora.
2. **Given** a atualização já aplicada, **When** ela roda de novo, **Then** nada muda nem duplica.
3. **Given** um link antigo cujo site não pode ser identificado com os dados guardados, **When**
   a classificação roda, **Then** ele vai para "Sem site identificado" e as demais notas seguem.

---

### User Story 4 - Novas notas, edições e importações entram no site certo (Priority: P2)

Quando mando um link novo, edito uma mensagem ou importo uma exportação, a nota já aparece
no botão do site correspondente.

**Why this priority**: mantém a organização correta no uso diário; depende das histórias
anteriores para ser visível.

**Independent Test**: enviar um link novo, editar outro trocando o site e importar uma
exportação inventada com links; conferir os botões de site depois de cada passo.

**Acceptance Scenarios**:

1. **Given** o sistema rodando, **When** envio "https://m.facebook.com/evento", **Then** a nota
   aparece sob "facebook.com".
2. **Given** um link do instagram.com, **When** edito a mensagem para um link do youtube.com,
   **Then** a nota sai de "instagram.com" e passa para "youtube.com".
3. **Given** uma nota de texto, **When** edito incluindo uma URL, **Then** ela passa para a aba
   Links, no botão do site da URL.
4. **Given** uma exportação com links, **When** importo, **Then** as notas criadas aparecem nos
   botões dos seus sites.

---

### Edge Cases

- Maiúsculas no endereço (`YouTube.COM`): mesmo site que `youtube.com`.
- Vários subdomínios (`www.m.exemplo.com`, `a.b.exemplo.com.br`) ou porta (`exemplo.com:8080`):
  contam como o domínio principal (`exemplo.com`, `exemplo.com.br`).
- Sites hospedados em domínio compartilhado (`fulano.github.io`, `blog.blogspot.com`): cada
  conta é um site próprio, conforme a lista de sufixos (`fulano.github.io`).
- Endereço que é só um sufixo (`http://com.br`): vai para "Sem site identificado".
- Endereço com IP ou nome sem ponto (`http://192.168.0.1`, `http://localhost`): o site é o
  próprio endereço, sem alteração.
- Domínio com acento ou outro alfabeto: aparece na forma legível, e as duas formas de escrita
  do mesmo domínio contam como um só site.
- URL malformada, ou link escondido em texto formatado cujo endereço não ficou guardado:
  vai para "Sem site identificado".
- Encurtadores e domínios alternativos (`youtu.be`, `bit.ly`, `instagr.am`): contam como o site
  que aparece no endereço; não há resolução do destino.
- Mesma nota com várias URLs do mesmo site: aparece uma vez naquele site.
- Foto, vídeo ou documento com URL na legenda: continua no seu tipo; não entra na aba Links
  nem nos botões de site.
- Muitos sites diferentes: todos os botões aparecem; a ordem por quantidade deixa os mais
  usados primeiro.
- Notas com falha: continuam na aba Falhas; se forem links com site identificável, também
  contam no botão do site.
- Site inexistente digitado à mão no endereço da página: a página informa que nada foi
  encontrado, sem erro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O painel MUST mostrar uma aba para cada tipo de nota (texto, link, foto, áudio,
  vídeo, documento, localização, contato, outro), mais "Todas" e "Falhas", substituindo a lista
  de seleção de tipo.
- **FR-002**: Cada aba MUST mostrar a quantidade de notas daquela categoria no caderno inteiro;
  as contagens não dependem da busca ativa.
- **FR-003**: Selecionar uma aba MUST listar só as notas daquele tipo, mantendo ordenação,
  paginação, busca e atualização automática já existentes.
- **FR-004**: Na aba Links, o painel MUST mostrar um botão para cada site presente nos links,
  com a quantidade de notas, ordenados por quantidade decrescente e, em empate, por nome.
- **FR-005**: O site de uma URL MUST ser o seu domínio registrável (domínio principal), em
  minúsculas e sem porta: qualquer subdomínio é descartado (`www.youtube.com`, `m.youtube.com`
  e `music.youtube.com` → `youtube.com`; `pt.wikipedia.org` → `wikipedia.org`). Sufixos de mais
  de um nível contam como sufixo (`folha.uol.com.br` → `uol.com.br`; `exemplo.co.uk` →
  `exemplo.co.uk`). A lista de sufixos MUST ficar no próprio computador (FR-010).
- **FR-006**: Uma nota de link com URLs de sites diferentes MUST aparecer em cada um desses
  sites; com várias URLs do mesmo site, MUST contar uma vez nele.
- **FR-007**: Uma nota de link sem site identificável MUST aparecer sob "Sem site identificado";
  nenhuma nota de link pode ficar fora de todos os botões.
- **FR-008**: Selecionar um site MUST listar só os links daquele site, combinável com a busca;
  "Todos os sites" (ou clicar de novo no site ativo) MUST remover esse filtro.
- **FR-009**: Aba e site selecionados MUST ficar no endereço da página, de modo que recarregar,
  voltar no navegador ou abrir o endereço salvo restaure a mesma seleção.
- **FR-010**: A identificação do site MUST ser feita por regra determinística, sem acesso à rede
  (Princípios I e II).
- **FR-011**: As notas existentes antes desta funcionalidade MUST ser classificadas por site
  durante a atualização do sistema, sem intervenção do dono; repetir a atualização MUST NOT
  alterar nem duplicar nada.
- **FR-012**: Notas novas, edições e importações MUST ter o site calculado com a mesma regra, de
  modo que uma nota apareça sempre nos sites das URLs do seu texto atual.
- **FR-013**: A classificação por site MUST NOT apagar nem alterar o texto, o tipo ou qualquer
  outro dado já guardado da nota.
- **FR-014**: Uma falha ao identificar o site de uma nota MUST NOT impedir a captura dela nem a
  classificação das outras; a nota vai para "Sem site identificado" (Princípio VIII).
- **FR-015**: Valores de aba ou site inválidos no endereço da página MUST resultar em lista vazia
  ou aviso, nunca em erro inesperado.

### Key Entities

- **Categoria**: o tipo da nota (já existente na 001). Cada nota tem exatamente uma.
- **Site**: subcategoria das notas de link; o domínio normalizado de uma URL (ex.: `youtube.com`).
  Uma nota de link pertence a um ou mais sites, ou a "Sem site identificado".
- **Nota** (da 001): passa a se relacionar com os sites das URLs do seu texto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das notas de link (antigas e novas) aparecem em ao menos um botão de site.
- **SC-002**: 100% dos casos de teste de normalização (maiúsculas, `www.`, `m.`, outros
  subdomínios, sufixos como `.com.br`, domínio compartilhado, porta, IP, domínio com acento,
  URL malformada) resultam no site esperado.
- **SC-003**: Com 10.000 notas, trocar de aba ou de site mostra os resultados em até 1 segundo.
- **SC-004**: A classificação das notas existentes, com 10.000 notas, termina em menos de 1 minuto
  e não altera nenhum outro dado delas.
- **SC-005**: O dono chega a todos os links de um site específico em no máximo 2 cliques a
  partir da página inicial.
- **SC-006**: A soma das contagens das abas de tipo é igual ao total da aba "Todas".

## Assumptions

- Categoria = tipo da nota, já definido pela 001; não há categorias novas nem por assunto.
- Só a aba Links tem subcategorias; os outros tipos não têm botões internos nesta fatia.
- Só notas do tipo link entram nos botões de site; URLs em legendas de mídia não contam.
- O site é tirado das URLs que estão no texto guardado da nota; não há busca de título,
  miniatura nem do destino de encurtadores.
- A lista de sufixos é uma cópia local da lista pública de sufixos de domínio, atualizada só
  quando o sistema é atualizado; nunca é baixada em tempo de execução (Princípio I).
- Não há lista de apelidos de domínio (`youtu.be` não vira `youtube.com`) nesta fatia.
- A aba "Falhas" continua existindo como hoje, ao lado das abas de tipo.
- As contagens das abas e dos botões refletem o caderno inteiro, não a busca nem a página atual.
- A classificação das notas antigas acontece junto com a atualização do banco que o sistema
  já faz ao ser atualizado; não é preciso um comando separado.
- O painel continua acessível só pelo próprio computador e utilizável pelo teclado.
