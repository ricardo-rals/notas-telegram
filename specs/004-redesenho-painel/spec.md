# Feature Specification: Redesenho do Painel

**Feature Branch**: `004-redesenho-painel`

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "Redesenho do painel, escuro primeiro: barra lateral com tipos e contagens, grade de cartões em largura total, cartão próprio para cada tipo, aviso de notas novas no lugar da atualização automática, atalho / para buscar, foto ampliada na página, estados vazio e de carregamento desenhados, e importação que encontra as exportações em Downloads sozinha."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegar pela barra lateral (Priority: P1)

Abro o painel e, à esquerda, vejo as categorias que eu realmente uso, cada uma com a sua
quantidade. A área principal ocupa o resto da tela. Clico numa categoria e a lista muda sem
recarregar a página inteira.

**Why this priority**: hoje são dez abas iguais numa linha que quebra. A barra lateral é a
estrutura em que todas as outras melhorias se apoiam.

**Independent Test**: com notas de 4 tipos guardadas, abrir o painel e conferir que a barra
mostra "Todas" e só esses 4 tipos, com as contagens certas, e que clicar em um deles filtra a lista.

**Acceptance Scenarios**:

1. **Given** notas de texto, link, foto e documento, **When** abro o painel, **Then** a barra
   lateral mostra Todas, Texto, Link, Foto e Documento, cada um com a sua contagem, e não mostra
   tipos sem nenhuma nota.
2. **Given** a barra lateral, **When** clico em "Foto", **Then** só fotos aparecem, a categoria
   fica destacada e o endereço da página muda para `?tipo=foto`.
3. **Given** a categoria Link selecionada, **When** a lista carrega, **Then** os sites aparecem
   como botões acima da lista, como na 002.
4. **Given** 2 notas com falha, **When** abro o painel, **Then** um aviso "2 falhas" aparece no
   topo e leva à lista de falhas; sem falhas, o aviso não aparece.
5. **Given** uma janela estreita (360 px), **When** abro o painel, **Then** as categorias viram
   uma faixa rolável horizontal no topo, sem rolagem horizontal da página.

---

### User Story 2 - Um cartão próprio para cada tipo (Priority: P1)

Cada nota aparece num cartão desenhado para o seu tipo: foto com a imagem em destaque, áudio
com player, documento com o tipo de arquivo e o tamanho, link com a prévia, localização com as
coordenadas e um link para o mapa, contato com nome e telefone, e texto com a tipografia em
destaque. Os cartões se organizam numa grade que ocupa a largura da tela.

**Why this priority**: é o que o dono olha o tempo todo; hoje todos os cartões têm o mesmo formato.

**Independent Test**: com uma nota de cada tipo, conferir no painel o formato de cada cartão e
que a grade usa a largura disponível.

**Acceptance Scenarios**:

1. **Given** uma foto com legenda, **When** vejo o cartão, **Then** a imagem ocupa a largura do
   cartão, recortada sem distorção, com a legenda abaixo.
2. **Given** um documento `boleto.pdf` de 230 KB, **When** vejo o cartão, **Then** ele mostra o
   selo "PDF", o nome do arquivo, "230 KB" e o botão Baixar.
3. **Given** uma localização, **When** vejo o cartão, **Then** ele mostra as coordenadas e um
   link "Abrir no mapa" que abre numa aba nova; o painel não carrega nenhum mapa.
4. **Given** uma tela de 1920 px, **When** abro o painel, **Then** os cartões se distribuem em
   várias colunas e não há faixas vazias largas dos lados.
5. **Given** uma nota com falha, **When** vejo o cartão, **Then** ele tem destaque de falha e
   mostra o erro.

---

### User Story 3 - Aviso de notas novas, sem interromper (Priority: P1)

Com o painel aberto, mando algo no grupo. Em vez de a lista inteira se recarregar sozinha, surge
um aviso "1 nota nova · mostrar". A lista só muda quando eu clico. Um áudio que estou ouvindo não
para, e a página não pula.

**Why this priority**: é um bug de uso. Hoje a lista é substituída a cada 10 s, o que
interrompe um áudio no meio e recarrega as imagens.

**Independent Test**: com o painel aberto na primeira página, gravar uma nota nova e conferir
que o aviso aparece em até 10 s, que a lista não mudou e que, ao clicar, a nota nova aparece.

**Acceptance Scenarios**:

1. **Given** o painel aberto, **When** uma nota nova é gravada, **Then** em até 10 segundos
   aparece "1 nota nova · mostrar", e os cartões já exibidos não mudam.
