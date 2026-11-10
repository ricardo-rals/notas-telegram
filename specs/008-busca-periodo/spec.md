# Feature Specification: Busca Ampliada e Filtro por Data e Hora

**Feature Branch**: `008-busca-periodo`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Filtro por data e hora. A busca deve buscar também as informações da thumb ou algo relacionado; por exemplo, se buscar por Luiz, vai buscar tudo o que tem Luiz."

## Clarifications

### Session 2026-11-10

- Q: Onde a busca procura? → A: no texto da nota, no nome do arquivo, no título e na descrição
  da prévia de cada link, no autor da linha do WhatsApp, no site e no endereço do link — em
  todas as abas, não só na aba Link.
- Q: "Luiz" deve achar "Luis"? → A: não por grafia parecida; a busca acha palavras que começam
  com o que foi digitado ("Lui" acha "Luis" e "Luiz"). Grafias diferentes ficam fora desta fatia.
- Q: O filtro usa data e hora? → A: só data (revisão do dono após o uso); "até" vazio = hoje.
- Q: O período usa qual data? → A: a data de envio da nota; na aba Link, a data do item (a da
  linha do WhatsApp, quando houver), a mesma usada para ordenar.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar em tudo que está ligado à nota (Priority: P1)

Busco "Montenegro" e aparecem as notas cujos links têm "Montenegro" no título da prévia, mesmo
sem essa palavra no texto que eu mandei.

**Acceptance Scenarios**:

1. **Given** uma nota de link cujo texto é só a URL e cuja prévia tem o título "Luis Eduardo
   Montenegro on Instagram", **When** busco "montenegro" na aba Todas, **Then** a nota aparece.
2. **Given** uma lista do WhatsApp com autor "Usuario", **When** busco "usuario", **Then** a nota aparece.
3. **Given** um link do youtube.com, **When** busco "youtube", **Then** ele aparece.
4. **Given** um documento "Relatório anual.pdf", **When** busco "relatorio", **Then** ele aparece.
5. **Given** a busca "lui", **Then** aparecem "Luis" e "Luiz".

---

### User Story 2 - Filtrar por período (Priority: P1)

Escolho "de" e "até" (data e hora) ou um atalho (Hoje, 7 dias, 30 dias) e a lista mostra só o
período, combinando com busca, categoria, site e tag.

**Acceptance Scenarios**:

1. **Given** notas de 01/11 e 05/11, **When** escolho de 03/11 00:00, **Then** só a de 05/11 aparece.
2. **Given** "até 03/11 12:00", **Then** só notas enviadas até esse instante (hora local).
3. **Given** o atalho "7 dias", **Then** o filtro "de" vira agora menos 7 dias.
4. **Given** período ativo, **When** troco de categoria ou tag, **Then** o período continua.
5. **Given** "de" depois de "até", **Then** a lista fica vazia com a mensagem de nada encontrado.
6. **Given** uma data em formato inválido no endereço, **Then** o painel responde 422.

## Requirements *(mandatory)*

- **FR-001**: A busca MUST casar com: texto, nome do arquivo, título e descrição das prévias dos
  links da nota, autor, site e endereço dos links; em todas as abas; com as regras da 007
  (sem maiúsculas/acentos, todas as palavras, prefixo).
- **FR-002**: Na aba Link, cada item MUST casar pelo texto da nota, pela sua prévia ou pelo seu
  autor, site e endereço.
- **FR-003**: O painel MUST aceitar `de` e `ate` (só a data, `AAAA-MM-DD`, dias inteiros no fuso
  local), filtrar pela data de envio (aba Link: data do item) e manter o período em todos os links
  do painel. Sem `ate`, vale o dia de hoje, e o campo mostra a data de hoje.
- **FR-004**: O painel MUST oferecer atalhos Hoje, 7 dias e 30 dias e um "limpar período".
- **FR-005**: Com 10.000 notas, busca e período MUST responder em até 1 segundo.

## Success Criteria *(mandatory)*

- **SC-001**: Buscar um nome que só aparece no título de uma prévia acha a nota em 1 busca.
- **SC-002**: Filtrar um dia específico leva no máximo 2 cliques ou 1 atalho.

## Assumptions

- O período é inclusivo nos dois lados, por dia inteiro: "de" começa às 00:00 e "até" vai até
  23:59:59. (Revisão de 2026-11-10, a pedido do dono: a hora saiu do filtro.)
- O fuso é o do computador, o mesmo das datas mostradas.
