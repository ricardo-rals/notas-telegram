import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from notas.db import exigir_revisao_atual

INSERIR = text(
    "INSERT INTO nota (chat_id, message_id, enviada_em, tipo, texto, link, situacao, erro, origem, criada_em)"
    " VALUES (:chat, :mid, '2026-11-05T10:00:00+00:00', :tipo, :texto, 'l', :sit, :erro, 'ao_vivo',"
    " '2026-11-05T10:00:00+00:00')"
)


def inserir(sessao, mid=1, tipo="texto", texto="x", sit="ok", erro=None):
    sessao.execute(INSERIR, dict(chat=-100, mid=mid, tipo=tipo, texto=texto, sit=sit, erro=erro))


def test_migracao_cria_tabelas(sessao):
    nomes = {r[0] for r in sessao.execute(text("SELECT name FROM sqlite_master"))}
    assert {"nota", "nota_fts", "importacao"} <= nomes
    assert sessao.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_mensagem_duplicada_e_rejeitada(sessao):
    inserir(sessao)
    with pytest.raises(IntegrityError):
        inserir(sessao)


@pytest.mark.parametrize(
    "campos",
    [dict(tipo="gif"), dict(sit="talvez"), dict(sit="falha", erro=None)],
)
def test_checks(sessao, campos):
    with pytest.raises(IntegrityError):
        inserir(sessao, **campos)


def test_fts_ignora_maiusculas_e_acentos(sessao):
    inserir(sessao, mid=1, texto="Reunião às 15h")
    inserir(sessao, mid=2, texto="comprar pão")
    achados = sessao.execute(
        text("SELECT nota.texto FROM nota_fts JOIN nota ON nota.id = nota_fts.rowid WHERE nota_fts MATCH 'REUNIAO'")
    ).scalars().all()
    assert achados == ["Reunião às 15h"]


def test_fts_acompanha_update(sessao):
    inserir(sessao, texto="antes")
    sessao.execute(text("UPDATE nota SET texto = 'depois' WHERE message_id = 1"))
    consulta = text("SELECT count(*) FROM nota_fts WHERE nota_fts MATCH :q")
    assert sessao.execute(consulta, {"q": "antes"}).scalar() == 0
    assert sessao.execute(consulta, {"q": "depois"}).scalar() == 1


def test_uma_importacao_rodando_por_vez(sessao):
    ins = text(
        "INSERT INTO importacao (pasta, via, status, iniciada_em) VALUES ('p', 'terminal', :s, '2026-11-05')"
    )
    sessao.execute(ins, {"s": "rodando"})
    sessao.execute(ins, {"s": "concluida"})
    with pytest.raises(IntegrityError):
        sessao.execute(ins, {"s": "rodando"})


def test_revisao_atual_ok(engine):
    exigir_revisao_atual(engine)


def test_banco_sem_migracao_e_recusado(tmp_path):
    from notas.db import criar_engine

    with pytest.raises(SystemExit, match="alembic upgrade head"):
        exigir_revisao_atual(criar_engine(tmp_path / "vazio.db"))
