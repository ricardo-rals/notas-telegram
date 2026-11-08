"""Backup diário do banco (006): `uv run --env-file .env python -m notas.backup` faz um na hora.

No painel, uma thread verifica na partida e a cada hora; o banco é copiado com `VACUUM INTO`,
que gera um arquivo SQLite consistente mesmo com o bot gravando ao mesmo tempo.
"""

import logging
import re
import sqlite3
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

from notas.config import ErroConfig, carregar

log = logging.getLogger("notas.backup")

NOME = re.compile(r"^notas-(\d{8}-\d{6})\.db$")
INTERVALO = timedelta(hours=24)
VERIFICAR_A_CADA = 3600  # segundos
ULTIMO_ERRO: dict[str, str | None] = {"mensagem": None}  # mostrado em /importar (Princípio VIII)


def _backups(pasta: Path) -> list[tuple[datetime, Path]]:
    """Só arquivos com o nome de backup, do mais recente para o mais antigo."""
    try:
        itens = [(datetime.strptime(m[1], "%Y%m%d-%H%M%S"), p) for p in pasta.iterdir() if (m := NOME.match(p.name))]
    except OSError:
        return []
    return sorted(itens, reverse=True)


def ultimo_backup(pasta: Path) -> datetime | None:
    b = _backups(pasta)
    return b[0][0] if b else None


def precisa_backup(pasta: Path, agora: datetime) -> bool:
    """Sem backup ou o mais recente com mais de 24 h. Um backup "do futuro" (relógio que voltou)
    não conta como recente."""
    recentes = [d for d, _ in _backups(pasta) if d <= agora]
    return not recentes or agora - recentes[0] >= INTERVALO


def fazer_backup(banco: Path, pasta: Path, manter: int, agora: datetime | None = None) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"notas-{(agora or datetime.now()):%Y%m%d-%H%M%S}.db"
    con = sqlite3.connect(banco)
    try:
        con.execute("VACUUM INTO ?", (str(destino),))
    finally:
        con.close()
    for _, velho in _backups(pasta)[manter:]:
        velho.unlink(missing_ok=True)
    return destino


def verificar(banco: Path, pasta: Path, manter: int, agora: datetime | None = None) -> Path | None:
    """Faz o backup se precisar. Nunca levanta: o erro vai para o log e para ULTIMO_ERRO."""
    agora = agora or datetime.now()
    try:
        if not precisa_backup(pasta, agora):
            return None
        destino = fazer_backup(banco, pasta, manter, agora)
        ULTIMO_ERRO["mensagem"] = None
        log.info("backup feito: %s", destino.name)
        return destino
    except Exception as e:
        ULTIMO_ERRO["mensagem"] = f"{type(e).__name__}: {e}"
        log.warning("backup falhou: %s", type(e).__name__)
        return None


def iniciar_thread(banco: Path, pasta: Path, manter: int) -> threading.Event:
    parar = threading.Event()

    def laco():
        while not parar.is_set():
            verificar(banco, pasta, manter)
            parar.wait(VERIFICAR_A_CADA)

    threading.Thread(target=laco, name="backup", daemon=True).start()
    return parar


def main() -> None:
    try:
        cfg = carregar()
    except ErroConfig as e:
        raise SystemExit(f"Configuração inválida: {e}") from None
    try:
        destino = fazer_backup(cfg.database_path, cfg.backup_dir, cfg.backup_manter)
    except Exception as e:
        print(f"Backup falhou: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Backup feito: {destino}")


if __name__ == "__main__":
    main()
