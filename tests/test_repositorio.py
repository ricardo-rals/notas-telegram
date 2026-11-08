from sqlalchemy import func, select

from notas.db import Nota
from notas.repositorio import registrar_falha, salvar_ao_vivo


def dados(mid=1, **extra):
    return {
        "chat_id": -1001234567890,
        "message_id": mid,
        "enviada_em": "2026-11-05T10:00:00+00:00",
        "editada_em": None,
        "tipo": "texto",
        "texto": "comprar pão",
        "link": f"https://t.me/c/1234567890/{mid}",
        "arquivo_caminho": None,
        "arquivo_nome": None,
        "arquivo_tamanho": None,
        "situacao": "ok",
        "erro": None,
        "bruto": "{}",
    } | extra


def contar(sessao):
    return sessao.scalar(select(func.count()).select_from(Nota))


def test_salvar_ao_vivo_grava_campos(sessao):
    salvar_ao_vivo(sessao, dados())
    n = sessao.scalars(select(Nota)).one()
    assert (n.tipo, n.texto, n.origem, n.situacao) == ("texto", "comprar pão", "ao_vivo", "ok")
    assert n.criada_em


def test_salvar_ao_vivo_repetido_mantem_uma_linha(sessao):
    salvar_ao_vivo(sessao, dados())
    salvar_ao_vivo(sessao, dados())
    assert contar(sessao) == 1


def test_salvar_ao_vivo_atualiza_sem_mexer_em_envio(sessao):
    salvar_ao_vivo(sessao, dados())
    criada = sessao.scalars(select(Nota)).one().criada_em
    salvar_ao_vivo(
        sessao,
        dados(texto="https://x.y", tipo="link", editada_em="2026-11-05T11:00:00+00:00", enviada_em="outra"),
    )
    sessao.expire_all()
    n = sessao.scalars(select(Nota)).one()
    assert (n.tipo, n.texto, n.editada_em) == ("link", "https://x.y", "2026-11-05T11:00:00+00:00")
    assert n.enviada_em == "2026-11-05T10:00:00+00:00" and n.criada_em == criada


def test_registrar_falha_nova(sessao):
    registrar_falha(sessao, chat_id=-1001234567890, message_id=7, erro="boom", bruto='{"x":1}',
                    enviada_em="2026-11-05T10:00:00+00:00", link="l")
    n = sessao.scalars(select(Nota)).one()
    assert (n.situacao, n.erro, n.tipo, n.texto, n.bruto) == ("falha", "boom", "outro", "", '{"x":1}')


def test_registrar_falha_preserva_conteudo_existente(sessao):
    salvar_ao_vivo(sessao, dados())
    registrar_falha(sessao, chat_id=-1001234567890, message_id=1, erro="boom", bruto="{}",
                    enviada_em="x", link="l", editada_em="2026-11-05T12:00:00+00:00")
    sessao.expire_all()
    n = sessao.scalars(select(Nota)).one()
    assert (n.texto, n.tipo, n.situacao, n.erro) == ("comprar pão", "texto", "falha", "boom")
    assert n.editada_em == "2026-11-05T12:00:00+00:00"


# --- US2: busca -------------------------------------------------------------
import pytest  # noqa: E402

from notas.repositorio import buscar  # noqa: E402


def semear(sessao, textos_tipos):
    for i, (texto, tipo) in enumerate(textos_tipos, start=1):
        salvar_ao_vivo(sessao, dados(mid=i, texto=texto, tipo=tipo, enviada_em=f"2026-11-05T10:{i // 60:02d}:{i % 60:02d}+00:00"))


def test_buscar_pagina_e_ordem(sessao):
    semear(sessao, [(f"nota {i}", "texto") for i in range(1, 121)])
    itens, total = buscar(sessao)
    assert total == 120 and len(itens) == 50
    assert itens[0].texto == "nota 120" and itens[49].texto == "nota 71"
    itens3, _ = buscar(sessao, pagina=3)
    assert len(itens3) == 20
    assert buscar(sessao, pagina=4)[0] == []


