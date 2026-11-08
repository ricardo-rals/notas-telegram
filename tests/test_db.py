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


# --- 003: link, previa, previa_fts (nota_site removida) ----------------------------
LINK = text(
    "INSERT INTO link (nota_id, posicao, url, site, data) VALUES (:n, :p, :u, 's', '2026-11-05T10:00:00+00:00')"
)


def id_nota(sessao, mid=1):
    return sessao.execute(text("SELECT id FROM nota WHERE message_id = :m"), {"m": mid}).scalar()


def nomes(sessao, tipo=None):
    filtro = f" WHERE type = '{tipo}'" if tipo else ""
    return {r[0] for r in sessao.execute(text(f"SELECT name FROM sqlite_master{filtro}"))}


def test_0003_tabelas_e_indices(sessao):
    n = nomes(sessao)
    assert {"link", "previa", "previa_fts"} <= n and "nota_site" not in n
    assert {"link_site_data", "link_data", "previa_fila"} <= nomes(sessao, "index")


def test_link_unicos_e_cascade(sessao):
    inserir(sessao, tipo="link")
    n = id_nota(sessao)
    sessao.execute(LINK, {"n": n, "p": 0, "u": "https://a.com"})
    with pytest.raises(IntegrityError):
        sessao.execute(LINK, {"n": n, "p": 1, "u": "https://a.com"})
    sessao.rollback()
    inserir(sessao, tipo="link")
    n = id_nota(sessao)
    sessao.execute(LINK, {"n": n, "p": 0, "u": "https://a.com"})
    with pytest.raises(IntegrityError):
        sessao.execute(LINK, {"n": n, "p": 0, "u": "https://b.com"})
    sessao.rollback()
    inserir(sessao, tipo="link")
    sessao.execute(LINK, {"n": id_nota(sessao), "p": 0, "u": "https://a.com"})
    sessao.execute(text("DELETE FROM nota"))
    assert sessao.execute(text("SELECT count(*) FROM link")).scalar() == 0


def test_previa_check_e_fts(sessao):
    with pytest.raises(IntegrityError):
        sessao.execute(text("INSERT INTO previa (url, situacao) VALUES ('u', 'talvez')"))
    sessao.rollback()
    sessao.execute(text("INSERT INTO previa (url, situacao) VALUES ('u', 'pendente')"))
    sessao.execute(text("UPDATE previa SET situacao = 'ok', titulo = 'Reunião de pais' WHERE url = 'u'"))
    achados = sessao.execute(text("SELECT count(*) FROM previa_fts WHERE previa_fts MATCH 'REUNIAO'")).scalar()
    assert achados == 1


def test_downgrade_0002_recria_nota_site(config_teste):
    from alembic import command

    from notas.db import _alembic, criar_engine, migrar

    migrar(config_teste.database_path)
    command.downgrade(_alembic(config_teste.database_path), "0002")
    eng = criar_engine(config_teste.database_path)
    with eng.connect() as conn:
        n = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master"))}
    eng.dispose()
    assert "nota_site" in n and not {"link", "previa", "previa_fts"} & n


def test_migracao_0003_reconstroi_notas_antigas(config_teste):
    import json

    from alembic import command

    from conftest import carregar_fixture
    from notas.db import _alembic, criar_engine

    cfg = _alembic(config_teste.database_path)
    command.upgrade(cfg, "0001")
    eng = criar_engine(config_teste.database_path)
    ins = text(
        "INSERT INTO nota (chat_id, message_id, enviada_em, tipo, texto, link, situacao, origem, bruto, criada_em)"
        " VALUES (-1001234567890, :mid, '2026-11-05T10:00:00+00:00', :tipo, 'x', 'l', 'ok', 'ao_vivo', :bruto,"
        " '2026-11-05T10:00:00+00:00')"
    )
    with eng.begin() as conn:
        for mid, nome in [(60, "whatsapp_9_links"), (40, "link_varios_sites")]:
            bruto = json.dumps(carregar_fixture(f"bot_api/{nome}.json"), ensure_ascii=False)
            conn.execute(ins, dict(mid=mid, tipo="link", bruto=bruto))
        conn.execute(ins, dict(mid=4, tipo="texto", bruto=None))
    consulta = text(
        "SELECT n.message_id, count(l.id) FROM nota n LEFT JOIN link l ON l.nota_id = n.id GROUP BY 1 ORDER BY 1"
    )

    def contagem():
        with eng.connect() as conn:
            return conn.execute(consulta).all(), {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master"))}

    command.upgrade(cfg, "head")
    linhas, tabelas = contagem()
    assert linhas == [(4, 0), (40, 3), (60, 9)] and "nota_site" not in tabelas
    command.downgrade(cfg, "0002")
    command.upgrade(cfg, "head")
    assert contagem()[0] == linhas
    eng.dispose()


def test_migracao_0004_enfileira_previas_de_links_antigos(config_teste):
    """Banco migrado para 0003 antes da fila existir: links sem prévia ganham `pendente`."""
    from alembic import command

    from notas.db import _alembic, criar_engine

    cfg = _alembic(config_teste.database_path)
    command.upgrade(cfg, "0003")
    eng = criar_engine(config_teste.database_path)
    with eng.begin() as conn:
        conn.execute(text(
            "INSERT INTO nota (id, chat_id, message_id, enviada_em, tipo, texto, link, situacao, origem, criada_em)"
            " VALUES (1, -1001234567890, 1, '2026-11-05T10:00:00+00:00', 'link', 'x', 'l', 'ok', 'ao_vivo', 'x')"
        ))
        conn.execute(text(
            "INSERT INTO link (nota_id, posicao, url, site, data) VALUES"
            " (1, 0, 'https://a.com/1', 'a.com', 'd'), (1, 1, 'https://b.com/2', 'b.com', 'd'), (1, 2, '', '', 'd')"
        ))
        conn.execute(text("INSERT INTO previa (url, situacao) VALUES ('https://b.com/2', 'ok')"))
    command.upgrade(cfg, "head")
    with eng.connect() as conn:
        assert conn.execute(text("SELECT url, situacao FROM previa ORDER BY url")).all() == [
            ("https://a.com/1", "pendente"), ("https://b.com/2", "ok")
        ]
    eng.dispose()
