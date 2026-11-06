# Research: Categorias por Tipo e Sites dos Links

Sem `NEEDS CLARIFICATION` no Technical Context; as decisões abaixo fecham as escolhas abertas.

## R1. Domínio registrável (FR-005)

- **Decision**: dependência `publicsuffixlist` (pura Python, sem dependências próprias, traz
  `public_suffix_list.dat` dentro do pacote; versão = data da lista, ex. `1.1.2.20261105`).
  `PublicSuffixList().privatesuffix(host)` devolve o domínio registrável. A instância é criada
  uma vez no import do módulo.
- **Rationale**: a regra precisa da lista pública de sufixos (`.com.br`, `.co.uk`, seções
  privadas como `github.io`, curingas e exceções). A lista é dado, não código: só pode vir de
  um arquivo. O pacote entrega o arquivo e o algoritmo testados; não acessa rede em tempo de
  execução (o `update.py` dele só roda se chamado à mão). Atualizar a lista = atualizar o
  pacote no `uv.lock`, coerente com "atualizada só quando o sistema é atualizado".
- **Comportamento verificado** (versão 1.1.2.20261105):

  | entrada | `privatesuffix` |
  |---|---|
  | `www.youtube.com`, `music.youtube.com` | `youtube.com` |
  | `pt.wikipedia.org` | `wikipedia.org` |
  | `folha.uol.com.br` | `uol.com.br` |
  | `exemplo.co.uk` | `exemplo.co.uk` |
  | `fulano.github.io` | `fulano.github.io` |
  | `com.br`, `localhost` | `None` |
  | `192.168.0.1` | `0.1` ← errado; IP precisa ser tratado antes |
  | `exemplo.desconhecido` | `exemplo.desconhecido` (TLD desconhecido = sufixo de 1 nível) |

- **Alternatives considered**:
  - `tldextract`: faz download da lista na primeira execução por padrão (viola Princípio I a
    menos que configurado) e traz `requests`, `filelock`, `idna`.
  - Copiar `public_suffix_list.dat` para o repositório + ~30 linhas de algoritmo: mesmo
    resultado, mas a atualização da lista vira tarefa manual e o algoritmo (curingas,
    exceções) passa a ser nosso para manter.
  - Só remover `www.`/`m.`: descartado na clarificação (opção C).

## R2. Normalização do host antes da lista

- **Decision**: função `site(url) -> str | None` em `regras.py`, nesta ordem:
  1. `urllib.parse.urlsplit`; URL sem esquema ganha `http://` antes (entidades do Telegram
     reconhecem `exemplo.com` sem `https://`).
  2. `hostname` (já tira porta, usuário e colchetes de IPv6, e põe em minúsculas). Vazio → `None`.
  3. Remove ponto final (`exemplo.com.`).
  4. IP (`ipaddress.ip_address`) → o próprio IP.
  5. Sem ponto (`localhost`) → o próprio host.
  6. Labels `xn--` → forma legível com o codec `idna` da stdlib, label a label; falha no
     decode mantém o label como veio. Assim `xn--bcher-kva.de` e `bücher.de` viram o mesmo site.
  7. `privatesuffix(host)`; `None` (host é só sufixo, ex. `com.br`) → `None`.
- **Rationale**: tudo stdlib menos o passo 7; cada passo corresponde a um caso de borda da spec
  e vira um teste parametrizado (SC-002).
- **Alternatives considered**: regex própria para host: reinventa `urlsplit` e erra em IPv6 e
  credenciais na URL.

## R3. De onde vêm as URLs de uma nota

- **Decision**: os adaptadores existentes passam a preencher `MensagemNormalizada.urls`
  (tupla, ordem de aparição, sem repetição):
  - Bot API: entidade `text_link` → `url`; entidade `url` → trecho do texto pelo offset/length
    (contados em UTF-16, então o recorte é feito sobre `texto.encode("utf-16-le")`).
  - Exportação: `text_entities` do tipo `text_link` → `href`; do tipo `link` → `text`.
  - Sem entidades: regex `URL` que já existe em `regras.py`.
  - `sites_da_nota(m)` = conjunto de `site(u)` para cada URL; nenhum site válido → `{""}`
    (sentinela "Sem site identificado", ver data-model).
