# Feature Specification: Backup Automático, Comando Único e Início com o Windows

**Feature Branch**: `006-backup-inicio-automatico`

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "Backup automático do banco (cópia diária, guardando as últimas 7), um comando que sobe o bot e o painel juntos, e opção de iniciar tudo sozinho quando o Windows liga."

## Clarifications

### Session 2026-11-08

Execução automática pedida pelo dono; respostas recomendadas.

- Q: Onde ficam os backups? → A: numa pasta `backups` ao lado do banco, fora do repositório,
  configurável; nunca dentro do repositório (Princípio IV).
- Q: O início automático é ligado sozinho? → A: não; o dono roda um comando para instalar e
  outro para remover. Nada muda na inicialização do Windows sem esse comando.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backup diário sem pensar (Priority: P1)

Com o painel rodando, o sistema faz uma cópia do caderno uma vez por dia e guarda as 7 mais
recentes. Na página Importar vejo quando foi o último backup; se ele estiver atrasado, vejo o aviso.

**Why this priority**: o banco é um arquivo só; perdê-lo é perder o caderno.

**Independent Test**: com o painel recém-iniciado e nenhum backup, conferir que surge uma cópia
íntegra; com 8 cópias antigas, conferir que restam 7.

**Acceptance Scenarios**:

1. **Given** nenhum backup, **When** o painel inicia, **Then** em até 1 minuto existe uma cópia
   íntegra do banco em `backups`, com data e hora no nome.
2. **Given** um backup de 3 horas atrás, **When** o painel verifica, **Then** nenhuma cópia nova é feita.
3. **Given** 8 backups, **When** um novo é feito, **Then** sobram os 7 mais recentes.
4. **Given** o último backup com mais de 48 horas, **When** abro Importar, **Then** vejo um aviso
   de backup atrasado; com backup em dia, vejo a data dele.
5. **Given** um backup falha (pasta sem permissão), **Then** o erro vai para o log e aparece na
   página Importar; o painel continua funcionando.

---

### User Story 2 - Um comando para subir tudo (Priority: P1)

Dou dois cliques em `iniciar.cmd` (ou rodo no terminal) e o bot e o painel sobem, cada um na sua
janela minimizada.

**Independent Test**: rodar `iniciar.cmd` e conferir os dois processos e o painel respondendo.

**Acceptance Scenarios**:

1. **Given** o `.env` preenchido, **When** rodo `iniciar.cmd`, **Then** o bot e o painel ficam
   rodando, cada um na sua janela minimizada, sem eu abrir terminais.

---

### User Story 3 - Iniciar com o Windows (Priority: P2)

Rodo `uv run python -m notas.servico instalar` uma vez; a partir daí, o bot e o painel sobem
sozinhos quando entro no Windows. `desinstalar` desfaz.

**Acceptance Scenarios**:

1. **Given** o comando `instalar`, **When** ele roda, **Then** um atalho de inicialização aponta para
   `iniciar.cmd` deste projeto, e a saída diz onde ele foi criado.
2. **Given** o comando `desinstalar`, **When** ele roda, **Then** o atalho some; sem atalho, informa
   que não havia nada para remover.

### Edge Cases

- Backup durante uma gravação do bot: a cópia é consistente (SQLite garante cópia atômica).
- Pasta de backups com arquivos que não são backups: nunca são apagados.
- Relógio do computador voltou no tempo: um backup "do futuro" não impede o seguinte de ser feito
  depois de 24 h pelo relógio atual; a contagem usa o arquivo mais recente pelo nome.
- `BACKUP_DIR` dentro do repositório: configuração recusada com mensagem clara.
- `BACKUP_MANTER=0` ou negativo: recusado; mínimo 1.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O painel MUST verificar ao iniciar e depois a cada hora se o último backup tem mais
  de 24 horas e, se tiver ou não existir, fazer uma cópia consistente do banco.
- **FR-002**: O backup MUST ser um arquivo SQLite íntegro e completo, nomeado
  `notas-AAAAMMDD-HHMMSS.db`, em `BACKUP_DIR` (padrão: `backups` ao lado do banco).
- **FR-003**: Depois de cada backup, MUST sobrar só os `BACKUP_MANTER` (padrão 7) mais recentes;
  arquivos com outro nome nunca são apagados.
- **FR-004**: `uv run --env-file .env python -m notas.backup` MUST fazer um backup na hora e
  mostrar onde ele ficou.
- **FR-005**: A página Importar MUST mostrar a data do último backup, aviso quando ele tiver mais
  de 48 horas ou não existir, e o último erro de backup, se houver.
- **FR-006**: `BACKUP_DIR` MUST ficar fora do repositório; `BACKUP_MANTER` MUST ser inteiro ≥ 1.
- **FR-007**: `iniciar.cmd`, na raiz do projeto, MUST subir o bot e o painel em janelas
  minimizadas, a partir da pasta do projeto, sem depender da pasta de onde foi chamado.
- **FR-008**: `python -m notas.servico instalar` MUST criar um atalho de inicialização do usuário
  que roda `iniciar.cmd`; `desinstalar` MUST removê-lo; nenhum dos dois mexe em outra configuração
  do sistema.

## Success Criteria *(mandatory)*

- **SC-001**: Com o painel rodando continuamente, nunca passam mais de 25 horas sem backup.
- **SC-002**: Um backup restaurado (copiado no lugar do banco) abre no painel com as mesmas notas.
- **SC-003**: Do computador ligado ao painel no ar, 0 ações do dono depois de `instalar`.

## Assumptions

- O backup é local, no mesmo disco; copiar a pasta `backups` para outro lugar é decisão do dono
  (um Drive exigiria mudar a constituição).
- A mídia (`data/media`) não entra no backup diário: os arquivos podem ser baixados de novo pelo
  link do Telegram, e o banco é o que não se recupera.
- "Atalho de inicialização" é um arquivo `.cmd` na pasta Inicializar do usuário do Windows.
