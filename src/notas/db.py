"""Engine PostgreSQL, modelos e verificação de migração. O esquema real vem de alembic/versions."""

from datetime import UTC, datetime

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import BigInteger, Engine, ForeignKey, Integer, String, create_engine
from sqlalchemy.exc import OperationalError
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
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    enviada_em: Mapped[str]
    editada_em: Mapped[str | None]
    tipo: Mapped[str]
    texto: Mapped[str] = mapped_column(String, default="")
    link: Mapped[str]
    arquivo_caminho: Mapped[str | None]
    arquivo_nome: Mapped[str | None]
    arquivo_tamanho: Mapped[int | None] = mapped_column(BigInteger)
    situacao: Mapped[str]
    erro: Mapped[str | None]
    origem: Mapped[str]
    bruto: Mapped[str | None]
    criada_em: Mapped[str] = mapped_column(String, default=agora)


class Link(Base):
    """Um item por URL distinta de uma nota de link. `site = ''` = "Sem site identificado";
    `url = ''` só no item sentinela de uma nota de link sem URL extraível."""

    __tablename__ = "link"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("nota.id", ondelete="CASCADE"))
    posicao: Mapped[int]
    url: Mapped[str]
    site: Mapped[str]
    data: Mapped[str]
    autor: Mapped[str | None]


class Tag(Base):
    """Hashtag de uma nota, em minúsculas (005)."""

    __tablename__ = "tag"

    nota_id: Mapped[int] = mapped_column(ForeignKey("nota.id", ondelete="CASCADE"), primary_key=True)
    nome: Mapped[str] = mapped_column(String, primary_key=True)


class Previa(Base):
    """Prévia de uma URL (título, descrição, miniatura), compartilhada por todos os itens."""

    __tablename__ = "previa"

    url: Mapped[str] = mapped_column(String, primary_key=True)
    situacao: Mapped[str] = mapped_column(String, default="pendente")  # pendente | ok | indisponivel
    titulo: Mapped[str | None]
    descricao: Mapped[str | None]
    imagem: Mapped[str | None]  # relativo a MEDIA_DIR
    erro: Mapped[str | None]
    definitiva: Mapped[int] = mapped_column(default=0)
    tentativas: Mapped[int] = mapped_column(default=0)
    buscada_em: Mapped[str | None]
    tentar_depois_de: Mapped[str | None]


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


def criar_engine(url: str) -> Engine:
    """PostgreSQL local (constituição 2.0.0). `pool_pre_ping` refaz conexões caídas."""
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


def _alembic(url: str) -> AlembicConfig:
    cfg = AlembicConfig(str(RAIZ_REPO / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_REPO / "alembic"))
    cfg.attributes["url"] = url  # fora de set_main_option: o ConfigParser interpretaria "%" da senha
    return cfg


def migrar(url: str) -> None:
    command.upgrade(_alembic(url), "head")


def exigir_revisao_atual(engine: Engine) -> None:
    head = ScriptDirectory.from_config(_alembic(engine.url.render_as_string(hide_password=False))).get_current_head()
    try:
        with engine.connect() as conn:
            atual = MigrationContext.configure(conn).get_current_revision()
    except OperationalError:
        u = engine.url
        raise SystemExit(f"Não consegui conectar ao PostgreSQL em {u.host}:{u.port or 5432} (banco {u.database}). "
                         "Ele está ligado? Confira DATABASE_URL no .env.") from None
    if atual != head:
        raise SystemExit(
            f"Banco desatualizado (revisão {atual}, esperado {head}). "
            "Rode: uv run --env-file .env alembic upgrade head"
        )
