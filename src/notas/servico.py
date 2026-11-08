"""Início automático com o Windows (006).

`uv run python -m notas.servico instalar` cria `notas-telegram.cmd` na pasta Inicializar do
usuário, que só chama o `iniciar.cmd` deste projeto; `desinstalar` apaga. Nada mais é alterado.
"""

import os
import sys
from pathlib import Path

from notas.config import RAIZ_REPO

ATALHO = "notas-telegram.cmd"


def pasta_inicializar() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def instalar(pasta: Path | None = None) -> Path:
    destino = (pasta or pasta_inicializar()) / ATALHO
    destino.write_text(f'@echo off\r\ncall "{RAIZ_REPO / "iniciar.cmd"}"\r\n', encoding="utf-8")
    return destino


def desinstalar(pasta: Path | None = None) -> bool:
    destino = (pasta or pasta_inicializar()) / ATALHO
    if not destino.exists():
        return False
    destino.unlink()
    return True


def main() -> None:
    acao = sys.argv[1] if len(sys.argv) == 2 else ""
    if acao == "instalar":
        print(f"Início automático instalado: {instalar()}")
    elif acao == "desinstalar":
        print("Início automático removido." if desinstalar() else "Não havia início automático instalado.")
    else:
        raise SystemExit("uso: python -m notas.servico instalar|desinstalar")


if __name__ == "__main__":
    main()
