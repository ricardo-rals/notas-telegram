"""Engine SQLite, modelos e verificação de migração. O esquema real vem de alembic/versions."""

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, Integer, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from notas.config import RAIZ_REPO

TIPOS = ("texto", "link", "foto", "audio", "video", "documento", "localizacao", "contato", "outro")
SITUACOES = ("ok", "grande_demais", "sem_arquivo", "falha")


def agora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Base(DeclarativeBase):
    pass


class Nota(Base):
    __tablename__ = "nota"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int]
    message_id: Mapped[int]
    enviada_em: Mapped[str]
    editada_em: Mapped[str | None]
    tipo: Mapped[str]
    texto: Mapped[str] = mapped_column(String, default="")
    link: Mapped[str]
    arquivo_caminho: Mapped[str | None]
    arquivo_nome: Mapped[str | None]
    arquivo_tamanho: Mapped[int | None]
    situacao: Mapped[str]
    erro: Mapped[str | None]
    origem: Mapped[str]
    bruto: Mapped[str | None]
    criada_em: Mapped[str] = mapped_column(String, default=agora)


class Importacao(Base):
    __tablename__ = "importacao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pasta: Mapped[str]
    via: Mapped[str]
    status: Mapped[str]
    iniciada_em: Mapped[str] = mapped_column(String, default=agora)
    terminada_em: Mapped[str | None]
    criadas: Mapped[int] = mapped_column(default=0)
    existentes: Mapped[int] = mapped_column(default=0)
    ignoradas: Mapped[int] = mapped_column(default=0)
    falhas: Mapped[int] = mapped_column(default=0)
    erro: Mapped[str | None]


def criar_engine(caminho: Path) -> Engine:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{caminho}")

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def _alembic(caminho: Path) -> AlembicConfig:
    cfg = AlembicConfig(str(RAIZ_REPO / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_REPO / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{caminho}")
    return cfg


def migrar(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(_alembic(caminho), "head")


def exigir_revisao_atual(engine: Engine) -> None:
    head = ScriptDirectory.from_config(_alembic(Path(engine.url.database))).get_current_head()
    with engine.connect() as conn:
        atual = MigrationContext.configure(conn).get_current_revision()
    if atual != head:
        raise SystemExit(
            f"Banco desatualizado (revisão {atual}, esperado {head}). "
            "Rode: uv run --env-file .env alembic upgrade head"
        )
