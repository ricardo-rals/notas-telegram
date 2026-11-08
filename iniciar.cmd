@echo off
rem Sobe o bot e o painel, cada um numa janela minimizada (006). Duplo clique ou: iniciar.cmd
cd /d "%~dp0"
start "notas - bot" /min cmd /c uv run --env-file .env python -m notas.bot
start "notas - painel" /min cmd /c uv run --env-file .env python -m notas.painel