2. **Given** o aviso visível, **When** clico em "mostrar", **Then** a lista volta ao topo com
   as notas novas e o aviso some.
3. **Given** um áudio tocando, **When** chegam notas novas, **Then** o áudio continua tocando.
4. **Given** uma busca ou um filtro ativo, **When** chegam notas novas que não atendem a eles,
   **Then** nenhum aviso aparece.

---

### User Story 4 - Buscar pelo teclado (Priority: P2)

Aperto `/` em qualquer lugar do painel e o cursor vai para a busca. `Esc` limpa a busca e tira
o foco dela.

**Why this priority**: acelera a ação mais frequente, sem custo para quem usa o mouse.

**Independent Test**: abrir o painel, apertar `/`, digitar uma palavra e ver o resultado;
apertar `Esc` e ver a lista completa de novo.

**Acceptance Scenarios**:

1. **Given** o painel aberto e o foco fora de qualquer campo, **When** aperto `/` ou `Ctrl+K`,
   **Then** o foco vai para a busca, sem digitar a barra.
2. **Given** o foco na busca com texto, **When** aperto `Esc`, **Then** a busca é limpa, a lista
   completa volta e o foco sai do campo.
3. **Given** o foco num campo de texto, **When** digito `/`, **Then** a barra é digitada
   normalmente.
4. **Given** a busca vazia, **Then** o campo indica o atalho (ex.: "Buscar  /").

---

### User Story 5 - Foto ampliada na própria página (Priority: P2)

Clico numa foto e ela abre ampliada por cima do painel, sem sair da página. Fecho com `Esc`, com
o botão fechar ou clicando fora da foto.

**Why this priority**: hoje a foto abre numa aba nova e eu perco o lugar na lista.

**Independent Test**: clicar numa foto, ver a versão ampliada, fechar com `Esc` e confirmar que
a lista está na mesma posição.

**Acceptance Scenarios**:

1. **Given** uma foto na lista, **When** clico nela, **Then** a foto aparece ampliada sobre um
   fundo escurecido, com a legenda e um botão fechar.
2. **Given** a foto ampliada, **When** aperto `Esc`, clico em fechar ou clico fora da foto,
   **Then** ela fecha e o foco volta para a foto clicada.
3. **Given** o navegador sem scripts, **When** clico numa foto, **Then** ela abre em tamanho
   original, como hoje.

---

### User Story 6 - Estados vazio e de carregamento desenhados (Priority: P2)

Quando não há nada para mostrar, o painel explica o porquê e o que fazer. Enquanto uma busca ou
um filtro carrega, a área da lista mostra cartões fantasmas com o formato do conteúdo, em vez de
ficar parada.

**Why this priority**: o primeiro uso e as buscas sem resultado hoje mostram só "Nenhuma nota
encontrada".

**Independent Test**: abrir o painel com o caderno vazio, buscar uma palavra inexistente e
selecionar uma categoria vazia, conferindo a mensagem de cada caso.

**Acceptance Scenarios**:

1. **Given** o caderno vazio, **When** abro o painel, **Then** vejo "Seu caderno está vazio",
   com a instrução de mandar algo no grupo e um link para importar uma exportação.
2. **Given** uma busca sem resultado, **When** a lista carrega, **Then** vejo "Nada encontrado
   para “xyz”" e uma ação para limpar a busca.
3. **Given** uma página além da última, **When** a abro, **Then** vejo que não há mais notas e
   um link para a primeira página.
4. **Given** uma busca em andamento, **When** a resposta demora, **Then** a lista mostra cartões
   fantasmas até o resultado chegar.

---

### User Story 7 - Importar com um clique (Priority: P3)

Na página de importação, o painel já lista as exportações do Telegram Desktop que encontrou nas
minhas pastas de downloads, da mais recente para a mais antiga, com a data e o nome do chat. Clico
em "Importar" ao lado da que eu quero. Digitar o caminho continua possível para pastas em outros lugares.

**Why this priority**: tira a etapa mais chata (copiar o caminho de uma pasta), mas a importação
é rara.

**Independent Test**: com duas pastas de exportação inventadas numa pasta de downloads de teste,
abrir a página de importação, conferir a lista e importar a mais recente com um clique.

**Acceptance Scenarios**:

1. **Given** duas exportações em `Downloads\Telegram Desktop`, **When** abro a página de
   importação, **Then** vejo as duas, a mais recente primeiro, com o nome do chat, a data da
   pasta e o número de mensagens.
