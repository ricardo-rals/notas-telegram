# Feature Specification: Armazenamento em PostgreSQL

**Feature Branch**: `007-postgresql`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Criei um banco no Postgres (usuário postgres, banco telegram). Quero que tudo fique salvo nesse banco."

## Clarifications

### Session 2026-11-10

- Q: E as notas que já estão no SQLite? → A: um comando copia tudo do SQLite para o PostgreSQL
  uma vez; o SQLite fica intacto, como cópia de segurança.
- Q: Onde rodam os testes? → A: num banco separado no mesmo servidor, cujo nome termina em
  `_test`; os testes nunca tocam o banco `telegram`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tudo gravado no PostgreSQL (Priority: P1)

Bot, painel, importação, prévias e tags passam a ler e gravar no banco PostgreSQL configurado,
com o mesmo comportamento das fatias 001 a 006, inclusive a busca sem diferença de maiúsculas e
acentos.

**Independent Test**: a suíte inteira passa contra o banco de teste PostgreSQL.

**Acceptance Scenarios**:

1. **Given** `DATABASE_URL` apontando para o PostgreSQL local, **When** rodo `alembic upgrade head`,
   **Then** as tabelas são criadas no banco `telegram`.
2. **Given** o painel rodando, **When** busco "reuniao", **Then** acho "Reunião" (sem acento e sem
   diferença de maiúsculas), e "reun" também acha (prefixo).
3. **Given** `DATABASE_URL` com host diferente de `127.0.0.1`/`localhost`, **Then** a configuração
   é recusada (Princípio IV).

---

### User Story 2 - Trazer as notas do SQLite (Priority: P1)

Rodo um comando uma vez e todas as notas, importações e prévias do SQLite antigo aparecem no
PostgreSQL, com links e tags reconstruídos.

**Acceptance Scenarios**:

1. **Given** o SQLite com 7 notas e o PostgreSQL vazio, **When** rodo
   `python -m notas.migrar_sqlite`, **Then** o PostgreSQL tem as 7 notas, com os mesmos ids, links,
   tags e prévias, e o comando mostra as contagens.
2. **Given** o PostgreSQL já com notas, **When** rodo o comando, **Then** ele recusa e não altera nada.

---

### User Story 3 - Backup do PostgreSQL (Priority: P2)

O backup diário da 006 passa a usar `pg_dump`, com as mesmas regras de agenda, retenção e aviso.

**Acceptance Scenarios**:

1. **Given** o painel rodando, **When** o backup é feito, **Then** surge `notas-AAAAMMDD-HHMMSS.dump`
   em `BACKUP_DIR`, restaurável com `pg_restore`.

### Edge Cases

- PostgreSQL desligado: bot e painel encerram com mensagem clara ("não consegui conectar ao
  PostgreSQL em 127.0.0.1:5432"), sem mostrar a senha.
- `pg_dump` não encontrado: o backup registra o erro (visível em Importar), o resto segue.
- SQLite em revisão antiga (0001 a 0005): a cópia funciona com as colunas que existirem.

## Requirements *(mandatory)*

- **FR-001**: `DATABASE_URL` MUST ser obrigatório e apontar para PostgreSQL em `127.0.0.1` ou
  `localhost`; a senha MUST NOT aparecer em log nem em mensagem de erro.
- **FR-002**: O esquema MUST reproduzir as fatias 001 a 006 (restrições, unicidade, uma importação
  por vez) e a busca MUST ignorar maiúsculas e acentos, com todas as palavras e prefixo.
- **FR-003**: `python -m notas.migrar_sqlite [arquivo]` MUST copiar notas (com ids), importações e
  prévias, reconstruir links e tags, ajustar as sequências e recusar se o destino já tiver notas.
- **FR-004**: O backup MUST usar `pg_dump` em formato custom, sem pôr a senha na linha de comando.
- **FR-005**: Os testes MUST rodar só num banco cujo nome termina em `_test` e MUST recusar rodar
  se `TEST_DATABASE_URL` for igual a `DATABASE_URL`.

## Success Criteria *(mandatory)*

- **SC-001**: A suíte das fatias 001 a 006 passa contra o PostgreSQL, com os mesmos limites de
  desempenho (buscas ≤ 1 s com 10.000 notas).
- **SC-002**: As 7 notas do SQLite real aparecem no painel depois da migração, com a mesma busca.

## Assumptions

- O servidor PostgreSQL é o 18 instalado no Windows, com a extensão `unaccent` disponível.
- Datas continuam como texto ISO UTC, como no SQLite (ordenação e comparação iguais).
- O SQLite antigo não é apagado; vira só uma cópia.
