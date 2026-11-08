# Implementation Plan: Backup Automático, Comando Único e Início com o Windows

**Branch**: `006-backup-inicio-automatico` | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)

## Summary

`notas/backup.py`: `fazer_backup` usa `VACUUM INTO` (cópia consistente e compactada, da stdlib
`sqlite3`), `podar` mantém os N mais recentes pelo padrão do nome, `precisa_backup` olha o mais
recente pelo nome. Uma thread do painel (como a das prévias, injetável em `criar_app`) verifica
na partida e a cada hora; o último erro fica numa variável do módulo e aparece em `/importar`.

`iniciar.cmd` na raiz usa `start /min` para abrir os dois processos que já existem.
`notas/servico.py` escreve ou apaga `notas-telegram.cmd` na pasta Inicializar
(`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`), que só chama o `iniciar.cmd`.

## Technical Context

Python 3.12, stdlib (`sqlite3`, `threading`); sem dependência nova; sem migração.
Config: `BACKUP_DIR`, `BACKUP_MANTER`. Testes: pytest com `tmp_path`, relógio injetado; a pasta
Inicializar é injetada nos testes (nenhum teste toca a do usuário).

## Constitution Check

| Princípio | Situação |
|---|---|
| I. Tudo local | ✅ cópia no mesmo disco, nenhuma rede |
| IV. Privacidade | ✅ backups fora do repositório (validado em `config`) |
| V. Testes antes | ✅ backup, poda, agenda, config e instalar/desinstalar |
| VI. Simplicidade | ✅ nenhum processo novo: backup é thread do painel; `iniciar.cmd` só abre os dois processos que já existem e termina |
| VIII. Falha visível | ✅ erro de backup no log e na página Importar |

## Project Structure

```text
iniciar.cmd                     # novo
src/notas/backup.py             # novo: fazer_backup, podar, precisa_backup, ultimo_backup, thread, main
src/notas/servico.py            # novo: instalar/desinstalar o atalho de inicialização
src/notas/config.py             # backup_dir, backup_manter
src/notas/painel.py             # inicia a thread; /importar mostra o estado do backup
src/notas/templates/importar.html
.env.example, README.md
tests/test_backup.py, test_config.py, test_painel.py
```

## Complexity Tracking

Sem violações.
