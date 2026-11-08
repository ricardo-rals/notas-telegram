"""Configuração lida de variáveis de ambiente (o .env é carregado por `uv run --env-file .env`)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]


class ErroConfig(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    chat_id: int
    user_id: int
    database_path: Path
    media_dir: Path
    painel_port: int
    token: str | None = None
    previas_links: bool = True  # busca título/miniatura dos links (Princípio I, item b)
    backup_dir: Path | None = None  # None = "backups" ao lado do banco (006)
    backup_manter: int = 7


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

    db = valor("DATABASE_PATH")
    if db:
        database_path = Path(db)
    else:
        base = valor("LOCALAPPDATA")
        database_path = (Path(base) if base else Path.home() / ".local" / "share") / "notas-telegram" / "notas.db"
    if _dentro(database_path, RAIZ_REPO):
        raise ErroConfig("DATABASE_PATH precisa ficar fora do repositório (Princípio IV)")

    media_dir = Path(valor("MEDIA_DIR") or "data/media")
    if not media_dir.is_absolute():
        media_dir = RAIZ_REPO / media_dir
    if _dentro(media_dir, RAIZ_REPO) and not _dentro(media_dir, RAIZ_REPO / "data"):
        raise ErroConfig("MEDIA_DIR dentro do repositório precisa estar em data/ (ignorada pelo Git)")

    previas = valor("PREVIAS_LINKS") or "1"
    if previas not in ("0", "1"):
        raise ErroConfig("PREVIAS_LINKS precisa ser 0 ou 1")

    backup_dir = Path(valor("BACKUP_DIR") or database_path.parent / "backups")
    if _dentro(backup_dir, RAIZ_REPO):
        raise ErroConfig("BACKUP_DIR precisa ficar fora do repositório (Princípio IV)")
    backup_manter = inteiro("BACKUP_MANTER", 7)
    if backup_manter < 1:
        raise ErroConfig("BACKUP_MANTER precisa ser pelo menos 1")

    return Config(
        chat_id=inteiro("ALLOWED_CHAT_ID"),
        user_id=inteiro("ALLOWED_USER_ID"),
        database_path=database_path,
        media_dir=media_dir,
        painel_port=inteiro("PAINEL_PORT", 8000),
        token=token,
        previas_links=previas == "1",
        backup_dir=backup_dir,
        backup_manter=backup_manter,
    )