- **Rationale**: `classificar` já decide "link" pelas entidades; tirar as URLs da mesma fonte
  garante que toda nota de link tenha o mesmo conjunto de URLs que a fez ser link. O texto
  guardado não contém o endereço de um `text_link`, então só o texto não basta.
- **Alternatives considered**: extrair só do campo `texto` com regex: perde `text_link` e
  domínios sem esquema; quebraria SC-001 em parte dos links.

## R4. Notas já guardadas (FR-011)

- **Decision**: toda nota da 001 tem `bruto` (o JSON original), inclusive as ao vivo e as
  falhas. A migração Alembic `0002` cria a tabela `nota_site` e chama
  `repositorio.reclassificar_sites(conn)`, que para cada nota `tipo='link'`:
  1. `json.loads(bruto)` → `normalizar_bot_api` (origem `ao_vivo`) ou `normalizar_exportacao`
     (origem `importacao`) → `sites_da_nota`;
  2. se `bruto` falta ou não normaliza, usa a regex sobre `texto`;
  3. apaga as linhas `nota_site` da nota e insere as novas.
  Tudo numa transação; rodar de novo gera o mesmo resultado (FR-011).
- **Rationale**: o dono já roda `alembic upgrade head` ao atualizar (o painel e o bot recusam
  banco desatualizado), então a classificação acontece "sem intervenção" e sem comando novo.
  Reaproveitar os adaptadores garante que nota antiga e nova caiam no mesmo site (FR-012).
- **Alternatives considered**:
  - Comando separado `python -m notas.sites`: mais um passo que o dono pode esquecer.
  - Calcular no início do painel: trabalho repetido a cada partida e escrita no banco por um
    processo que hoje só lê notas.
- **Nota**: a migração importa código da aplicação. `ponytail:` se `regras` mudar a ponto de a
  `0002` não rodar mais em banco novo, congelar a função dentro da migração.

## R5. Gravar sites na captura, edição e importação (FR-012)

- **Decision**: `salvar_ao_vivo` e `salvar_importada` recebem `sites` e gravam na mesma
  transação da nota. O upsert ao vivo passa a usar `RETURNING id` (SQLite ≥ 3.35, já presente
  no Python 3.12) e substitui as linhas da nota (apaga e insere). Tipo diferente de link →
  nenhuma linha. `registrar_falha` não mexe em `nota_site`: numa nota existente ela mantém o
  conteúdo, então os sites continuam valendo; numa nota nova o tipo é `outro`.
- **Rationale**: mesma unidade de trabalho = nenhuma nota de link fica sem site, mesmo se o
  processo morrer no meio.
- **Alternatives considered**: trigger SQL: não sabe calcular domínio registrável.

## R6. Abas e botões no painel

- **Decision**: abas e botões são links `<a href="/?tipo=…&site=…&q=…">` com
  `aria-current="page"` no ativo. Ficam dentro do fragmento que o HTMX já atualiza a cada 10 s,
  então contagens e lista ficam em sincronia. O formulário de busca leva `tipo` e `site` como
  campos ocultos. O `<select>` de tipo sai.
- Contagens: uma consulta `GROUP BY tipo` + uma de `situacao='falha'`; botões: uma consulta
  `GROUP BY site` sobre `nota_site` junto com `nota.tipo='link'`, ordenada por quantidade
  decrescente e nome. Nenhuma depende de `q` (FR-002).
- **Rationale**: HTML padrão funciona pelo teclado e com recarregar/voltar (FR-009) sem JS novo.
- **Alternatives considered**: abas com JS próprio: estado fora da URL, mais código.

## R7. Desempenho (SC-003, SC-004)

- **Decision**: índice `nota_site (site, nota_id)` e chave primária `(nota_id, site)`. Filtro
  por site = `nota.id IN (SELECT nota_id FROM nota_site WHERE site = :s)`.
- **Rationale**: com 10.000 notas as três consultas de contagem e a lista ficam na casa de
  milissegundos; o teste `lento` existente de 10.000 notas ganha a variação com site.
  Reclassificar 10.000 notas = 10.000 `json.loads` + lookup, bem abaixo de 1 minuto.