def test_buscar_sem_acento_e_maiuscula(sessao):
    semear(sessao, [("Reunião às 15h", "texto"), ("reuniao amanhã", "texto"), ("outra coisa", "texto")])
    itens, total = buscar(sessao, q="REUNIÃO")
    assert total == 2


def test_buscar_varias_palavras_exige_todas(sessao):
    semear(sessao, [("reunião às 15h", "texto"), ("reunião cancelada", "texto")])
    assert [n.texto for n in buscar(sessao, q="reuniao 15h")[0]] == ["reunião às 15h"]


@pytest.mark.parametrize("q", ['"', "*", "-", "(", 'a"b', "NEAR(", "x OR", "^"])
def test_buscar_caracteres_especiais_nao_quebram(sessao, q):
    semear(sessao, [("texto qualquer", "texto")])
    buscar(sessao, q=q)


def test_buscar_tipo_falha_e_combinacao(sessao):
    semear(sessao, [("foto da praia", "foto"), ("praia texto", "texto")])
    salvar_ao_vivo(sessao, dados(mid=50, texto="praia quebrada", situacao="falha", erro="x", tipo="foto"))
    assert {n.texto for n in buscar(sessao, tipo="foto")[0]} == {"foto da praia", "praia quebrada"}
    assert [n.texto for n in buscar(sessao, tipo="falha")[0]] == ["praia quebrada"]
    assert [n.texto for n in buscar(sessao, q="praia", tipo="texto")[0]] == ["praia texto"]


@pytest.mark.lento
def test_busca_com_10000_notas_em_menos_de_1s(sessao):
    import time

    from sqlalchemy import insert as insert_core

    palavras = ["reunião", "mercado", "projeto", "viagem", "leitura", "treino", "conta", "ideia"]
    linhas = [
        dados(mid=i, texto=f"{palavras[i % 8]} nota {i} {palavras[(i * 7) % 8]}",
              tipo="link" if i % 5 == 0 else "texto", enviada_em=f"2026-01-01T00:00:00+00:00:{i:05d}")
        | {"origem": "ao_vivo", "criada_em": "x"}
        for i in range(1, 10_001)
    ]
    sessao.execute(insert_core(Nota), linhas)
    sessao.commit()
    for q, tipo in [("", ""), ("reuniao", ""), ("projeto viagem", ""), ("mercado", "link"), ("", "falha")]:
        inicio = time.perf_counter()
        buscar(sessao, q=q, tipo=tipo, pagina=3)
        assert time.perf_counter() - inicio < 1.0, (q, tipo)


# --- 002/003: contagem por tipo -------------------------------------------------------
import json  # noqa: E402

from conftest import carregar_fixture  # noqa: E402
from notas.db import TIPOS, Link  # noqa: E402
from notas.regras import ItemLink, itens_de_link, normalizar_bot_api  # noqa: E402
from notas.repositorio import (  # noqa: E402
    buscar_links,
    contar_por_tipo,
    contar_sites,
    links_das_notas,
    reconstruir_links,
    salvar_importada,
)

DATA = "2026-11-05T10:00:00+00:00"


def item(pos, url, site, data=DATA, autor=None):
    return ItemLink(pos, url, site, data, autor)


def com_links(sessao, mid, sites, **extra):
    """Nota de link com um item por site (url derivada do site)."""
    itens = [item(i, f"https://{s or 'com.br'}/{mid}/{i}", s, extra.pop("data", DATA)) for i, s in enumerate(sites)]
    salvar_ao_vivo(sessao, dados(mid, **({"tipo": "link"} | extra)), itens=itens)


def test_contar_por_tipo(sessao):
    for i in range(7):
        salvar_ao_vivo(sessao, dados(i, tipo="foto"))
    for i in range(7, 10):
        salvar_ao_vivo(sessao, dados(i, tipo="audio"))
    com_links(sessao, 10, ["a.com", "b.com", "a.com"], situacao="falha", erro="x")
    c = contar_por_tipo(sessao)
    # a aba Link conta itens (3); as demais contam notas (FR-002)
    assert c == {t: 0 for t in TIPOS} | {"foto": 7, "audio": 3, "link": 3, "falha": 1, "todas": 11}


