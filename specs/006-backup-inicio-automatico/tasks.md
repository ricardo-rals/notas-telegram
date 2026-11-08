# Tasks: Backup Automático, Comando Único e Início com o Windows

**Tests**: TDD (Princípio V).

## Phase 1: US1 Backup (P1)

- [ ] T001 [US1] Testes de config: `BACKUP_DIR` padrão ao lado do banco, recusado dentro do repositório; `BACKUP_MANTER` padrão 7, recusado < 1 ou não inteiro
- [ ] T002 [US1] `config.py`: `backup_dir`, `backup_manter`. T001 deve passar
- [ ] T003 [US1] `tests/test_backup.py`: cópia íntegra (abre e tem as notas, `PRAGMA integrity_check`); nome `notas-AAAAMMDD-HHMMSS.db`; poda deixa N e não toca em outros arquivos; `precisa_backup` (sem backup, 3 h, 25 h, backup "do futuro"); `rodar_agenda` faz um backup e registra erro sem levantar; `main` imprime o caminho
- [ ] T004 [US1] `src/notas/backup.py`. T003 deve passar
- [ ] T005 [US1] Testes do painel: thread de backup iniciada (injetável); `/importar` mostra a data do último backup, aviso de atrasado/sem backup e o último erro
- [ ] T006 [US1] Painel e template. T005 deve passar

## Phase 2: US2 + US3 Comando único e início automático

- [ ] T007 [US2] Criar `iniciar.cmd` (FR-007)
- [ ] T008 [US3] Testes de `servico.instalar/desinstalar` com pasta injetada: conteúdo aponta para o `iniciar.cmd` do projeto; desinstalar remove; desinstalar sem atalho informa
- [ ] T009 [US3] `src/notas/servico.py`. T008 deve passar

## Phase 3: Polish

- [ ] T010 `.env.example`, README; `uv run pytest`; `python -m notas.backup` numa cópia do banco e restauração conferida
