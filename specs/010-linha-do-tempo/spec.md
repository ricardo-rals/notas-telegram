# Feature Specification: Aba Todas como Linha do Tempo

**Feature Branch**: `010-linha-do-tempo` · **Created**: 2026-11-10 · **Status**: Draft

**Input**: "A aba Todas não ficou legal; remova ou melhore para ter uma UI/UX melhor."

## Problema observado (painel real, 1440 px)

Cartões aninhados (uma lista de 9 links vira uma coluna de 9 mini-cartões dentro de um cartão),
o endereço cru repetido acima da prévia, buracos na grade por alturas muito diferentes e nenhuma
noção de quando as coisas chegaram.

## User Story 1 - Linha do tempo plana, agrupada por dia (Priority: P1)

Na aba Todas, cada coisa que mandei é um cartão: cada link vira um cartão próprio (igual à aba
Link); fotos, documentos e textos continuam no seu formato. Os cartões ficam sob títulos de dia
("Hoje", "Ontem", "5 de novembro"), do mais recente ao mais antigo.

**Acceptance Scenarios**:

1. **Given** a lista do WhatsApp com 9 links e 1 texto, **When** abro Todas, **Then** vejo 10
   cartões, nenhum cartão dentro de outro, e a contagem de Todas é 10.
2. **Given** itens de hoje, de ontem e de 05/11, **Then** aparecem sob "Hoje", "Ontem" e
   "5 de novembro", nessa ordem.
3. **Given** busca, tag ou período, **Then** a linha do tempo aplica os mesmos filtros (links
   pela data do item, como na aba Link).
4. **Given** mais de 50 itens, **Then** a paginação conta itens.

## Requirements

- **FR-001**: Todas MUST listar itens: notas que não são de link e um item por link, ordenados
  pela data (links pela data do item), 50 por página.
- **FR-002**: Itens MUST ser agrupados por dia local, com rótulos Hoje, Ontem e "D de mês".
- **FR-003**: A contagem de Todas MUST contar itens (notas sem link + itens de link).
- **FR-004**: Busca, tag e período MUST valer na linha do tempo com as regras da 008.
- **FR-005**: As outras abas não mudam.

## Success Criteria

- **SC-001**: 0 cartões aninhados na aba Todas.
- **SC-002**: Com 10.000 notas e 5.000 links, a linha do tempo responde em até 1 s.
