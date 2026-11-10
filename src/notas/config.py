"""Configuração lida de variáveis de ambiente (o .env é carregado por `uv run --env-file .env`)."""

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

RAIZ_REPO = Path(__file__).resolve().parents[2]


class ErroConfig(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    chat_id: int
    user_id: int
    database_url: str
    media_dir: Path
    painel_port: int
    token: str | None = None
    previas_links: bool = True  # busca título/miniatura dos links (Princípio I, item b)
    backup_dir: Path | None = None  # None = "backups" ao lado do banco (006)
    backup_manter: int = 7
    pg_bin: Path | None = None  # pasta com pg_dump/pg_restore (backup)
    sqlite_antigo: Path | None = None  # SQLite das fatias 001–006, só para migrar_sqlite
    api_id: int | None = None  # MTProto oficial, só leitura (009); my.telegram.org
    api_hash: str | None = None
    telegram_sessao: Path | None = None  # sem ".session"; fora do repositório


HOSTS_LOCAIS = {"127.0.0.1", "localhost", "::1"}


def validar_url(url: str, nome: str) -> str:
    """PostgreSQL só no próprio computador (Princípio IV). A senha nunca vai na mensagem de erro."""
    try:
        u = make_url(url)
    except ArgumentError:
        raise ErroConfig(f"{nome} inválida (esperado postgresql+psycopg://usuario:senha@127.0.0.1:5432/banco)") from None
    if not u.drivername.startswith("postgresql"):
        raise ErroConfig(f"{nome} precisa ser PostgreSQL (postgresql+psycopg://...)")
    if u.host not in HOSTS_LOCAIS:
        raise ErroConfig(f"{nome} precisa apontar para 127.0.0.1 ou localhost (Princípio IV)")
    if not u.database:
        raise ErroConfig(f"{nome} precisa ter o nome do banco")
    return url


def achar_pg_bin(env: Mapping[str, str] = os.environ) -> Path | None:
    if env.get("PG_BIN"):
        return Path(env["PG_BIN"])
    if exe := shutil.which("pg_dump"):
        return Path(exe).parent
    candidatas = sorted(Path(r"C:\Program Files\PostgreSQL").glob("*/bin/pg_dump.exe"), reverse=True)
    return candidatas[0].parent if candidatas else None


def _dentro(caminho: Path, pasta: Path) -> bool:
    return caminho.resolve().is_relative_to(pasta.resolve())


def carregar(exigir_token: bool = False, env: Mapping[str, str] = os.environ) -> Config:
    def valor(nome: str) -> str | None:
        v = env.get(nome, "").strip()
        return v or None

    def inteiro(nome: str, padrao: int | None = None) -> int:
        v = valor(nome)
        if v is None:
            if padrao is None:
                raise ErroConfig(f"variável obrigatória ausente: {nome}")
            return padrao
        try:
            return int(v)
        except ValueError:
            raise ErroConfig(f"{nome} precisa ser um número inteiro") from None

    token = valor("TELEGRAM_BOT_TOKEN")
    if exigir_token and token is None:
        raise ErroConfig("variável obrigatória ausente: TELEGRAM_BOT_TOKEN")

    url = valor("DATABASE_URL")
    if url is None:
        raise ErroConfig("variável obrigatória ausente: DATABASE_URL")
    database_url = validar_url(url, "DATABASE_URL")
    base = valor("LOCALAPPDATA")
    dados = (Path(base) if base else Path.home() / ".local" / "share") / "notas-telegram"
    sqlite_antigo = Path(valor("DATABASE_PATH") or dados / "notas.db")

    media_dir = Path(valor("MEDIA_DIR") or "data/media")
    if not media_dir.is_absolute():
        media_dir = RAIZ_REPO / media_dir
    if _dentro(media_dir, RAIZ_REPO) and not _dentro(media_dir, RAIZ_REPO / "data"):
        raise ErroConfig("MEDIA_DIR dentro do repositório precisa estar em data/ (ignorada pelo Git)")

    previas = valor("PREVIAS_LINKS") or "1"
    if previas not in ("0", "1"):
        raise ErroConfig("PREVIAS_LINKS precisa ser 0 ou 1")

    backup_dir = Path(valor("BACKUP_DIR") or dados / "backups")
    if _dentro(backup_dir, RAIZ_REPO):
        raise ErroConfig("BACKUP_DIR precisa ficar fora do repositório (Princípio IV)")
    backup_manter = inteiro("BACKUP_MANTER", 7)
    if backup_manter < 1:
        raise ErroConfig("BACKUP_MANTER precisa ser pelo menos 1")

    api_id = inteiro("TELEGRAM_API_ID", 0) or None
    api_hash = valor("TELEGRAM_API_HASH")
    telegram_sessao = Path(valor("TELEGRAM_SESSAO") or dados / "telegram")
    if _dentro(telegram_sessao, RAIZ_REPO):
        raise ErroConfig("TELEGRAM_SESSAO precisa ficar fora do repositório (Princípio IV)")

    return Config(
        chat_id=inteiro("ALLOWED_CHAT_ID"),
        user_id=inteiro("ALLOWED_USER_ID"),
        database_url=database_url,
        media_dir=media_dir,
        painel_port=inteiro("PAINEL_PORT", 8000),
        token=token,
        previas_links=previas == "1",
        backup_dir=backup_dir,
        backup_manter=backup_manter,
        pg_bin=achar_pg_bin(env),
        sqlite_antigo=sqlite_antigo,
        api_id=api_id,
        api_hash=api_hash,
        telegram_sessao=telegram_sessao,
    )
