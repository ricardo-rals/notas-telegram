# Quickstart: Captura de Notas (validação ponta a ponta)

Comandos em PowerShell, na raiz do repositório. Detalhes de rotas e variáveis em
[contracts/](contracts/); do banco em [data-model.md](data-model.md).

## 1. Pré-requisitos

- uv instalado (`uv --version`); o Python 3.12 é baixado pelo uv.
- Bot criado no @BotFather, com `/setprivacy` → **Disable** e adicionado ao grupo-caderno.
- O grupo é supergrupo (o ID começa com `-100`). Seu usuário não posta como admin anônimo.
- IDs do grupo e do seu usuário em mãos.

## 2. Instalação

```powershell
uv sync
Copy-Item .env.example .env   # preencha TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, ALLOWED_USER_ID
uv run --env-file .env alembic upgrade head
```

Esperado: o banco é criado em `DATABASE_PATH`, fora do repositório; `git status` não mostra
`.env`, `data/` nem `*.db`.

## 3. Testes automáticos

```powershell
uv run pytest
```

Esperado: todos passam. Os testes usam só mensagens inventadas em `tests/fixtures/`.

## 4. Captura ao vivo (User Stories 1, 3, 4)

```powershell
uv run --env-file .env python -m notas.bot      # terminal 1
uv run --env-file .env python -m notas.painel   # terminal 2
```

Abra `http://127.0.0.1:8000` e, no grupo, envie:

| Envio | Esperado no painel em até 10 s |
|---|---|
| `comprar pão` | tipo texto |
| `olha https://exemplo.com` | tipo link |
| Foto com legenda | tipo foto, miniatura, legenda como texto |
| Mensagem de voz | tipo áudio, player funcionando |
| PDF pequeno | tipo documento, link para o arquivo |
| PDF > 20 MB | tipo documento, aviso "arquivo acima de 20 MB" |
| Vídeo | tipo vídeo, sem arquivo |
| Localização / contato | coordenadas / nome e telefone |
| Figurinha | tipo outro |
| Editar `comprar pão` → `comprar pão e leite` | mesma nota, texto novo, data de edição |
| Mensagem de outra conta no grupo | nada aparece |

Em `data/media` devem existir só os arquivos da foto, da voz e do PDF pequeno.

## 5. Busca e filtro (User Story 2)

- Busque `PAO` → aparece "comprar pão e leite".
- Filtre por `foto` → só a foto.
- Busca + filtro juntos → interseção.
- Busque `xyzxyz` → "Nenhuma nota encontrada".

## 6. Importação (User Story 5)

No Telegram Desktop: grupo → ⋮ → Exportar histórico, formato **JSON**, com fotos, arquivos e
mensagens de voz.

```powershell
uv run --env-file .env python -m notas.importacao "C:\caminho\da\exportacao"
```

Esperado: as mensagens já capturadas contam como `existentes`; as de outras pessoas como
`ignoradas`. Rodar de novo → `criadas = 0`.

Pelo painel: `http://127.0.0.1:8000/importar`, informe a mesma pasta → mesmas contagens
(todas `existentes`). Clicar de novo enquanto roda → aviso de importação em andamento.

## 7. Painel só local

```powershell
curl.exe -H "Host: exemplo.com" http://127.0.0.1:8000/   # esperado: 400
```

E de outro computador da rede, `http://<ip-da-maquina>:8000` não abre.