# --- 003 US1: itens de link -------------------------------------------------------------
def itens_por_mid(sessao):
    sessao.expire_all()
    linhas = sessao.execute(
        select(Nota.message_id, Link.url, Link.site).join(Link, Link.nota_id == Nota.id).order_by(Link.posicao)
    ).all()
    r = {}
    for mid, url, site in linhas:
        r.setdefault(mid, []).append((url, site))
    return r


def popular_sites(sessao):
    for mid in (1, 2, 3):
        com_links(sessao, mid, ["youtube.com"], texto=f"vídeo {mid}")
    com_links(sessao, 4, ["instagram.com", "ac.com", "youtube.com"], texto="três sites")
    com_links(sessao, 5, [""], texto="sem site")


def test_contar_sites_conta_itens(sessao):
    popular_sites(sessao)
    assert contar_sites(sessao) == [("youtube.com", 4), ("ac.com", 1), ("instagram.com", 1), ("", 1)]


def test_salvar_grava_troca_e_remove_itens(sessao):
    salvar_ao_vivo(sessao, dados(1, tipo="link"), itens=[item(0, "https://a.com", "a.com"), item(1, "https://b.com", "b.com")])
    assert itens_por_mid(sessao)[1] == [("https://a.com", "a.com"), ("https://b.com", "b.com")]
    salvar_ao_vivo(sessao, dados(1, tipo="link"), itens=[item(0, "https://b.com", "b.com")])  # edição (FR-004)
    assert itens_por_mid(sessao)[1] == [("https://b.com", "b.com")]
    salvar_ao_vivo(sessao, dados(1, tipo="texto"))  # deixou de ser link
    assert 1 not in itens_por_mid(sessao)
    salvar_ao_vivo(sessao, dados(2, tipo="link"))  # link sem itens → sentinela
    assert itens_por_mid(sessao)[2] == [("", "")]
    salvar_ao_vivo(sessao, dados(3, tipo="foto"), itens=[item(0, "https://c.com", "c.com")])
    assert 3 not in itens_por_mid(sessao)


def test_salvar_importada_so_ao_criar_e_falha_mantem(sessao):
    assert salvar_importada(sessao, dados(1, tipo="link"), itens=[item(0, "https://c.com", "c.com")])
    assert not salvar_importada(sessao, dados(1, tipo="link"), itens=[item(0, "https://d.com", "d.com")])
    registrar_falha(sessao, chat_id=-1001234567890, message_id=1, erro="x", bruto=None,
                    enviada_em=DATA, link="l")
    assert itens_por_mid(sessao)[1] == [("https://c.com", "c.com")]


def test_buscar_links(sessao):
    popular_sites(sessao)
    com_links(sessao, 6, ["youtube.com"], texto="mais novo", data="2026-12-01T00:00:00+00:00")
    pagina, total = buscar_links(sessao)
    assert total == 8 and pagina[0][1].texto == "mais novo"  # ordem por data do item (FR-017)
    assert all(previa.situacao == "pendente" for _, _, previa in pagina)  # criada junto com o link (003)
    textos = lambda **kw: sorted(n.texto for _, n, _ in buscar_links(sessao, **kw)[0])  # noqa: E731
    assert textos(site="youtube.com") == ["mais novo", "três sites", "vídeo 1", "vídeo 2", "vídeo 3"]
    assert textos(site="") == ["sem site"]
    assert textos(site="youtube.com", q="vídeo 2") == ["vídeo 2"]
    assert buscar_links(sessao, site="nao-existe.com") == ([], 0)


def test_buscar_links_paginacao(sessao):
    com_links(sessao, 1, [f"s{i}.com" for i in range(52)])
    assert len(buscar_links(sessao)[0]) == 50 and buscar_links(sessao)[1] == 52
    assert len(buscar_links(sessao, pagina=2)[0]) == 2


