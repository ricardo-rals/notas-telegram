# Feature Specification: Captura de Notas do Grupo do Telegram

**Feature Branch**: `001-captura-notas`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "Uso um grupo privado do Telegram como caderno e quero tudo o que mando lá guardado e listado num lugar só, no meu computador. Nesta primeira fatia, o sistema recebe as mensagens que eu envio no grupo, identifica o tipo de cada uma entre texto, link, foto, áudio, vídeo, documento, localização e contato, guarda data, tipo, texto e link para a mensagem original, e mostra as mais recentes numa página web com busca por palavra e filtro por tipo. Fotos, áudios e documentos de até 20 MB são baixados para uma pasta local. Se eu editar uma mensagem, a nota é atualizada. Mensagens de outras pessoas ou de outros grupos são ignoradas. Fora do escopo agora: página de links, classificação por assunto e lembretes."

## Clarifications

### Session 2026-11-05

- Q: Vídeos de até 20 MB devem ser baixados para a pasta local? → A: Não; a nota guarda só legenda e link.
- Q: Como recuperar mensagens perdidas quando o sistema fica desligado além da janela do Telegram? → A: Importar a exportação do Telegram Desktop nesta fatia para preencher lacunas.
- Q: Por onde disparar a importação? → A: Pelas duas vias: comando no terminal e ação no painel.
- Q: Como os arquivos baixados aparecem no painel? → A: Miniatura para fotos, player para áudios, link para documentos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guardar o que mando no grupo (Priority: P1)

Eu mando uma mensagem no meu grupo-caderno (texto, link, foto, áudio, vídeo, documento,
localização ou contato) e ela vira uma nota guardada no meu computador, com data, tipo,
texto e link para a mensagem original. Fotos, áudios e documentos de até 20 MB ficam
salvos numa pasta local.

**Why this priority**: sem captura não há caderno; é o núcleo do valor.

**Independent Test**: enviar uma mensagem de cada tipo no grupo e conferir que cada uma
gerou exatamente uma nota com tipo correto, e que os arquivos elegíveis estão na pasta local.

**Acceptance Scenarios**:

1. **Given** o sistema rodando, **When** envio "comprar pão" no grupo, **Then** surge uma
   nota do tipo texto com esse texto, a data do envio e o link para a mensagem.
2. **Given** o sistema rodando, **When** envio "olha isso https://exemplo.com", **Then** a
   nota é do tipo link e guarda o texto completo.
3. **Given** o sistema rodando, **When** envio uma foto de 3 MB com legenda, **Then** a nota é
   do tipo foto, guarda a legenda como texto e o arquivo aparece na pasta local.
4. **Given** o sistema rodando, **When** envio um documento de 25 MB, **Then** a nota é criada
   do tipo documento, sem arquivo baixado, e indica "acima de 20 MB".
5. **Given** o sistema rodando, **When** envio uma localização ou um contato, **Then** a nota
   tem o tipo correspondente e um texto legível (coordenadas; nome e telefone).

---

### User Story 2 - Ver e buscar minhas notas (Priority: P1)

Abro uma página web no meu computador e vejo as notas mais recentes primeiro. Posso buscar
por palavra e filtrar por tipo.

**Why this priority**: guardar sem conseguir encontrar não resolve o problema de "tudo num
lugar só".

**Independent Test**: com notas inventadas já guardadas, abrir a página, buscar uma palavra
e aplicar um filtro de tipo, conferindo os resultados.

**Acceptance Scenarios**:

1. **Given** 120 notas guardadas, **When** abro a página, **Then** vejo as 50 mais recentes em
   ordem decrescente de data e consigo navegar para as anteriores.
2. **Given** notas com "Reunião" e "reuniao", **When** busco "reunião", **Then** as duas aparecem
   (busca ignora maiúsculas e acentos).
3. **Given** notas de vários tipos, **When** filtro por "foto", **Then** só aparecem fotos.
4. **Given** busca e filtro ativos ao mesmo tempo, **When** a página carrega, **Then** os
   resultados atendem aos dois critérios.
5. **Given** uma nota qualquer, **When** clico no link da mensagem original, **Then** a mensagem
   abre no Telegram.
6. **Given** notas de foto, áudio e documento com arquivo baixado, **When** abro a página,
   **Then** a foto aparece como miniatura, o áudio toca na página e o documento tem link.

---

### User Story 3 - Edição atualiza a nota (Priority: P2)

