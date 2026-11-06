<!--
Sync Impact Report
- Versão: template (sem versão) → 1.0.0 (ratificação inicial)
- Princípios: 5 placeholders do template → 8 princípios definidos (I a VIII)
- Seções adicionadas: Restrições Técnicas, Fluxo de Desenvolvimento
- Seções removidas: nenhuma
- Templates: plan/spec/tasks leem a constituição em tempo de execução; nada alterado aqui
- TODOs adiados: nenhum
-->

# Notas Telegram Constitution

## Core Principles

### I. Tudo Local

O serviço MUST rodar inteiramente no computador do dono. MUST NOT usar LLM nem qualquer API
paga. Acesso à rede é permitido apenas para (a) falar com o Telegram e (b) abrir os links
recebidos para obter título e miniatura. O item (b) MUST poder ser desligado na configuração;
com ele desligado, nenhuma requisição além do Telegram sai da máquina.

Razão: custo zero, privacidade e funcionamento sem dependência de terceiros.

### II. Regra Antes de Modelo

Tudo que pode ser resolvido por regra determinística (tipo de mensagem, extração de URL,
identificação do site) MUST ser resolvido por regra e MUST NOT usar ML. ML só entra onde
uma regra comprovadamente não resolve.

Razão: regras são previsíveis, testáveis e baratas; modelo é o último recurso.

### III. ML com Avaliação Obrigatória

Todo modelo de ML MUST ter:

- conjunto de teste separado, nunca usado em treino;
- baseline para comparação;
- meta numérica declarada no spec da funcionalidade;
- um script que gera `docs/results.md` a partir do conjunto de teste.

Um modelo novo MUST superar o modelo em uso no mesmo conjunto de teste antes de substituí-lo.

Razão: sem medida no mesmo conjunto, "melhorou" é opinião.

### IV. Privacidade

Os dados MUST ficar em um único arquivo SQLite fora do repositório. MUST NOT entrar no Git:
token, banco de dados ou mensagem real. Testes MUST usar apenas mensagens inventadas.
O painel MUST escutar somente em `127.0.0.1`.

Razão: o conteúdo vem de um grupo privado; vazamento não tem volta.

### V. Testes Antes da Implementação

Para parsing de mensagens, regras de site e acesso a dados, os testes MUST ser escritos e
falhar antes da implementação. Outras áreas podem ter testes depois, a critério do spec.

Razão: são as partes onde um erro silencioso corrompe ou perde dados.

### VI. Simplicidade

A arquitetura é: um processo para o bot, um processo para o painel, um arquivo de banco.
Fila, contêiner, serviço externo ou processo adicional MUST NOT ser introduzido sem
necessidade medida e registrada no plano.

Razão: projeto pessoal; cada peça a mais é manutenção sem retorno.

### VII. Só APIs Oficiais

Fontes permitidas: Telegram Bot API e a exportação do Telegram Desktop. WhatsApp MUST entrar
apenas por arquivo exportado. MUST NOT usar clientes não oficiais, userbots ou scraping
de aplicativos de mensagem.

Razão: evita banimento de conta e quebra por mudanças não documentadas.

### VIII. Falha Visível

Toda mensagem que não puder ser processada MUST ser gravada e aparecer no painel junto com
o erro. Nenhuma mensagem MUST NOT ser descartada silenciosamente.

Razão: perda silenciosa é pior que erro; o dono precisa ver e corrigir.

## Restrições Técnicas

- Armazenamento: exatamente um arquivo SQLite, com caminho configurável fora do repositório.
- Rede: apenas Telegram e busca de metadados de links (desligável). Sem LLM, sem API paga.
- Exposição: o painel faz bind só em `127.0.0.1`; nada escuta em interface pública.
- Segredos: token e configuração local ficam fora do Git; o repositório versiona só um
  exemplo de configuração sem valores reais.
- Processos: bot e painel são os únicos processos de longa duração.

## Fluxo de Desenvolvimento

- Cada funcionalidade segue o ciclo do Spec Kit (specify → plan → tasks → implement).
- O `plan.md` MUST conter uma verificação de conformidade com esta constituição; qualquer
  desvio (ex.: nova dependência externa, novo processo) MUST ser justificado com a medida
  que o motivou.
- Specs que envolvem ML MUST declarar conjunto de teste, baseline e meta numérica antes do
  plano (Princípio III).
- Revisão antes de concluir uma tarefa: nenhum dado real, token ou banco no diff; testes de
  parsing, regras de site e acesso a dados passando.

## Governance

Esta constituição prevalece sobre qualquer outra prática do projeto. Emendas são feitas via
`/speckit.constitution`, registradas neste arquivo com nova versão e data.

Versionamento semântico:

- MAJOR: remoção ou redefinição incompatível de um princípio.
- MINOR: princípio ou seção nova, ou orientação materialmente ampliada.
- PATCH: esclarecimentos e ajustes de redação.

Todo `plan.md` e toda revisão de implementação MUST verificar conformidade com os princípios
I a VIII.

**Version**: 1.0.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-05
