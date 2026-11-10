"""Esquema PostgreSQL (007): restrições, busca sem acento e uma importação por vez."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from notas.db import exigir_revisao_atual

INSERIR = text(
    "INSERT INTO nota (chat_id, message_id, enviada_em, tipo, texto, link, situacao, erro, origem, criada_em)"
    " VALUES (:chat, :mid, '2026-11-05T10:00:00+00:00', :tipo, :texto, 'l', :sit, :erro, 'ao_vivo',"
    " '2026-11-05T10:00:00+00:00')"
)
BUSCA = text("SELECT texto FROM nota WHERE busca @@ to_tsquery('notas', :q) ORDER BY id")


def inserir(sessao, mid=1, tipo="texto", texto="x", sit="ok", erro=None, chat=-1009876543210):
    sessao.execute(INSERIR, dict(chat=chat, mid=mid, tipo=tipo, texto=texto, sit=sit, erro=erro))


def test_migracao_cria_tabelas(sessao):
    nomes = set(sessao.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")))
    assert {"nota", "link", "previa", "tag", "importacao", "alembic_version"} <= nomes
    indices = set(sessao.scalars(text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")))
    assert {"nota_busca", "previa_busca", "link_site_data", "previa_fila", "tag_nome", "importacao_uma_por_vez"} <= indices


def test_chat_id_de_supergrupo_cabe(sessao):
    inserir(sessao, chat=-1009876543210)  # não cabe em 32 bits
    assert sessao.scalar(text("SELECT chat_id FROM nota")) == -1009876543210


def test_mensagem_duplicada_e_rejeitada(sessao):
    inserir(sessao)
    with pytest.raises(IntegrityError):
        inserir(sessao)


@pytest.mark.parametrize("campos", [dict(tipo="gif"), dict(sit="talvez"), dict(sit="falha", erro=None)])
def test_checks(sessao, campos):
    with pytest.raises(IntegrityError):
        inserir(sessao, **campos)


def test_busca_ignora_maiusculas_e_acentos_e_aceita_prefixo(sessao):
    inserir(sessao, mid=1, texto="Reunião às 15h")
    inserir(sessao, mid=2, texto="comprar pão")
    assert sessao.scalars(BUSCA, {"q": "REUNIAO"}).all() == ["Reunião às 15h"]
    assert sessao.scalars(BUSCA, {"q": "reun:*"}).all() == ["Reunião às 15h"]
    assert sessao.scalars(BUSCA, {"q": "pao"}).all() == ["comprar pão"]


def test_busca_acompanha_update_e_nome_do_arquivo(sessao):
    inserir(sessao, texto="antes")
    sessao.execute(text("UPDATE nota SET texto = 'depois', arquivo_nome = 'Relatório.pdf' WHERE message_id = 1"))
    assert sessao.scalars(BUSCA, {"q": "antes"}).all() == []
    assert sessao.scalars(BUSCA, {"q": "depois"}).all() == ["depois"]
    assert sessao.scalars(BUSCA, {"q": "relatorio:*"}).all() == ["depois"]


def test_uma_importacao_rodando_por_vez(sessao):
    ins = text("INSERT INTO importacao (pasta, via, status, iniciada_em) VALUES ('p', 'terminal', :s, '2026-11-05')")
    sessao.execute(ins, {"s": "rodando"})
    sessao.execute(ins, {"s": "concluida"})
    with pytest.raises(IntegrityError):
        sessao.execute(ins, {"s": "rodando"})


def test_revisao_atual_ok(engine):
    exigir_revisao_atual(engine)


def test_banco_sem_migracao_e_recusado(url_banco):
    from sqlalchemy.engine import make_url

    from conftest import recriar_banco
    from notas.db import criar_engine

    url = make_url(url_banco).set(database=make_url(url_banco).database.removesuffix("_test") + "_vazio_test")
    url = url.render_as_string(hide_password=False)
    recriar_banco(url)
    eng = criar_engine(url)
    with pytest.raises(SystemExit, match="alembic upgrade head"):
        exigir_revisao_atual(eng)
    eng.dispose()


def test_postgres_desligado_da_mensagem_sem_senha():
    from notas.db import criar_engine

    with pytest.raises(SystemExit) as e:
        exigir_revisao_atual(criar_engine("postgresql+psycopg://postgres:segredo123@127.0.0.1:1/telegram"))
    assert "127.0.0.1:1" in str(e.value) and "segredo123" not in str(e.value)


# --- link, previa, tag --------------------------------------------------------------
LINK = text("INSERT INTO link (nota_id, posicao, url, site, data) VALUES (:n, :p, :u, 's', '2026-11-05T10:00:00+00:00')")


def id_nota(sessao, mid=1):
    return sessao.scalar(text("SELECT id FROM nota WHERE message_id = :m"), {"m": mid})


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
    sessao.execute(text("INSERT INTO tag (nota_id, nome) VALUES (:n, 'x')"), {"n": id_nota(sessao)})
    sessao.execute(text("DELETE FROM nota"))
    assert sessao.scalar(text("SELECT count(*) FROM link")) == 0
    assert sessao.scalar(text("SELECT count(*) FROM tag")) == 0


def test_previa_check_e_busca(sessao):
    with pytest.raises(IntegrityError):
        sessao.execute(text("INSERT INTO previa (url, situacao) VALUES ('u', 'talvez')"))
    sessao.rollback()
    sessao.execute(text("INSERT INTO previa (url, situacao) VALUES ('u', 'pendente')"))
    sessao.execute(text("UPDATE previa SET situacao = 'ok', titulo = 'Reunião de pais' WHERE url = 'u'"))
    assert sessao.scalar(text("SELECT count(*) FROM previa WHERE busca @@ to_tsquery('notas', 'REUNIAO')")) == 1