def test_links_das_notas(sessao):
    com_links(sessao, 1, ["a.com", "b.com"])
    com_links(sessao, 2, ["c.com"])
    ids = list(sessao.scalars(select(Nota.id).order_by(Nota.message_id)))
    r = links_das_notas(sessao, ids)
    assert [lk.site for lk, _ in r[ids[0]]] == ["a.com", "b.com"]
    assert [lk.site for lk, _ in r[ids[1]]] == ["c.com"]
    assert links_das_notas(sessao, []) == {}


def bruto_bot(nome):
    return json.dumps(carregar_fixture(f"bot_api/{nome}.json"), ensure_ascii=False)


def snapshot(sessao):
    return [tuple(r) for r in sessao.execute(select(Nota.__table__).order_by(Nota.id)).all()]


def test_reconstruir_links(sessao, engine):
    exp = carregar_fixture("exportacao_links/result.json")["messages"][0]
    salvar_ao_vivo(sessao, dados(60, tipo="link", bruto=bruto_bot("whatsapp_9_links")))
    salvar_ao_vivo(sessao, dados(2, tipo="link", bruto=bruto_bot("link_idn")))
    salvar_ao_vivo(sessao, dados(3, tipo="link", bruto=None, texto="https://m.x.com.br"))
    salvar_ao_vivo(sessao, dados(4, tipo="link", bruto="{", texto="ver https://www.y.com"))
    salvar_ao_vivo(sessao, dados(5, tipo="foto", texto="https://z.com"))
    salvar_importada(sessao, dados(7, tipo="link", bruto=json.dumps(exp)))
    antes = snapshot(sessao)

    with engine.begin() as conn:
        assert reconstruir_links(conn) == 5
    r = itens_por_mid(sessao)
    assert [s for _, s in r[60]] == ["i384100.net"] + ["instagram.com"] * 8
    assert r[2] == [("https://xn--bcher-kva.de/", "bücher.de")]
    assert r[3] == [("https://m.x.com.br", "x.com.br")]
    assert r[4] == [("https://www.y.com", "y.com")]
    assert 5 not in r
    assert r[7] == [("https://m.facebook.com/evento", "facebook.com")]
    autores = set(sessao.scalars(select(Link.autor).join(Nota).where(Nota.message_id == 60)))
    assert autores == {"Usuario"}
    with engine.begin() as conn:
        reconstruir_links(conn)
    assert itens_por_mid(sessao) == r  # FR-015 idempotente
    assert snapshot(sessao) == antes  # nota não muda


def test_itens_de_link_da_mensagem_de_exemplo_gravam_9(sessao):
    m = normalizar_bot_api(carregar_fixture("bot_api/whatsapp_9_links.json"))
    salvar_ao_vivo(sessao, dados(60, tipo="link"), itens=itens_de_link(m))
    assert contar_sites(sessao) == [("instagram.com", 8), ("i384100.net", 1)]


# --- 003 US2: fila de prévias --------------------------------------------------------
from datetime import UTC, datetime, timedelta  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from notas.db import Previa  # noqa: E402
from notas.repositorio import proximas_previas, registrar_previa  # noqa: E402

AGORA = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def resultado(situacao="indisponivel", definitiva=False, **kw):
    base = dict(titulo=None, descricao=None, imagem=None, erro=None if situacao == "ok" else "falhou")
    return SimpleNamespace(situacao=situacao, definitiva=definitiva, **(base | kw))


def test_links_criam_previa_pendente_uma_por_url(sessao):
    com_links(sessao, 1, ["a.com", "b.com"])
    salvar_ao_vivo(sessao, dados(2, tipo="link"), itens=[item(0, "https://a.com/1/0", "a.com")])  # mesma URL
    salvar_ao_vivo(sessao, dados(3, tipo="link"))  # sentinela: sem prévia
    urls = sorted(sessao.scalars(select(Previa.url)))
    assert urls == ["https://a.com/1/0", "https://b.com/1/1"]
    assert set(sessao.scalars(select(Previa.situacao))) == {"pendente"}