2. **Given** uma exportação de outro chat, **When** ela é listada, **Then** aparece marcada como
   "outro chat", sem o botão Importar.
3. **Given** a lista, **When** clico em "Importar" numa exportação, **Then** a importação começa
   e o progresso aparece como hoje.
4. **Given** nenhuma exportação encontrada, **When** abro a página, **Then** vejo como exportar
   pelo Telegram Desktop e o campo para digitar o caminho.

### Edge Cases

- Tipo com contagem que vai a zero (ex.: a única nota de vídeo foi editada e virou texto): o tipo
  some da barra lateral; se ele estava selecionado, a lista mostra o estado vazio da categoria.
- Endereço com tipo válido mas sem notas (`?tipo=video`): a categoria aparece destacada na barra
  lateral, mesmo sem notas, para o dono saber onde está.
- Foto cujo arquivo foi apagado da pasta: o cartão mostra um espaço neutro com "imagem
  indisponível", sem ícone de imagem quebrada.
- Muitas notas novas de uma vez (importação rodando com o painel aberto): o aviso mostra o total
  ("128 notas novas · mostrar"), sem um aviso por nota.
- Pasta de downloads inexistente, sem permissão ou com milhares de subpastas: a página de
  importação mostra o que conseguir ler das pastas `ChatExport*` em até 2 segundos, e nunca dá erro.
- `result.json` corrompido numa das pastas encontradas: essa pasta aparece como "exportação
  ilegível", sem botão Importar; as demais seguem normais.
- O atalho `/` com a foto ampliada aberta: não faz nada até a foto fechar.
- Sistema com tema claro: o painel segue o tema do sistema; o escuro é o padrão quando o sistema
  não indica preferência.
- Usuário que prefere menos movimento (configuração do sistema): sem animações de transição.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O painel MUST ter uma barra lateral com "Todas" e uma entrada para cada tipo que
  tenha ao menos uma nota, cada uma com a sua contagem (contagens da 002/003); tipos sem notas
  MUST NOT aparecer, exceto o tipo selecionado no endereço.
- **FR-002**: Falhas MUST deixar de ser uma aba e passar a ser um aviso no topo com a quantidade,
  visível só quando houver falha e levando à lista de falhas (`?tipo=falha` continua válido).
- **FR-003**: Selecionar uma categoria ou um site MUST atualizar só a lista e o destaque, mantendo
  o endereço da página em sincronia (FR-009 da 002); voltar no navegador MUST restaurar o filtro anterior.
- **FR-004**: Em largura de até 720 px, a barra lateral MUST virar uma faixa horizontal rolável
  acima da lista, sem rolagem horizontal da página de 360 px a 1920 px.
- **FR-005**: As notas MUST aparecer numa grade que ocupa a largura disponível, com colunas de no
  mínimo 260 px; a aba Link mantém os cartões de link da 003.
- **FR-006**: Cada tipo MUST ter um cartão próprio: foto com imagem em destaque e recorte sem
  distorção; áudio com player; documento com selo da extensão (em maiúsculas), nome e tamanho
  legível (KB/MB); localização com coordenadas e link externo para o mapa; contato com nome e
  telefone; texto com fonte maior quando curto (até 140 caracteres); vídeo com a legenda e o
  aviso de que não é baixado.
- **FR-007**: Data, tipo, "abrir no Telegram" e o botão Baixar (quando houver) MUST continuar em
  todos os cartões, nessa ordem depois do conteúdo (FR-013 da 003).
- **FR-008**: A primeira página sem busca nem filtro MUST verificar a cada 10 segundos se há
  notas mais novas que a mais recente exibida e, havendo, mostrar o aviso "N nota(s) nova(s) ·
  mostrar" sem alterar os cartões exibidos. Isso substitui a atualização automática da lista
  (FR-010 da 001), mantendo o SC-004 da 001: a nota nova fica visível no painel em até 10 s.
- **FR-009**: Clicar em "mostrar" MUST recarregar a lista no topo e esconder o aviso.
- **FR-010**: `/` e `Ctrl+K` MUST focar a busca quando o foco não estiver num campo de texto;
  `Esc` na busca MUST limpá-la, atualizar a lista e tirar o foco.
- **FR-011**: Clicar numa foto MUST abri-la ampliada sobre o painel, com legenda e botão fechar,
  fechando por `Esc`, botão ou clique fora e devolvendo o foco à foto. Sem scripts, o clique MUST
  abrir o arquivo original.