Se edito uma mensagem no grupo, a nota correspondente reflete o texto novo.

**Why this priority**: evita nota desatualizada, mas o caderno já funciona sem isso.

**Independent Test**: enviar uma mensagem, editá-la e conferir que continua existindo uma
única nota, agora com o texto editado.

**Acceptance Scenarios**:

1. **Given** uma nota "reunião às 14h", **When** edito a mensagem para "reunião às 15h",
   **Then** a mesma nota passa a mostrar "reunião às 15h" e registra a data da edição.
2. **Given** uma nota de texto, **When** edito a mensagem incluindo uma URL, **Then** o tipo da
   nota passa a ser link.

---

### User Story 4 - Ignorar o que não é meu (Priority: P2)

Só entram as mensagens que eu envio no meu grupo-caderno.

**Why this priority**: protege o caderno de ruído e garante privacidade de terceiros.

**Independent Test**: enviar mensagens de outra conta no grupo e de minha conta em outro
grupo; nenhuma nota é criada.

**Acceptance Scenarios**:

1. **Given** outra pessoa no grupo, **When** ela envia uma mensagem, **Then** nenhuma nota é criada.
2. **Given** eu em outro grupo onde o sistema também esteja, **When** envio uma mensagem lá,
   **Then** nenhuma nota é criada.

---

### User Story 5 - Preencher lacunas com a exportação do Telegram Desktop (Priority: P3)

Quando o sistema ficou desligado tempo demais, exporto o grupo pelo Telegram Desktop e mando o
sistema importar essa exportação. As mensagens que faltavam viram notas; as que já existiam
não são duplicadas.

**Why this priority**: garante que nada se perca (Princípio VIII) mesmo com o computador
desligado por dias; não é necessário no uso diário.

**Independent Test**: com uma exportação inventada contendo 10 mensagens do dono, 3 delas já
capturadas e 2 de outra pessoa, importar e conferir que surgem exatamente 7 notas novas.

**Acceptance Scenarios**:

1. **Given** uma exportação com mensagens que não estão no caderno, **When** importo, **Then**
   cada mensagem do dono vira nota, com o mesmo tipo e dados que teria se capturada ao vivo.
2. **Given** mensagens que já são notas, **When** importo a mesma exportação, **Then** nenhuma
   nota é duplicada nem perde dados.
3. **Given** a mesma exportação, **When** importo duas vezes, **Then** o resultado é idêntico ao
   de uma importação só.
4. **Given** mensagens de outras pessoas ou de outro chat na exportação, **When** importo,
   **Then** elas são ignoradas.
5. **Given** a exportação inclui fotos, áudios ou documentos de até 20 MB, **When** importo,
   **Then** os arquivos são copiados para a pasta local e ligados às notas.
6. **Given** a importação terminou, **When** olho o resultado, **Then** vejo quantas notas foram
   criadas, quantas já existiam, quantas foram ignoradas e quantas falharam.
7. **Given** a mesma exportação, **When** importo pelo terminal ou pelo painel, **Then** as notas
   resultantes são idênticas.

---

### Edge Cases

- Mensagem de tipo não listado (figurinha, enquete, nota de vídeo circular etc.): vira nota do
  tipo "outro", nunca é descartada.
- Falha ao processar ou baixar arquivo: a nota é guardada com o erro e aparece no painel em
  destaque; nada some (Princípio VIII).
- Vídeos: guardados como nota com legenda e link, sem download do arquivo nesta fatia.
- Arquivo acima de 20 MB: nota criada, sem download, com a indicação "acima de 20 MB".
- Álbum (várias fotos de uma vez): cada item vira uma nota separada.
- Mensagem encaminhada por mim: conta como minha.
- Mesma mensagem recebida duas vezes: continua existindo uma única nota.
- Mensagem apagada no Telegram: a nota permanece.
- Edição de mensagem que nunca foi capturada: cria a nota a partir da versão editada.
- Sistema desligado: mensagens enviadas no período são capturadas ao religar, dentro da
  janela que o Telegram mantém mensagens pendentes; além dela, a lacuna é preenchida pela
  importação da exportação do Telegram Desktop (User Story 5).
- Exportação inválida, incompleta ou de outro grupo (pasta sem `result.json`, JSON que não
  abre, sem identificador do chat ou sem lista de mensagens, ou chat diferente do configurado):
  a importação informa o problema e não altera notas existentes; mensagens individuais que falharem viram notas com erro.