def test_fila_e_recuo(sessao):
    com_links(sessao, 1, ["a.com"])
    url = "https://a.com/1/0"
    assert proximas_previas(sessao, AGORA) == [url]
    esperas = []
    for _ in range(5):
        registrar_previa(sessao, url, resultado(), AGORA)
        p = sessao.get(Previa, url)
        sessao.refresh(p)
        esperas.append(datetime.fromisoformat(p.tentar_depois_de) - AGORA)
        assert proximas_previas(sessao, AGORA) == []
        assert proximas_previas(sessao, AGORA + esperas[-1]) == [url]
    h = timedelta(hours=1)
    assert esperas == [h, 6 * h, 24 * h, 7 * 24 * h, 7 * 24 * h] and p.tentativas == 5


def test_registrar_ok_e_definitiva(sessao):
    com_links(sessao, 1, ["a.com", "b.com"])
    registrar_previa(sessao, "https://a.com/1/0", resultado("ok", titulo="T", descricao="D", imagem="previas/x.png"), AGORA)
    registrar_previa(sessao, "https://b.com/1/1", resultado(definitiva=True, erro="endereço local"), AGORA)
    a, b = sessao.get(Previa, "https://a.com/1/0"), sessao.get(Previa, "https://b.com/1/1")
    assert (a.situacao, a.titulo, a.descricao, a.imagem, a.erro) == ("ok", "T", "D", "previas/x.png", None)
    assert (b.situacao, b.definitiva, b.erro) == ("indisponivel", 1, "endereço local")
    assert proximas_previas(sessao, AGORA + timedelta(days=365)) == []


def test_busca_na_aba_link_casa_titulo_da_previa(sessao):
    com_links(sessao, 1, ["a.com"], texto="sem palavra")
    registrar_previa(sessao, "https://a.com/1/0", resultado("ok", titulo="Receita de Pão"), AGORA)
    assert buscar_links(sessao, q="pao")[1] == 1


@pytest.mark.lento
def test_aba_link_com_10000_notas_em_menos_de_1s(sessao, engine):
    """SC-005 da 003: 10.000 notas, 2.500 de link com 2 URLs (5.000 itens em 200 sites), metade das prévias ok."""
    import time

    from sqlalchemy import insert as insert_core

    from notas.repositorio import buscar_links, contar_sites, links_das_notas, reconstruir_links
    from sqlalchemy import text

    notas = [
        dados(mid=i, texto=f"nota {i} receita" if i % 3 else f"nota {i}", tipo="link" if i % 4 == 0 else "texto",
              enviada_em=f"2026-01-01T00:00:{i % 60:02d}+00:00") | {"origem": "ao_vivo", "criada_em": "x"}
        for i in range(1, 10_001)
    ]
    sessao.execute(insert_core(Nota), notas)
    ids = dict(sessao.execute(text("SELECT message_id, id FROM nota WHERE tipo = 'link'")).all())
    links = [
        {"nota_id": nid, "posicao": p, "url": f"https://s{(mid + p) % 200}.com/{mid}/{p}",
         "site": f"s{(mid + p) % 200}.com", "data": "2026-01-01T00:00:00+00:00", "autor": None}
        for mid, nid in ids.items() for p in (0, 1)
    ]
    sessao.execute(insert_core(Link), links)
    sessao.execute(insert_core(Previa), [
        {"url": lk["url"], "situacao": "ok" if i % 2 else "pendente", "titulo": f"Título {i}" if i % 2 else None}
        for i, lk in enumerate(links)
    ])
    sessao.commit()
    medir = []
    for nome, f in [
        ("contar_por_tipo", lambda: contar_por_tipo(sessao)),
        ("contar_sites", lambda: contar_sites(sessao)),
        ("buscar_links site+q", lambda: buscar_links(sessao, site="s7.com", q="receita", pagina=1)),
        ("buscar_links titulo", lambda: buscar_links(sessao, q="titulo", pagina=3)),
        ("buscar+links_das_notas", lambda: links_das_notas(sessao, [n.id for n in buscar(sessao, pagina=2)[0]])),
    ]:
        inicio = time.perf_counter()
        f()
        medir.append((nome, time.perf_counter() - inicio))
    assert all(t < 1.0 for _, t in medir), medir
    with engine.begin() as conn:
        inicio = time.perf_counter()
        reconstruir_links(conn)
        assert time.perf_counter() - inicio < 60


