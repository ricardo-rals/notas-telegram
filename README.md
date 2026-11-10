# Notas Telegram

**Transforme um grupo privado do Telegram num caderno pessoal organizado, pesquisável e 100% seu.**

Você manda qualquer coisa no grupo (um texto, um link do Instagram, uma foto, um áudio, um PDF,
uma localização) e ela vira uma nota no seu computador, organizada por tipo, por site e por tag,
com busca e um painel web para encontrar tudo depois.

---

## Por que existe

Muita gente usa um grupo só seu no Telegram (ou o "Mensagens salvas") como caderno: é o jeito
mais rápido de guardar algo no celular. O problema aparece depois. Achar aquele link de três
semanas atrás é rolar a conversa sem fim, e links, fotos, ideias e arquivos ficam todos misturados.

Este projeto mantém o hábito de **mandar no grupo** e resolve o **encontrar depois**:

- cada mensagem vira uma nota, classificada automaticamente;
- links ganham prévia com título e imagem, e ficam separados por site (Instagram, YouTube...);
- fotos, áudios e documentos são baixados para o seu computador;
- uma busca encontra palavras no texto, no nome dos arquivos e até no título das prévias.

### Princípios

O projeto segue uma constituição ([`.specify/memory/constitution.md`](.specify/memory/constitution.md)).
Os pontos que mais importam para quem usa:

- **Tudo local.** As notas ficam num PostgreSQL no seu computador, e o painel só abre no próprio
  computador (`127.0.0.1`). Não há nuvem, nem LLM, nem API paga.
- **Rede só quando precisa.** O sistema só fala com o Telegram e, se você deixar ligado, com os
  sites dos links (para buscar a prévia). Dá para desligar as prévias.
- **Regras antes de inteligência artificial.** A classificação é feita por regras previsíveis e
  testadas, não por modelos.
- **Nada some.** Uma mensagem que falha ao ser processada aparece no painel com o erro.
- **Só APIs oficiais.** O bot usa a Bot API. A sincronização usa a API oficial do Telegram com a
  sua conta, **só para leitura** do grupo configurado.

---

## O que ele faz

| Recurso | Como funciona |
|---|---|
| **Captura automática** | Um bot no grupo transforma cada mensagem sua em nota, na hora. Editar a mensagem atualiza a nota. |
| **9 tipos** | Texto, link, foto, áudio, vídeo, documento, localização, contato e outro. |
| **Links por site** | Cada link vira um cartão com título, descrição e miniatura, agrupado pelo site. Uma lista de links colada do WhatsApp vira um cartão por link, com a data e o autor de cada linha. |
| **Mídia local** | Fotos, áudios e documentos de até 20 MB vão para `data/media`, com botão **Baixar**. |
| **Tags** | Escreva `#receita` ou `#trabalho` na mensagem e a nota ganha a tag. |
| **Busca** | Ignora maiúsculas e acentos e procura pelo começo das palavras. Procura no texto, nos nomes de arquivo, nas prévias, nos autores e nos endereços dos links. |
| **Período** | Filtro **de / até** por data, com atalhos Hoje, 7 dias e 30 dias. |
| **Linha do tempo** | A aba **Todas** mostra tudo agrupado por dia: Hoje, Ontem, 5 de novembro... |
| **Sincronizar** | Um clique traz tudo o que você mandou desde a última nota salva, mesmo com o bot desligado por dias. |
| **Importar** | Também aceita a exportação JSON do Telegram Desktop. |
| **Backup diário** | O painel faz um backup do banco por dia e guarda os 7 mais recentes. |

O painel tem tema escuro (segue o tema claro do sistema) e atalhos: `/` ou `Ctrl+K` para buscar,
`Esc` para limpar a busca ou fechar a foto ampliada.

---

## Como funciona