- Mensagem na exportação sem o arquivo de mídia (exportada sem mídia): nota criada, com
  a indicação "arquivo não veio na exportação".
- Busca sem resultados: a página informa que nada foi encontrado.
- Banco inacessível no momento da captura: a falha não pode ser gravada; o sistema registra
  em log o identificador da mensagem e orienta recuperar pela importação (User Story 5), já
  que a mensagem continua no Telegram.
- Item da exportação que não pode ser processado: vira nota com erro e conta como falha;
  as demais mensagens da importação seguem normalmente.
- Importação interrompida no meio (processo encerrado ou erro geral): as notas já gravadas
  são mantidas; repetir a importação completa o resto sem duplicar (FR-019). Uma importação
  que ficou "em andamento" por mais de 1 hora é considerada abandonada e não bloqueia a
  próxima (FR-021).
- Edição que falha no processamento: a nota mantém o conteúdo anterior e passa a aparecer
  como falha, com o erro.
- Bot sem conexão com o Telegram: tenta reconectar sozinho e captura as mensagens pendentes
  ao voltar. Token ausente ou inválido: o bot não inicia e informa o motivo.
- Caderno vazio ou página além da última: a página informa que nada foi encontrado.
- Arquivo de uma nota apagado da pasta local: fora do escopo; a nota continua no painel com
  o link para a mensagem original.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST capturar mensagens enviadas pelo dono no grupo configurado e
  ignorar mensagens de qualquer outro remetente ou chat, sem guardar nada delas nem
  registrá-las em log.
- **FR-002**: O sistema MUST classificar cada mensagem em exatamente um tipo: texto, link,
  foto, áudio, vídeo, documento, localização, contato ou outro, por regra determinística.
- **FR-003**: Uma mensagem de texto que contém ao menos uma URL MUST ser classificada como link.
- **FR-004**: Cada nota MUST guardar: data de envio, tipo, texto (corpo ou legenda; vazio se
  não houver) e link para a mensagem original.
- **FR-005**: Localização MUST ter como texto as coordenadas; contato MUST ter nome e telefone.
- **FR-006**: Fotos, áudios (incluindo mensagens de voz) e documentos de até 20 MB MUST ser
  baixados para uma pasta local configurável, e a nota MUST referenciar o arquivo.
- **FR-007**: Arquivos acima de 20 MB e vídeos MUST NOT ser baixados; a nota MUST ser criada
  mesmo assim.
- **FR-008**: Ao editar uma mensagem, o sistema MUST atualizar a nota existente (texto, tipo e
  data da edição) sem criar nota nova.
- **FR-009**: Cada mensagem original MUST corresponder a no máximo uma nota.
- **FR-010**: O painel MUST listar as notas da mais recente para a mais antiga (por data de
  envio), 50 por página, com navegação para páginas anteriores. Sem busca nem filtro, a
  primeira página MUST se atualizar sozinha a cada 10 segundos (SC-004).
- **FR-011**: O painel MUST permitir busca por palavra no texto, ignorando maiúsculas e acentos.
- **FR-012**: O painel MUST permitir filtrar por tipo, combinável com a busca.
- **FR-013**: Cada nota no painel MUST mostrar data, tipo, texto e link para a mensagem
  original. Quando houver arquivo baixado: foto MUST aparecer como miniatura (clicável para o
  tamanho original), áudio MUST ter player na própria página e documento MUST ter link para
  abrir ou baixar.
- **FR-014**: Mensagens que falharem no processamento (leitura da mensagem, classificação,
  download ou cópia do arquivo, inclusive por falta de espaço em disco) MUST ser guardadas com
  a descrição do erro e aparecer no painel identificadas como falha.
- **FR-015**: O painel, incluindo os arquivos de mídia que ele serve, MUST ser acessível
  apenas a partir do próprio computador.
- **FR-016**: O banco de dados MUST ficar fora da pasta do repositório. Os arquivos de mídia
  MUST ficar numa pasta ignorada pelo Git (por padrão `data/media`, configurável).
- **FR-017**: O dono MUST poder importar uma exportação do grupo feita pelo Telegram Desktop
  (formato JSON da exportação), indicando a pasta da exportação, por duas vias equivalentes:
  um comando no terminal e uma ação no painel. As duas MUST produzir o mesmo resultado.