# --- 005: tags ---------------------------------------------------------------------------
def tags_da(sessao, mid):
    from notas.db import Tag
    return sorted(sessao.scalars(select(Tag.nome).join(Nota).where(Nota.message_id == mid)))


def test_gravar_e_substituir_tags(sessao):
    from notas.repositorio import contar_tags, salvar_importada
    salvar_ao_vivo(sessao, dados(1, texto="pão #Receita #cozinha"))
    assert tags_da(sessao, 1) == ["cozinha", "receita"]
    salvar_ao_vivo(sessao, dados(1, texto="pão #receita"))  # edição
    assert tags_da(sessao, 1) == ["receita"]
    salvar_importada(sessao, dados(2, texto="#receita #trabalho") | {"tipo": "texto"})
    salvar_ao_vivo(sessao, dados(3, texto="#trabalho"))
    salvar_ao_vivo(sessao, dados(4, texto="#zebra"))
    assert contar_tags(sessao) == [("receita", 2), ("trabalho", 2), ("zebra", 1)]


def test_buscar_por_tag(sessao):
    salvar_ao_vivo(sessao, dados(1, texto="foto #receita", tipo="foto"))
    salvar_ao_vivo(sessao, dados(2, texto="texto #receita bolo"))
    salvar_ao_vivo(sessao, dados(3, texto="outra coisa #trabalho"))
    com_links(sessao, 4, ["a.com"], texto="link #receita")
    assert {n.message_id for n in buscar(sessao, tag="receita")[0]} == {1, 2, 4}
    assert [n.message_id for n in buscar(sessao, tag="receita", tipo="foto")[0]] == [1]
    assert [n.message_id for n in buscar(sessao, tag="receita", q="bolo")[0]] == [2]
    assert buscar(sessao, tag="inexistente") == ([], 0)
    assert buscar_links(sessao, tag="receita")[1] == 1 and buscar_links(sessao, tag="trabalho")[1] == 0


def test_grupos_de_documento(sessao):
    from notas.repositorio import contar_grupos_documento
    for mid, nome in enumerate(["a.pdf", "b.PDF", "c.xlsx", "d.zip", None], start=1):
        salvar_ao_vivo(sessao, dados(mid, tipo="documento", arquivo_nome=nome))
    salvar_ao_vivo(sessao, dados(9, tipo="foto", arquivo_nome="x.pdf"))  # não é documento
    assert contar_grupos_documento(sessao) == [("pdf", 2), ("planilha", 1), ("compactado", 1), ("outro", 1)]
    assert {n.message_id for n in buscar(sessao, tipo="documento", grupo="pdf")[0]} == {1, 2}
    assert [n.message_id for n in buscar(sessao, tipo="documento", grupo="outro")[0]] == [5]


@pytest.mark.lento
def test_tags_com_10000_notas_em_menos_de_1s(sessao):
    import time

    from sqlalchemy import insert as insert_core

    from notas.db import Tag
    from notas.repositorio import contar_tags
    sessao.execute(insert_core(Nota), [
        dados(mid=i, texto=f"nota {i}", enviada_em=f"2026-01-01T00:00:{i % 60:02d}+00:00")
        | {"origem": "ao_vivo", "criada_em": "x"} for i in range(1, 10_001)])
    ids = list(sessao.scalars(select(Nota.id)))
    sessao.execute(insert_core(Tag), [{"nota_id": i, "nome": f"t{(i + k) % 300}"} for i in ids for k in (0, 1)])
    sessao.commit()
    for f in (lambda: contar_tags(sessao), lambda: buscar(sessao, tag="t7", pagina=1),
              lambda: buscar(sessao, tag="t7", q="nota", tipo="texto")):
        inicio = time.perf_counter()
        f()
        assert time.perf_counter() - inicio < 1.0
