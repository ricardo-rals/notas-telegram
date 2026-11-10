"""007: copiar as notas do SQLite das fatias 001–006 para o PostgreSQL."""

import json
import sqlite3

import pytest
from sqlalchemy import select, text

from conftest import carregar_fixture
from notas.db import Importacao, Link, Nota, Previa, Tag
from notas.migrar_sqlite import ErroMigracao, migrar

NOTA_001 = """CREATE TABLE nota (id INTEGER PRIMARY KEY, chat_id INTEGER, message_id INTEGER, enviada_em TEXT,
    editada_em TEXT, tipo TEXT, texto TEXT, link TEXT, arquivo_caminho TEXT, arquivo_nome TEXT,
    arquivo_tamanho INTEGER, situacao TEXT, erro TEXT, origem TEXT, bruto TEXT, criada_em TEXT)"""
IMPORTACAO = """CREATE TABLE importacao (id INTEGER PRIMARY KEY, pasta TEXT, via TEXT, status TEXT, iniciada_em TEXT,
    terminada_em TEXT, criadas INTEGER, existentes INTEGER, ignoradas INTEGER, falhas INTEGER, erro TEXT)"""
PREVIA = """CREATE TABLE previa (url TEXT PRIMARY KEY, situacao TEXT, titulo TEXT, descricao TEXT, imagem TEXT,
    erro TEXT, definitiva INTEGER, tentativas INTEGER, buscada_em TEXT, tentar_depois_de TEXT)"""


def sqlite_antigo(caminho, com_previa=True):
    c = sqlite3.connect(caminho)
    c.execute(NOTA_001)
    c.execute(IMPORTACAO)
    bruto = json.dumps(carregar_fixture("bot_api/whatsapp_9_links.json"), ensure_ascii=False)
    linhas = [
        (5, -1001234567890, 10, "2026-11-05T10:00:00+00:00", None, "texto", "bolo #Receita", "l10", None, None,
         None, "ok", None, "ao_vivo", None, "x"),
        (9, -1001234567890, 60, "2026-11-05T11:00:00+00:00", None, "link", "lista", "l60", None, None, None,
         "ok", None, "ao_vivo", bruto, "x"),
        (12, -1001234567890, 70, "2026-11-05T12:00:00+00:00", None, "documento", "", "l70", "70_a.pdf",
         "Relatório.pdf", 2048, "ok", None, "importacao", None, "x"),
    ]
    c.executemany(f"INSERT INTO nota VALUES ({','.join('?' * 16)})", linhas)
    c.execute("INSERT INTO importacao VALUES (3, 'C:/x', 'terminal', 'concluida', 'a', 'b', 1, 0, 0, 0, NULL)")
    if com_previa:
        c.execute(PREVIA)
        c.execute("INSERT INTO previa VALUES ('https://imp.i384100.net/cbUijS', 'ok', 'Curso', NULL, NULL, NULL, 0, 1,"
                  " 'x', NULL)")
    c.commit()
    c.close()


@pytest.mark.parametrize("com_previa", [True, False])
def test_migrar_preserva_ids_e_reconstroi(engine, sessao, tmp_path, com_previa):
    origem = tmp_path / "notas.db"
    sqlite_antigo(origem, com_previa)
    contagens = migrar(origem, engine)
    assert contagens == {"notas": 3, "importacoes": 1, "previas": 1 if com_previa else 0, "links": 9, "tags": 1}
    assert list(sessao.scalars(select(Nota.id).order_by(Nota.id))) == [5, 9, 12]
    assert sessao.scalar(select(Nota.arquivo_nome).where(Nota.id == 12)) == "Relatório.pdf"
    assert list(sessao.scalars(select(Tag.nome))) == ["receita"]
    assert sessao.scalar(select(text("count(*)")).select_from(Link)) == 9
    p = sessao.get(Previa, "https://imp.i384100.net/cbUijS")
    assert p.situacao == ("ok" if com_previa else "pendente")
    assert sessao.scalar(select(text("count(*)")).select_from(Previa)) == 9  # as outras 8 entram pendentes
    # sequências ajustadas: nova nota e nova importação não colidem com os ids copiados
    from notas.repositorio import iniciar_importacao, salvar_ao_vivo
    salvar_ao_vivo(sessao, {"chat_id": -1001234567890, "message_id": 99, "enviada_em": "x", "editada_em": None,
                            "tipo": "texto", "texto": "nova", "link": "l", "arquivo_caminho": None,
                            "arquivo_nome": None, "arquivo_tamanho": None, "situacao": "ok", "erro": None,
                            "bruto": None})
    assert sessao.scalar(select(Nota.id).where(Nota.message_id == 99)) == 13
    assert iniciar_importacao(sessao, "p", "painel") == 4
    assert sessao.get(Importacao, 3).pasta == "C:/x"


def test_recusa_destino_com_notas(engine, sessao, tmp_path):
    origem = tmp_path / "notas.db"
    sqlite_antigo(origem)
    migrar(origem, engine)
    with pytest.raises(ErroMigracao, match="já tem notas"):
        migrar(origem, engine)
    assert sessao.scalar(select(text("count(*)")).select_from(Nota)) == 3


def test_origem_inexistente(engine, tmp_path):
    with pytest.raises(ErroMigracao, match="não encontrei"):
        migrar(tmp_path / "nao_existe.db", engine)
