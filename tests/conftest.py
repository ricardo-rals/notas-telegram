import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from notas.config import Config, achar_pg_bin

FIXTURES = Path(__file__).parent / "fixtures"
CHAT = -1001234567890
DONO = 111
TABELAS = ("tag", "previa", "link", "importacao", "nota")


def carregar_fixture(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


def url_de_teste() -> str:
    """Só um banco cujo nome termina em `_test`, nunca o DATABASE_URL (FR-005 da 007)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.exit("Defina TEST_DATABASE_URL (rode: uv run --env-file .env pytest)", returncode=2)
    u = make_url(url)
    if not (u.database or "").endswith("_test") or url == os.environ.get("DATABASE_URL"):
        pytest.exit("TEST_DATABASE_URL precisa ser um banco terminado em _test e diferente de DATABASE_URL",
                    returncode=2)
    if u.host not in ("127.0.0.1", "localhost", "::1"):
        pytest.exit("TEST_DATABASE_URL precisa ser local", returncode=2)
    return url


def recriar_banco(url: str) -> None:
    """Apaga e cria de novo o banco de teste (nunca outro: `url_de_teste` garante o `_test`)."""
    u = make_url(url)
    admin = create_engine(u.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{u.database}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{u.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def url_banco():
    from notas.db import migrar

    url = url_de_teste()
    recriar_banco(url)
    migrar(url)
    return url


@pytest.fixture
def config_teste(tmp_path, url_banco) -> Config:
    return Config(
        chat_id=CHAT,
        user_id=DONO,
        database_url=url_banco,
        media_dir=tmp_path / "media",
        painel_port=8000,
        previas_links=False,  # nenhum teste acessa a rede pela thread de prévias
        backup_dir=tmp_path / "backups",
        pg_bin=achar_pg_bin(),
    )


@pytest.fixture
def engine(config_teste):
    from notas.db import criar_engine

    eng = criar_engine(config_teste.database_url)
    yield eng
    with eng.begin() as c:
        c.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY CASCADE"))
    eng.dispose()


@pytest.fixture
def sessao(engine):
    with Session(engine) as s:
        yield s