- **FR-018**: A importação MUST aplicar as mesmas regras da captura ao vivo: só mensagens do
  dono no grupo configurado, mesma classificação de tipo e mesmo limite de 20 MB para arquivos.
- **FR-019**: A importação MUST ser idempotente: uma mensagem já existente como nota MUST NOT
  ser duplicada nem sobrescrita, pois a nota capturada ao vivo é a fonte preferida.
- **FR-020**: Ao final, a importação MUST informar contagens de notas criadas, já existentes,
  ignoradas e com falha, no terminal ou no painel, conforme a via usada.
- **FR-021**: Uma nova importação MUST NOT começar enquanto outra estiver em andamento; a
  segunda tentativa é recusada com aviso.

### Key Entities

- **Nota**: uma mensagem capturada. Atributos: identificador da mensagem original, data de
  envio, data da última edição, tipo, texto, link para a mensagem, arquivo local (opcional),
  situação (ok, acima de 20 MB, arquivo não veio na exportação, falha), descrição do erro
  (opcional) e conteúdo original da mensagem (opcional, guardado em falhas e importações para
  diagnóstico; nunca sai do computador).
- **Arquivo**: mídia baixada para a pasta local, ligada a uma nota; nome, tamanho e caminho.
- **Nota** ganha o atributo origem (captura ao vivo ou importação). A mesma mensagem tem o
  mesmo identificador nas duas origens, o que permite evitar duplicatas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das mensagens do dono no grupo, de qualquer tipo, geram nota (incluindo as
  que falham, que aparecem como falha).
- **SC-002**: 100% das mensagens de teste dos 8 tipos listados são classificadas no tipo correto.
- **SC-003**: 0 notas criadas a partir de mensagens de outras pessoas ou outros chats.
- **SC-004**: Uma nota nova aparece no painel em até 10 segundos após o envio, com o sistema
  rodando.
- **SC-005**: Busca e filtro retornam resultados em até 1 segundo com 10.000 notas guardadas.
- **SC-006**: Após uma edição, existe exatamente uma nota para a mensagem, com o texto novo.
- **SC-007**: O dono encontra uma nota específica por palavra em menos de 30 segundos.
- **SC-008**: Importar uma exportação com 5.000 mensagens sem mídia leva menos de 2 minutos e, repetida,
  cria 0 notas novas.

## Assumptions

- Há um único usuário (o dono) e um único grupo-caderno, ambos definidos na configuração.
- A captura ao vivo só vê mensagens enviadas depois de o sistema estar ativo no grupo; o
  histórico anterior e as lacunas entram pela importação da exportação do Telegram Desktop.
- O Telegram guarda mensagens pendentes por tempo limitado (cerca de 24 horas); para períodos
  maiores, o dono faz a exportação e a importação manualmente.
- Na importação, edições feitas depois da captura ao vivo não são aplicadas (a nota existente
  é mantida); a captura ao vivo já atualiza edições quando o sistema está ligado.
- O limite de 20 MB acompanha o limite de download disponível pela API oficial do Telegram.
- Vídeos não são baixados nesta fatia porque o pedido lista apenas fotos, áudios e
  documentos para download.
- A edição substitui o conteúdo da nota; histórico de versões não é guardado.
- Busca de título e miniatura de links, página de links, classificação por assunto e
  lembretes estão fora do escopo.
- Os testes usam apenas mensagens inventadas (Princípio IV).
- O token do bot fica só no arquivo `.env`, fora do Git, e nunca aparece em log nem no painel.
- Os logs não contêm texto de mensagens nem o token; registram só o tipo do erro e os
  identificadores do chat e da mensagem.
- Apagar notas pelo painel e política de retenção estão fora do escopo; as notas ficam
  guardadas até o dono apagar o arquivo do banco.
- Para reprocessar uma nota com falha, o dono edita a mensagem no Telegram; a captura ao vivo
  regrava a nota. A importação não sobrescreve notas existentes, nem as com falha (FR-019).
- Notas novas criadas pela importação guardam a data de edição que vier na exportação.
- Busca com várias palavras retorna as notas que contêm todas elas, em qualquer ordem.
- As datas do painel aparecem no fuso horário do computador.
- Acessibilidade mínima: miniaturas têm texto alternativo (a legenda) e tudo funciona pelo
  teclado com HTML padrão.
- O painel mostra a importação como "em andamento" até o fim, atualizando sozinho; as
  contagens aparecem só ao terminar.
