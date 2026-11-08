# Feature Specification: Tags por Hashtag e Subcategorias de Documentos

**Feature Branch**: `005-tags-subcategorias`

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "Categorizar o que foi enviado com categorias criadas por mim: escrevo #receita ou #trabalho na mensagem e a nota ganha essa tag; o painel lista as tags com contagens e filtra por elas, combinando com tipo e busca. Na categoria Documento, botões por tipo de arquivo (PDF, planilhas, textos, apresentações, compactados, imagens, outros), como os sites na categoria Link."

## Clarifications

### Session 2026-11-08

Execução automática pedida pelo dono; cada pergunta foi respondida com a opção recomendada.

- Q: `#Receita` e `#receita` são a mesma tag? → A: sim; a tag é guardada em minúsculas e
  comparada sem diferença de maiúsculas. Acentos contam (`#reunião` ≠ `#reuniao`) para não
  juntar palavras diferentes.
- Q: Um `#` dentro de um link (`https://site.com/#secao`) vira tag? → A: não; só `#` no início
  do texto ou depois de espaço ou pontuação, fora de URLs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marcar notas com hashtags (Priority: P1)

Escrevo "pão de queijo #receita #cozinha" no grupo. A nota ganha as tags `receita` e
`cozinha`. No painel, a barra lateral tem uma seção Tags com cada tag e a sua contagem; clico em
`#receita` e vejo só as notas com essa tag, de qualquer tipo.

**Why this priority**: é a categorização feita pelo próprio dono, sem modelo, que ele pediu.

**Independent Test**: gravar 3 notas com `#receita` (uma foto com legenda, um link, um texto) e
1 com `#trabalho`; conferir as contagens e o filtro.

**Acceptance Scenarios**:

1. **Given** a mensagem "pão #Receita #cozinha", **When** ela é capturada, **Then** a nota tem as
   tags `receita` e `cozinha`.
2. **Given** notas com tags, **When** abro o painel, **Then** a seção Tags lista cada tag com a sua
   contagem, da mais usada para a menos usada.
3. **Given** a tag `receita` selecionada, **When** escolho a categoria Foto, **Then** vejo só fotos
   com `#receita`; a busca também combina.
4. **Given** um cartão com tags, **When** o vejo, **Then** as tags aparecem como etiquetas que
   levam ao filtro da tag.
5. **Given** uma nota editada removendo `#receita`, **When** a edição é capturada, **Then** a nota
   sai da tag.

---

### User Story 2 - Subcategorias de documentos (Priority: P2)

Na categoria Documento, vejo botões por tipo de arquivo, cada um com a sua contagem, como os
sites na categoria Link.

**Why this priority**: documentos variados ficam misturados; o padrão já é conhecido pela categoria Link.

**Independent Test**: com documentos `.pdf`, `.xlsx`, `.docx` e `.zip`, conferir os botões, as
contagens e o filtro.

**Acceptance Scenarios**:

1. **Given** 2 PDFs, 1 planilha e 1 zip, **When** abro Documento, **Then** vejo "Todos", "PDF (2)",
   "Planilhas (1)", "Compactados (1)", e só grupos com documentos.
2. **Given** o botão PDF, **When** clico, **Then** só PDFs aparecem e o endereço guarda o grupo.

### Edge Cases

- `#` sozinho, `#123` só com dígitos, `##` e `#` no meio de palavra (`c#`): não viram tag.
- Tag com mais de 40 caracteres: ignorada.
- A mesma tag repetida na mensagem: conta uma vez.
- Hashtag dentro de URL (`/#secao`, `?a=1#b`): não vira tag.
- Notas antigas: as tags saem do texto já guardado, sem precisar reenviar.
- Documento sem nome de arquivo ou sem extensão conhecida: grupo "Outros".
- Tag inexistente no endereço: lista vazia com a mensagem de categoria vazia.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Uma tag MUST ser uma palavra iniciada por `#` no começo do texto ou depois de
  espaço/pontuação, com letras, dígitos ou `_`, ao menos uma letra, até 40 caracteres, fora de
  URLs; guardada em minúsculas, sem repetição por nota.
- **FR-002**: Tags MUST ser extraídas por regra determinística do texto (corpo ou legenda) na
  captura, na edição (substituindo as anteriores) e na importação, e das notas já guardadas.
- **FR-003**: A barra lateral MUST ter uma seção Tags, só quando existir alguma, com cada tag e a
  contagem de notas, da mais usada para a menos usada (empate em ordem alfabética).
- **FR-004**: Selecionar uma tag MUST filtrar a lista, combinável com categoria, site e busca,
  mantendo a tag no endereço (`?tag=`).
- **FR-005**: Cada cartão MUST mostrar as tags da nota como etiquetas que levam ao filtro.
- **FR-006**: Na categoria Documento, o painel MUST mostrar botões por grupo de arquivo, com
  contagem, só dos grupos presentes: PDF; Planilhas (xls, xlsx, ods, csv); Textos (doc, docx,
  odt, txt, rtf, md); Apresentações (ppt, pptx, odp, key); Compactados (zip, rar, 7z, tar, gz);
  Imagens (jpg, jpeg, png, gif, webp, heic, svg); Outros (o resto e sem nome).
- **FR-007**: Selecionar um grupo MUST filtrar os documentos, combinável com a busca, mantendo o
  grupo no endereço (`?grupo=`).

### Key Entities

- **Tag**: nome (minúsculas) ligado a uma nota; uma nota tem 0 ou mais tags, sem repetição.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das hashtags válidas dos testes viram tags; 0 falsos positivos nos casos de borda.
- **SC-002**: O dono chega às notas de uma tag em 1 clique a partir da página inicial.
- **SC-003**: Com 10.000 notas e 20.000 tags, listar e filtrar por tag leva até 1 segundo.
- **SC-004**: Notas guardadas antes da funcionalidade ganham as suas tags ao atualizar o banco.

## Assumptions

- Tags não são criadas nem editadas pelo painel nesta fatia; a fonte é o texto da mensagem.
- Tags de notas com falha saem do texto que existir (normalmente vazio).
- O grupo de documento vem da extensão do nome do arquivo, sem abrir o arquivo.
