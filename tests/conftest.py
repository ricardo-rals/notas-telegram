import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from notas.config import Config

FIXTURES = Path(__file__).parent / "fixtures"
CHAT = -1001234567890
DONO = 111


def carregar_fixture(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


@pytest.fixture
def config_teste(tmp_path) -> Config:
    return Config(
        chat_id=CHAT,
        user_id=DONO,
        database_path=tmp_path / "notas.db",
        media_dir=tmp_path / "media",
        painel_port=8000,
    )


@pytest.fixture
def engine(config_teste):
    from notas.db import criar_engine, migrar

    migrar(config_teste.database_path)
    eng = criar_engine(config_teste.database_path)
    yield eng
    eng.dispose()


@pytest.fixture
def sessao(engine):
    with Session(engine) as s:
        yield s
