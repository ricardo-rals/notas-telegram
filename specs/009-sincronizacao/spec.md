# Feature Specification: Sincronização com Um Clique

**Feature Branch**: `009-sincronizacao`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Importação automática: verificar a data da última mensagem salva no banco e atualizar tudo com apenas um clique, sem precisar importar nenhum arquivo. No caso seria uma sincronização."

## Clarifications

### Session 2026-11-10

- Q: Como ler o histórico, se a API de bots não permite? → A: pela API MTProto oficial, logada
  na conta do dono, só leitura do grupo configurado (constituição 2.0.0, Princípio VII).
- Q: "Desde a última mensagem" é por data ou por número? → A: pelo número da mensagem, que só
  cresce no grupo; pega tudo depois da maior mensagem já salva. Com o caderno vazio, pega o
  histórico inteiro.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sincronizar com um clique (Priority: P1)

Clico em "Sincronizar" no painel. Tudo o que mandei no grupo depois da última nota salva vira
nota, com as mesmas regras da captura ao vivo, e vejo quantas entraram.

**Independent Test**: com um cliente falso que devolve mensagens inventadas, sincronizar e
conferir as notas, as contagens e que só mensagens depois da última salva foram pedidas.

**Acceptance Scenarios**:

1. **Given** a última nota é a mensagem 120, **When** clico em Sincronizar, **Then** só mensagens
   depois da 120 são lidas, e as do dono viram notas com origem "sincronização".
2. **Given** fotos, áudios e documentos até 20 MB, **Then** são baixados como na captura ao vivo;
   vídeos e arquivos maiores seguem as regras da 001.
3. **Given** mensagens de outras pessoas no grupo, **Then** são ignoradas e contadas como ignoradas.
4. **Given** a sincronização terminou, **Then** vejo criadas, ignoradas e falhas, e o aviso de
   notas novas aparece na lista.
5. **Given** uma sincronização ou importação em andamento, **When** clico de novo, **Then** vejo
   "já existe uma importação em andamento".

---

### User Story 2 - Configurar e entrar uma vez (Priority: P1)

Coloco `TELEGRAM_API_ID` e `TELEGRAM_API_HASH` no `.env` e rodo
`uv run --env-file .env python -m notas.sincronizacao login` uma vez, digitando o telefone e o
código que o Telegram mandar. Depois disso, o botão funciona sem pedir nada.

**Acceptance Scenarios**:

1. **Given** sem `TELEGRAM_API_ID`, **When** clico em Sincronizar, **Then** vejo o que configurar.
2. **Given** configurado mas sem login, **Then** vejo o comando de login.

### Edge Cases

- Mensagem de serviço (alguém entrou, mensagem fixada): ignorada.
- Mensagem de admin anônimo (sem remetente): ignorada, como na captura ao vivo.
- Falha no meio (rede caiu): o que já entrou fica; a importação é marcada com o erro; clicar de
  novo continua de onde parou.
- Mensagem já capturada ao vivo entre a leitura e a gravação: não duplica (FR-009 da 001).

## Requirements *(mandatory)*

- **FR-001**: O painel MUST ter um botão "Sincronizar" que lê, só no grupo configurado, as
  mensagens com número maior que a maior mensagem salva desse grupo, da mais antiga para a mais nova.
- **FR-002**: Cada mensagem MUST passar pelo mesmo processamento da captura ao vivo (dono,
  classificação, links, tags, download, falha visível), com origem "sincronizacao".
- **FR-003**: O cliente MUST só ler (nunca enviar, editar ou apagar) e MUST NOT ler outros chats.
- **FR-004**: A sincronização MUST usar a trava de importação (uma por vez) e registrar contagens
  e erro como uma importação com via "sincronizacao".
- **FR-005**: O login MUST ser feito pelo dono num comando de terminal; a sessão MUST ficar fora
  do repositório (padrão `%LOCALAPPDATA%\notas-telegram\telegram.session`).
- **FR-006**: Sem configuração ou sem login, o botão MUST explicar o que falta, sem erro técnico.

## Success Criteria *(mandatory)*

- **SC-001**: Depois de dias com o bot desligado, 1 clique traz todas as mensagens do dono.
- **SC-002**: Sincronizar duas vezes seguidas cria 0 notas na segunda.

## Assumptions

- O `api_id`/`api_hash` vêm de my.telegram.org, criados pelo dono.
- Edições de mensagens antigas feitas com o bot desligado não são reaplicadas (como na importação).