- **FR-012**: O painel MUST ter mensagens próprias para: caderno vazio (com instrução e link para
  importar), busca sem resultado (com o termo e ação de limpar), categoria sem notas e página
  além da última (com link para a primeira).
- **FR-013**: Durante uma busca ou troca de filtro que leve mais de 150 ms, a lista MUST mostrar
  cartões fantasmas no lugar do conteúdo.
- **FR-014**: A página de importação MUST listar as pastas de exportação do Telegram Desktop
  (com `result.json`) encontradas em `Downloads` e `Downloads\Telegram Desktop` do usuário, da
  mais recente para a mais antiga, com nome do chat, data da pasta e número de mensagens, e um
  botão Importar para as do grupo configurado.
- **FR-015**: Exportações de outro chat MUST aparecer marcadas "outro chat" e exportações com
  `result.json` ilegível MUST aparecer marcadas "exportação ilegível", ambas sem botão Importar.
- **FR-016**: A busca de exportações MUST NOT abrir pastas fora das duas pastas de downloads,
  MUST ler só o necessário para identificar o chat e a quantidade de mensagens, e MUST terminar em
  até 2 segundos, mostrando o que tiver lido.
- **FR-017**: O campo para digitar o caminho MUST continuar disponível, com o comportamento da 001.
- **FR-018**: O visual MUST ser escuro por padrão e seguir o tema claro quando o sistema pedir,
  com contraste de texto de no mínimo 4,5:1 nos dois temas, e MUST NOT carregar fontes, scripts
  ou estilos de fora do computador (Princípio I; CSP da 003).
- **FR-019**: Com a preferência do sistema por menos movimento, o painel MUST NOT animar transições.
- **FR-020**: Toda ação MUST continuar alcançável pelo teclado, com foco visível, e as
  categorias, os sites e o aviso de notas novas MUST ter nomes acessíveis.

### Key Entities

Nenhuma entidade nova é guardada. Duas visões novas, calculadas na hora:

- **Exportação encontrada**: pasta, nome do chat, data da pasta, número de mensagens e situação
  (importável, outro chat, ilegível).
- **Aviso de notas novas**: quantidade de notas mais recentes que a mais nova exibida.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma nota nova gera o aviso no painel em até 10 segundos, e 0 cartões já exibidos
  são recarregados por causa dela.
- **SC-002**: Um áudio tocando nunca é interrompido pela chegada de notas novas.
- **SC-003**: De 360 px a 1920 px, não há rolagem horizontal; a 1920 px a grade mostra pelo menos
  5 colunas de cartões.
- **SC-004**: O dono chega a qualquer categoria em 1 clique e começa uma busca em 1 tecla.
- **SC-005**: Com 10.000 notas, trocar de categoria ou buscar mostra o resultado em até 1 segundo
  (SC-005 da 001 e da 003 mantidos).
- **SC-006**: Importar a exportação mais recente, a partir da página inicial, leva no máximo 2
  cliques quando ela está numa das pastas de downloads.
- **SC-007**: Todo texto tem contraste de pelo menos 4,5:1 contra o fundo, nos temas escuro e claro.
- **SC-008**: O painel não faz nenhuma requisição para fora do computador ao carregar (fontes,
  scripts e estilos são locais).

## Assumptions

- O redesenho muda só o painel; captura, classificação, importação e prévias funcionam como nas
  fatias 001 a 003.
- "Downloads" é a pasta de downloads do usuário do Windows (`%USERPROFILE%\Downloads`), onde o
  Telegram Desktop salva exportações por padrão, em `Telegram Desktop\ChatExport_AAAA-MM-DD`.
- A data mostrada de cada exportação é a data de modificação da pasta.
- O link "Abrir no mapa" é só um endereço externo (OpenStreetMap); o painel nunca carrega mapas
  nem imagens de mapa (Princípio I).
- A fonte do painel é embutida no projeto; sem ela disponível, vale a fonte do sistema.
- O painel continua funcionando sem scripts para ver, filtrar e paginar; scripts só acrescentam
  os atalhos, a foto ampliada, o aviso de notas novas e os cartões fantasmas.
- Paginação continua por páginas de 50, com "mais antigas" e "mais recentes"; rolagem infinita
  fica fora do escopo.
- Agrupar por dia, favoritos, arquivar, apagar e tags ficam para fatias seguintes.
- Os testes usam notas e exportações inventadas e uma pasta de downloads falsa; nenhum teste lê a
  pasta de downloads real.
