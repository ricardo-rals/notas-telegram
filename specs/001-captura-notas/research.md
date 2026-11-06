# Research: Captura de Notas do Grupo do Telegram

Decisões técnicas da fatia 001. Stack definida pelo dono; aqui ficam os pontos que a stack
não resolve sozinha.

## R1. Receber mensagens do grupo

- **Decision**: python-telegram-bot (v21+) com `Application.run_polling(allowed_updates=
  ["message", "edited_message"])`. Filtro na entrada: `filters.Chat(ALLOWED_CHAT_ID) &
  filters.User(ALLOWED_USER_ID)`. O bot precisa ter o modo de privacidade desligado no
  BotFather (`/setprivacy` → Disable) ou ser admin do grupo para ver todas as mensagens.
- **Rationale**: long polling não precisa de endereço público (Princípio I). Filtrar por chat
  e usuário cobre FR-001 de forma determinística.
- **Alternatives considered**: webhook (exige URL pública, rejeitado); filtrar dentro do
  handler (mesmo efeito, mais código).
- **Notas**:
  - Mensagens enviadas como "admin anônimo" chegam com remetente `GroupAnonymousBot` e
    seriam ignoradas. O quickstart orienta a desligar o anonimato.
  - O Telegram guarda updates pendentes por ~24 h; além disso vale a importação (R6).

## R2. Classificação de tipo (FR-002, FR-003, FR-005)

- **Decision**: função pura `classificar(m: MensagemNormalizada) -> (tipo, texto)`, aplicada
  igualmente à captura ao vivo e à importação. Cada fonte tem um adaptador que converte seu
  formato em `MensagemNormalizada`. Ordem das regras (primeira que casa):
  1. `foto` (photo)
  2. `outro` para animação/GIF, figurinha, nota de vídeo circular, enquete, dado, etc.
     A animação vem antes de documento porque a Bot API também a expõe como `document`.
  3. `audio` (audio ou voice)
  4. `video`
  5. `documento`
  6. `localizacao` (location ou venue) → texto `"lat, lon"`
  7. `contato` → texto `"Nome Sobrenome, +55..."`
  8. `link` se o texto tem entidade `url`/`text_link`; se não houver entidades, regex
     `https?://\S+`
  9. `texto` se há texto; senão `outro`
- **Rationale**: Princípio II: tudo é regra; um conjunto só de regras para as duas fontes
  garante FR-018.
- **Alternatives considered**: regras separadas por fonte (duplicação, divergência).

## R3. Link para a mensagem original

- **Decision**: `https://t.me/c/{id_interno}/{message_id}`, onde `id_interno` é o chat_id
  sem o prefixo `-100`. Exige supergrupo (todo grupo privado moderno é; grupo básico vira
  supergrupo ao ativar, por exemplo, "histórico visível para novos membros").
- **Rationale**: é o único formato de link para mensagem de grupo privado.
- **Notas**: se o chat não for supergrupo, o bot recusa iniciar com mensagem clara.

## R4. Download de mídia (FR-006, FR-007)

- **Decision**: `bot.get_file()` + `download_to_drive()` para foto (maior resolução), áudio,
  voz e documento com `file_size <= 20 MB`. Nome: `{message_id}_{file_unique_id}{ext}` em
  `MEDIA_DIR`. Vídeos nunca são baixados. Acima do limite: nota com
  `situacao = grande_demais`. Falha no download: nota com `situacao = falha` e erro.
- **Rationale**: 20 MB é o limite do `getFile` na Bot API; usar `file_unique_id` evita
  colisão entre edições.
- **Alternatives considered**: servidor local da Bot API (sem limite, mas é um serviço a
  mais; Princípio VI).

## R5. Banco, busca e concorrência

- **Decision**: SQLite em arquivo único definido por `DATABASE_PATH` (padrão
  `%LOCALAPPDATA%\notas-telegram\notas.db`, fora do repositório). SQLAlchemy 2 síncrono.
  Pragmas na conexão: `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`.
  Busca: tabela FTS5 de conteúdo externo sobre `nota.texto`, tokenizer
  `unicode61 remove_diacritics 2`, mantida por triggers criadas na migração Alembic (SQL
  direto em `op.execute`). O termo digitado vira tokens entre aspas (`"reuniao" "15h"`),
  então caracteres especiais do FTS não quebram a consulta.
