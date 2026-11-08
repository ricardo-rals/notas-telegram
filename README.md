# Notas

Caderno local a partir de um grupo privado do Telegram. Tudo que você manda no grupo vira uma
nota num SQLite no seu computador, com busca num painel em `http://127.0.0.1:8000`.
Sem LLM, sem API paga; a rede só é usada para falar com o Telegram e, se ligado, para buscar a
prévia dos links.

## Preparar o Telegram

1. No @BotFather: `/newbot`, guarde o token; depois `/setprivacy` → **Disable**.
2. Adicione o bot ao grupo-caderno. O grupo precisa ser supergrupo (ID começa com `-100`).
3. Não poste como admin anônimo: essas mensagens são ignoradas.

## Rodar

```powershell
uv sync
Copy-Item .env.example .env        # preencha TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, ALLOWED_USER_ID
uv run --env-file .env alembic upgrade head
uv run --env-file .env python -m notas.bot      # terminal 1
uv run --env-file .env python -m notas.painel   # terminal 2
```

Mensagens perdidas (computador desligado por mais de ~24 h) entram pela exportação JSON do
Telegram Desktop, pelo painel em `/importar` ou com:

```powershell
uv run --env-file .env python -m notas.importacao "C:\caminho\da\exportacao"
```

## Abas e sites

O painel tem uma aba por tipo de nota, cada uma com a sua contagem. Na aba **Link**, há um botão
para cada site, agrupado pelo domínio principal: `www.`, `m.`, `music.youtube.com` etc. contam como
`youtube.com`, e `folha.uol.com.br` conta como `uol.com.br`. O domínio principal sai da lista
pública de sufixos, que vem dentro do pacote `publicsuffixlist` e não é baixada em execução.

Depois de atualizar o código, rode de novo `uv run --env-file .env alembic upgrade head`; é ele
que classifica as notas já guardadas. Para atualizar a lista de sufixos:

```powershell
uv lock --upgrade-package publicsuffixlist; uv sync
```

## Cartões e prévias de links

Cada link de uma mensagem vira um cartão próprio, mesmo quando a mensagem tem vários (por
exemplo, um trecho colado do WhatsApp). Com `PREVIAS_LINKS=1` (padrão), o painel busca em
segundo plano, uma vez por endereço, o título, a descrição e a miniatura que a página declara
para compartilhamento. O que é acessado na rede: só a própria página do link e a imagem que
ela indica, nunca endereços da rede local; a miniatura fica em `data/media/previas/`.
Com `PREVIAS_LINKS=0`, nenhuma requisição é feita e o cartão mostra o endereço.

Instagram e outros sites que exigem login costumam negar a prévia; o cartão então mostra
"prévia indisponível" e continua abrindo o link. Fotos, áudios e documentos têm botão
**Baixar**, que salva com o nome original.

Depois de atualizar o código, rode `uv run --env-file .env alembic upgrade head`.

## Painel

Escuro por padrão (segue o tema claro do Windows). À esquerda, as categorias que você usa, com
as contagens; à direita, os cartões, cada tipo no seu formato. Atalhos: `/` ou `Ctrl+K` busca,
`Esc` limpa a busca e fecha a foto ampliada. Com o painel aberto, notas novas aparecem como um
aviso "N notas novas · mostrar", sem recarregar o que você está vendo. Em **Importar**, as
exportações do Telegram Desktop que estão em `Downloads` aparecem prontas para importar.

## Tags e tipos de arquivo

Escreva `#receita`, `#trabalho` (qualquer palavra) na mensagem ou na legenda: a nota ganha a tag,
que aparece na barra lateral com a contagem e filtra junto com a categoria e a busca. Editar a
mensagem atualiza as tags. Na categoria **Documento**, os botões separam PDF, planilhas, textos,
apresentações, compactados e imagens.

## Iniciar tudo de uma vez

Dois cliques em `iniciar.cmd` sobem o bot e o painel, cada um numa janela minimizada. Para subir
sozinho quando você entrar no Windows:

```powershell
uv run python -m notas.servico instalar      # cria o atalho na pasta Inicializar
uv run python -m notas.servico desinstalar   # remove
```

## Backup

Com o painel aberto, o banco é copiado uma vez por dia para `backups` (ao lado do banco, fora do
repositório), guardando os 7 mais recentes (`BACKUP_DIR`, `BACKUP_MANTER`). A página **Importar**
mostra o último backup e avisa se estiver atrasado. Backup na hora:

```powershell
uv run --env-file .env python -m notas.backup
```

Para restaurar: feche o bot e o painel e copie um `notas-AAAAMMDD-HHMMSS.db` no lugar de `notas.db`.
A pasta `data/media` não entra no backup diário.

## Testes

```powershell
uv run pytest            # tudo
uv run pytest -m "not lento"
```

Roteiros de validação: [001](specs/001-captura-notas/quickstart.md) e [002](specs/002-categorias-sites/quickstart.md) e
[003](specs/003-cartoes-links-previa/quickstart.md).
Princípios do projeto: [.specify/memory/constitution.md](.specify/memory/constitution.md).
