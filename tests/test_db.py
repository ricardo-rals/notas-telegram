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


# --- 002: nota_site ------------------------------------------------------------------
SITE = text("INSERT INTO nota_site (nota_id, site) VALUES (:n, :s)")


def id_nota(sessao, mid=1):
    return sessao.execute(text("SELECT id FROM nota WHERE message_id = :m"), {"m": mid}).scalar()


def test_nota_site_chave_e_not_null(sessao):
    inserir(sessao, tipo="link")
    n = id_nota(sessao)
    sessao.execute(SITE, {"n": n, "s": "a.com"})
    with pytest.raises(IntegrityError):
        sessao.execute(SITE, {"n": n, "s": "a.com"})
    sessao.rollback()
    inserir(sessao, tipo="link")
    with pytest.raises(IntegrityError):
        sessao.execute(SITE, {"n": id_nota(sessao), "s": None})


def test_nota_site_cascade_e_indice(sessao):
    inserir(sessao, tipo="link")
    sessao.execute(SITE, {"n": id_nota(sessao), "s": "a.com"})
    sessao.execute(text("DELETE FROM nota"))
    assert sessao.execute(text("SELECT count(*) FROM nota_site")).scalar() == 0
    indices = {r[0] for r in sessao.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))}
    assert "nota_site_site" in indices


def test_downgrade_remove_nota_site(config_teste):
    from alembic import command

    from notas.db import _alembic, criar_engine, migrar

    migrar(config_teste.database_path)
    command.downgrade(_alembic(config_teste.database_path), "0001")
    eng = criar_engine(config_teste.database_path)
    with eng.connect() as conn:
        nomes = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master"))}
    eng.dispose()
    assert "nota_site" not in nomes and "nota" in nomes


def test_migracao_0002_classifica_notas_antigas(config_teste):
    import json

    from alembic import command

    from conftest import carregar_fixture
    from notas.db import _alembic, criar_engine

    cfg = _alembic(config_teste.database_path)
    command.upgrade(cfg, "0001")
    eng = criar_engine(config_teste.database_path)
    ins = text(
        "INSERT INTO nota (chat_id, message_id, enviada_em, tipo, texto, link, situacao, origem, bruto, criada_em)"
        " VALUES (-1001234567890, :mid, '2026-11-05T10:00:00+00:00', :tipo, :texto, 'l', 'ok', 'ao_vivo', :bruto,"
        " '2026-11-05T10:00:00+00:00')"
    )
    with eng.begin() as conn:
        for mid, nome in [(1, "link_varios_sites"), (2, "link_entidade"), (3, "link_sem_esquema")]:
            bruto = json.dumps(carregar_fixture(f"bot_api/{nome}.json"), ensure_ascii=False)
            conn.execute(ins, dict(mid=mid, tipo="link", texto="x", bruto=bruto))
        conn.execute(ins, dict(mid=4, tipo="texto", texto="comprar pão", bruto=None))
    consulta = text(
        "SELECT n.message_id, s.site FROM nota n LEFT JOIN nota_site s ON s.nota_id = n.id ORDER BY 1, 2"
    )

    def linhas():
        with eng.connect() as conn:
            return conn.execute(consulta).all()

    command.upgrade(cfg, "head")
    primeiro = linhas()
    assert primeiro == [(1, "instagram.com"), (1, "youtube.com"), (2, "exemplo.com"), (3, "exemplo.com.br"),
                        (4, None)]
    command.downgrade(cfg, "0001")
    command.upgrade(cfg, "head")
    assert linhas() == primeiro
    eng.dispose()