- **Rationale**: WAL deixa bot, painel e importação lerem e escreverem ao mesmo tempo
  sem erro de "database is locked". `remove_diacritics 2` resolve FR-011 (maiúsculas e
  acentos); confirmado no SQLite 3.53 que vem com o Python 3.12 do Windows.
- **Alternatives considered**: `LIKE` com normalização em Python (varredura completa, não
  atende SC-005 com folga); SQLAlchemy async (aiosqlite) — complexidade a mais; escritas de
  uma nota levam milissegundos, então bloquear o loop do bot é aceitável.

## R6. Importação da exportação do Telegram Desktop (FR-017 a FR-021)

- **Decision**: ler `result.json` da pasta indicada. Campos usados: `id` e `type` do chat;
  em cada mensagem, `id`, `type` (só `message`), `date_unixtime`, `edited_unixtime`,
  `from_id` (`"user<ID>"`), `text_entities`, `photo`, `file`, `media_type`, `mime_type`,
  `file_size`, `location_information`, `contact_information`, `poll`, `sticker_emoji`.
  O adaptador produz `MensagemNormalizada`; daí em diante vale R2. A gravação usa
  `INSERT ... ON CONFLICT(chat_id, message_id) DO NOTHING` numa transação só.
  - Chat: o `id` da exportação vem sem o `-100`; compara-se com `ALLOWED_CHAT_ID` após
    normalizar. Chat diferente → importação recusada sem tocar no banco.
  - Mídia: arquivo copiado da pasta da exportação para `MEDIA_DIR` se `<= 20 MB`. O valor
    `"(File not included...)"` vira `situacao = sem_arquivo`.
- **Exclusão mútua (FR-021)**: tabela `importacao` com índice único parcial
  `WHERE status = 'rodando'`. Uma segunda importação falha no INSERT e é recusada. Uma
  execução com status `rodando` há mais de 1 h é considerada abandonada e marcada `falha`
  antes de tentar.
- **Rationale**: o próprio banco garante a exclusão entre processos (CLI e painel), sem
  lockfile. O `message_id` da exportação é o mesmo da Bot API em supergrupos, o que garante
  a idempotência.
- **Alternatives considered**: exportação em HTML (frágil de parsear); lockfile (some se o
  processo morrer de um jeito, fica órfão de outro).

## R7. Painel

- **Decision**: FastAPI + Jinja2 + HTMX (um arquivo JS servido localmente, sem CDN, para
  não abrir rede além do Telegram). `uvicorn.run(host="127.0.0.1")` fixo no código, sem
  opção de configurar o host. Mídia servida por `StaticFiles` montado em `/media`.
  Importação pelo painel roda em thread de fundo; a página consulta o status via HTMX a
  cada 2 s.
- **Proteção local**: middleware recusa requisições cujo `Host` não seja `127.0.0.1:<porta>`
  ou `localhost:<porta>` (bloqueia DNS rebinding) e POST cujo `Origin` não seja o próprio
  painel (bloqueia CSRF de outro site aberto no navegador).
- **Rationale**: FR-015 e Princípio IV; sem build de front (Princípio VI).
- **Alternatives considered**: HTMX via CDN (requisição externa, viola Princípio I).

## R8. Configuração

- **Decision**: variáveis de ambiente lidas com `os.environ` num dataclass; o `.env` é
  carregado por `uv run --env-file .env`. Variáveis: `TELEGRAM_BOT_TOKEN`,
  `ALLOWED_CHAT_ID`, `ALLOWED_USER_ID`, `DATABASE_PATH`, `MEDIA_DIR`, `PAINEL_PORT`.
  Variável obrigatória ausente → o processo encerra com mensagem clara.
- **Rationale**: zero dependência extra para ler `.env`.
- **Alternatives considered**: pydantic-settings / python-dotenv (dependência a mais para
  seis variáveis).

## R9. Falha visível (FR-014, Princípio VIII)

- **Decision**: o handler do bot envolve todo o processamento. Em qualquer exceção, grava a
  nota com `situacao = falha`, o erro e o update original em JSON (`bruto`), com tipo
  `outro` se a classificação não chegou a rodar. O painel destaca essas notas e tem filtro
  "falhas". O handler global de erros do PTB registra em log o que não puder nem ser gravado
  (por exemplo, banco inacessível).
- **Rationale**: guardar o original permite reprocessar depois.