```text
 Você ──manda──▶ Grupo do Telegram
                     │
        ┌────────────┴─────────────┐
        │ ao vivo                  │ sob demanda (botão Sincronizar)
        ▼                          ▼
  Bot (Bot API)          Cliente oficial (MTProto, só leitura)
        │                          │
        └──────────┬───────────────┘
                   ▼
     Regras: tipo, links, site, tags, download
                   │
                   ▼
   PostgreSQL local  +  data/media (arquivos)
                   │
                   ▼
   Painel web em http://127.0.0.1:8000  (busca, filtros, prévias, backup)
```

São só dois processos: o **bot** (`notas.bot`), que captura ao vivo, e o **painel**
(`notas.painel`), que mostra as notas, busca as prévias, sincroniza e faz o backup.

---

## Requisitos

- **Windows 10 ou 11.** O código é Python e roda em outros sistemas, mas os atalhos
  (`iniciar.cmd`, início automático e a pasta Downloads) foram feitos para Windows.
- **Python 3.12 ou mais novo**, gerenciado pelo [uv](https://docs.astral.sh/uv/).
- **PostgreSQL 15 ou mais novo** rodando no próprio computador (testado com o 18), com a
  extensão `unaccent`, que já vem no instalador oficial.
- Uma **conta no Telegram** e um **grupo** que será o caderno.

---

## Instalação

### 1. Instale o uv e o PostgreSQL

```powershell
winget install --id=astral-sh.uv -e
winget install --id=PostgreSQL.PostgreSQL.18 -e   # ou o instalador de postgresql.org
```

Durante a instalação do PostgreSQL, anote a senha do usuário `postgres`. Depois, crie o banco:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres telegram
```

### 2. Baixe o projeto e instale as dependências

```powershell
git clone https://github.com/ricardo-rals/notas-telegram.git
cd notas-telegram
uv sync
```

### 3. Crie o bot e prepare o grupo

1. No Telegram, fale com o **@BotFather**: envie `/newbot`, escolha um nome e **guarde o token**.
2. Ainda no @BotFather: `/setprivacy` → escolha o bot → **Disable**. Sem isso, o bot não vê as
   mensagens do grupo.
3. Crie um grupo (ou use um que já tem), adicione o bot e o deixe como **administrador**.
4. O grupo precisa ser um **supergrupo**, com ID começando em `-100`. Se não for, torne-o público
   por um instante (Editar → Tipo de grupo → Público) e volte para privado: ele vira supergrupo.
5. Não poste como "administrador anônimo": essas mensagens não têm autor e são ignoradas.

### 4. Descubra os IDs do grupo e o seu

Com o bot **parado**, mande qualquer mensagem no grupo e rode (troque `SEU_TOKEN`):

```powershell
(Invoke-RestMethod "https://api.telegram.org/botSEU_TOKEN/getUpdates").result.message |
  Select-Object @{n='grupo';e={$_.chat.id}}, @{n='tipo';e={$_.chat.type}}, @{n='voce';e={$_.from.id}}
```

`grupo` vai em `ALLOWED_CHAT_ID` (deve começar com `-100` e o tipo deve ser `supergroup`), e
`voce` vai em `ALLOWED_USER_ID`.

### 5. Configure o `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Preencha pelo menos `TELEGRAM_BOT_TOKEN`, `ALLOWED_CHAT_ID`, `ALLOWED_USER_ID` e
`DATABASE_URL` (troque `SENHA` pela senha do `postgres`). As outras opções estão em
[Configuração](#configuração). O `.env` **nunca** vai para o Git.

### 6. Crie as tabelas

```powershell
uv run --env-file .env alembic upgrade head
```

Rode esse comando de novo sempre que atualizar o código.

### 7. Comece a usar

Dê dois cliques em **`iniciar.cmd`**: o bot e o painel sobem, cada um numa janela minimizada.
Abra **http://127.0.0.1:8000** e mande algo no grupo.

Se preferir usar dois terminais:

```powershell
uv run --env-file .env python -m notas.bot      # terminal 1
uv run --env-file .env python -m notas.painel   # terminal 2
```

### 8. (Opcional) Ative o botão Sincronizar

O bot só recebe mensagens enquanto está rodando (o Telegram guarda as pendentes por cerca de
24 h). Para trazer o que ficou para trás com um clique:

1. Em **https://my.telegram.org** → *API development tools*, crie um app e copie o **api_id** e
   o **api_hash** para `TELEGRAM_API_ID` e `TELEGRAM_API_HASH` no `.env`.
2. Faça o login **uma vez** e digite o telefone e o código que o Telegram mandar:

   ```powershell
   uv run --env-file .env python -m notas.sincronizacao login
   ```

A sessão fica em `%LOCALAPPDATA%\notas-telegram\telegram.session`, fora do projeto. O cliente
só **lê** o grupo configurado: nunca envia, edita ou apaga mensagens, nem lê outros chats.
Também dá para sincronizar pelo terminal: `uv run --env-file .env python -m notas.sincronizacao`.

### 9. (Opcional) Iniciar junto com o Windows

```powershell
uv run python -m notas.servico instalar      # cria o atalho na pasta Inicializar
uv run python -m notas.servico desinstalar   # remove
```

---

## Usando o painel

- **Barra lateral:** as categorias que você usa, com as contagens. Mais abaixo ficam as tags.
- **Todas:** a linha do tempo, com um cartão por item, agrupada por dia.
- **Link:** um botão por site (`instagram.com`, `youtube.com`...). Subdomínios como `www.` e
  `m.` contam como o mesmo site.
- **Documento:** botões por tipo de arquivo (PDF, planilhas, textos, apresentações...).
- **Busca:** digite no topo. "lui" encontra "Luis" e "Luiz", e "reuniao" encontra "Reunião".
- **Período:** campos **de / até**. Se o "até" ficar vazio, vale até hoje.
- **Notas novas:** com o painel aberto, aparece o aviso "N notas novas · mostrar", sem recarregar
  o que você está vendo.
- **Falhas:** se alguma mensagem não puder ser processada, um aviso vermelho no topo leva a ela.
- **Importar:** lista as exportações do Telegram Desktop encontradas em `Downloads`, além da
  sincronização e do estado do backup.

---

## Configuração

Todas as opções ficam no `.env` (modelo em [`.env.example`](.env.example)).

| Variável | Obrigatória | Para que serve |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | sim (bot) | Token do @BotFather. |
| `ALLOWED_CHAT_ID` | sim | ID do grupo-caderno (`-100...`). Mensagens de outros chats são ignoradas. |
| `ALLOWED_USER_ID` | sim | Seu ID. Mensagens de outras pessoas são ignoradas. |
| `DATABASE_URL` | sim | `postgresql+psycopg://postgres:SENHA@127.0.0.1:5432/telegram`. Só aceita `127.0.0.1` ou `localhost`. |
| `MEDIA_DIR` | não | Pasta dos arquivos baixados (padrão `data/media`, ignorada pelo Git). |
| `PAINEL_PORT` | não | Porta do painel (padrão `8000`). O endereço é sempre `127.0.0.1`. |
| `PREVIAS_LINKS` | não | `1` (padrão) busca título e miniatura dos links; `0` não acessa nenhum site. |
| `BACKUP_DIR` | não | Pasta dos backups (padrão `%LOCALAPPDATA%\notas-telegram\backups`). Precisa ficar fora do projeto. |
| `BACKUP_MANTER` | não | Quantos backups guardar (padrão `7`). |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | só para sincronizar | Credenciais de my.telegram.org. |
| `TEST_DATABASE_URL` | só para testes | Banco dos testes. O nome **precisa** terminar em `_test`, porque ele é apagado e recriado. |
| `PG_BIN` | não | Pasta do `pg_dump`, se não for encontrada sozinha. |

---

## Backup e restauração

Com o painel aberto, o banco é copiado uma vez por dia com `pg_dump` e os 7 backups mais
recentes são guardados. A página **Importar** mostra o último backup e avisa se ele estiver
atrasado. Para fazer um backup na hora:

```powershell
uv run --env-file .env python -m notas.backup
```

Para restaurar, feche o bot e o painel e rode:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" --clean --if-exists -h 127.0.0.1 -U postgres -d telegram "CAMINHO\notas-AAAAMMDD-HHMMSS.dump"
```

A pasta `data/media` não entra no backup diário: os arquivos podem ser baixados de novo pelo
link da mensagem. Se quiser, copie-a junto.

### Vindo de uma versão antiga (SQLite)

As primeiras versões gravavam num arquivo SQLite. Para levar essas notas ao PostgreSQL, uma
vez e com o banco novo vazio:

```powershell
uv run --env-file .env alembic upgrade head
uv run --env-file .env python -m notas.migrar_sqlite   # o SQLite antigo fica intacto
```

---

## Solução de problemas

| Sintoma | O que fazer |
|---|---|
| O bot não registra nada | Confira se `/setprivacy` está em **Disable** e se o bot é membro (de preferência admin) do grupo. Se você mudou o privacy mode depois de adicionar o bot, remova-o e adicione de novo. |
| `getUpdates` volta vazio | O bot está rodando e já consumiu as mensagens. Pare o bot e mande uma mensagem nova. |
| "ID precisa começar com -100" | O grupo ainda não é supergrupo. Veja o passo 3. |
| "Banco desatualizado" | Rode `uv run --env-file .env alembic upgrade head`. |
| "Não consegui conectar ao PostgreSQL" | O serviço do PostgreSQL está parado. Confira em `services.msc` ou a `DATABASE_URL`. |
| Botão Sincronizar dá erro 404 | O painel aberto é de uma versão anterior. Feche-o e abra de novo pelo `iniciar.cmd`. |
| "Configure TELEGRAM_API_ID..." ou "Faça o login..." | Siga o passo 8. |
| Prévia indisponível em links do Instagram | Alguns sites negam a prévia sem login. O link continua funcionando. |

---

## Desenvolvimento

O projeto é desenvolvido com o [Spec Kit](https://github.com/github/spec-kit): cada
funcionalidade tem spec, plano e tarefas em [`specs/`](specs/). As regras de parsing, os
sites e o acesso a dados são escritos com testes antes do código.

```powershell
uv run --env-file .env pytest                  # suíte completa (cerca de 330 testes)
uv run --env-file .env pytest -m "not lento"   # sem os testes de desempenho
```

Os testes usam só mensagens inventadas e um banco separado (`TEST_DATABASE_URL`); nenhum acessa
a internet.

```text
src/notas/
├── bot.py            # captura ao vivo (Bot API, long polling)
├── sincronizacao.py  # botão Sincronizar (MTProto oficial, só leitura)
├── importacao.py     # exportação JSON do Telegram Desktop
├── regras.py         # classificação, links, sites, tags, período (sem rede, sem banco)
├── repositorio.py    # consultas e gravação no PostgreSQL
├── previas.py        # título/miniatura dos links (sem acessar a rede local)
├── painel.py         # FastAPI + Jinja2 + HTMX, só em 127.0.0.1
├── backup.py         # pg_dump diário
├── servico.py        # início automático com o Windows
└── templates/, static/
alembic/versions/     # esquema do banco
specs/                # spec, plano e tarefas de cada funcionalidade (001 a 010)
tests/                # pytest
```

| Fatia | Funcionalidade |
|---|---|
| 001 | Captura, classificação, painel, importação |
| 002 | Abas por tipo e botões por site |
| 003 | Cartões de link com prévia, botão Baixar |
| 004 | Redesenho do painel |
| 005 | Tags por hashtag e tipos de documento |
| 006 | Backup, `iniciar.cmd`, início automático |
| 007 | PostgreSQL |
| 008 | Busca ampliada e filtro por data |
| 009 | Sincronização com um clique |
| 010 | Aba Todas como linha do tempo |

---

## Limitações conhecidas

- Vídeos não são baixados (só a legenda e o link), e arquivos acima de 20 MB também não, por
  limite da Bot API.
- Edições feitas em mensagens antigas com o bot desligado não são reaplicadas pela
  sincronização nem pela importação.
- A busca encontra o começo das palavras, mas não grafias diferentes ("Luiz" não acha "Luis").
- O painel só abre no próprio computador. O acesso pelo celular exigiria mudar a constituição.
