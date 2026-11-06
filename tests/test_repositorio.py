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


# --- 002 US1: contagem por tipo -------------------------------------------------------
from notas.db import TIPOS  # noqa: E402
from notas.repositorio import contar_por_tipo  # noqa: E402


def test_contar_por_tipo(sessao):
    for i in range(7):
        salvar_ao_vivo(sessao, dados(i, tipo="foto"))
    for i in range(7, 10):
        salvar_ao_vivo(sessao, dados(i, tipo="audio"))
    salvar_ao_vivo(sessao, dados(10, tipo="link", situacao="falha", erro="x"))
    c = contar_por_tipo(sessao)
    assert c == {t: 0 for t in TIPOS} | {"foto": 7, "audio": 3, "link": 1, "falha": 1, "todas": 11}
    assert sum(c[t] for t in TIPOS) == c["todas"]  # SC-006


# --- 002 US2: sites -------------------------------------------------------------------
from notas.db import NotaSite  # noqa: E402
from notas.repositorio import buscar, contar_sites  # noqa: E402


def com_sites(sessao, mid, sites, **extra):
    salvar_ao_vivo(sessao, dados(mid, **({"tipo": "link"} | extra)), sites=frozenset(sites))
    if extra.get("tipo", "link") != "link":  # linha "suja" de nota não-link: não pode contar
        nid = sessao.scalar(select(Nota.id).where(Nota.message_id == mid))
        sessao.add_all(NotaSite(nota_id=nid, site=s) for s in sites)
        sessao.commit()


def popular_sites(sessao):
    for mid in (1, 2, 3):
        com_sites(sessao, mid, ["youtube.com"], texto=f"vídeo {mid}")
    com_sites(sessao, 4, ["instagram.com", "ac.com"], texto="dois sites")
    com_sites(sessao, 5, [""], texto="sem site")
    com_sites(sessao, 6, ["youtube.com"], tipo="foto", texto="foto com url")


def test_contar_sites(sessao):
    popular_sites(sessao)
    assert contar_sites(sessao) == [("youtube.com", 3), ("ac.com", 1), ("instagram.com", 1), ("", 1)]


def test_buscar_por_site(sessao):
    popular_sites(sessao)
    textos = lambda **kw: sorted(n.texto for n in buscar(sessao, **kw)[0])  # noqa: E731
    assert textos(tipo="link", site="youtube.com") == ["vídeo 1", "vídeo 2", "vídeo 3"]
    assert textos(tipo="link", site="") == ["sem site"]
    assert textos(tipo="link", site="instagram.com") == ["dois sites"]
    assert buscar(sessao, tipo="link", site="nao-existe.com") == ([], 0)
    assert textos(tipo="link", site="youtube.com", q="vídeo 2") == ["vídeo 2"]
    assert textos(tipo="foto", site="instagram.com") == ["foto com url"]  # site ignorado fora de link


# --- 002 US3: reclassificar notas antigas ---------------------------------------------
import json  # noqa: E402

from conftest import carregar_fixture  # noqa: E402
from notas.repositorio import reclassificar_sites  # noqa: E402


def bruto_bot(nome):
    return json.dumps(carregar_fixture(f"bot_api/{nome}.json"), ensure_ascii=False)


def sites_por_mid(sessao):
    linhas = sessao.execute(select(Nota.message_id, NotaSite.site).join(NotaSite, NotaSite.nota_id == Nota.id)).all()
    r = {}
    for mid, s in linhas:
        r.setdefault(mid, set()).add(s)
    return r


def snapshot(sessao):
    return [tuple(r) for r in sessao.execute(select(Nota.__table__).order_by(Nota.id)).all()]


def test_reclassificar_sites(sessao, engine):
    exp = carregar_fixture("exportacao_links/result.json")["messages"][0]
    salvar_ao_vivo(sessao, dados(1, tipo="link", bruto=bruto_bot("link_varios_sites")))
    salvar_ao_vivo(sessao, dados(2, tipo="link", bruto=bruto_bot("link_idn")))
    salvar_ao_vivo(sessao, dados(3, tipo="link", bruto=None, texto="https://m.x.com.br"))
    salvar_ao_vivo(sessao, dados(4, tipo="link", bruto="{", texto="ver https://www.y.com"))
    salvar_ao_vivo(sessao, dados(5, tipo="foto", texto="https://z.com"))
    salvar_ao_vivo(sessao, dados(6, tipo="link", bruto=bruto_bot("link_text_link")))
    from notas.repositorio import salvar_importada

    salvar_importada(sessao, dados(7, tipo="link", bruto=json.dumps(exp)) | {})
    # linha errada de antes deve ser corrigida
    nid6 = sessao.scalar(select(Nota.id).where(Nota.message_id == 6))
    sessao.add(NotaSite(nota_id=nid6, site="errado.com"))
    sessao.commit()
    antes = snapshot(sessao)

    with engine.begin() as conn:
        assert reclassificar_sites(conn) == 6
    sessao.expire_all()
    esperado = {
        1: {"youtube.com", "instagram.com"}, 2: {"bücher.de"}, 3: {"x.com.br"}, 4: {"y.com"},
        6: {"exemplo.com"}, 7: {"facebook.com"},
    }
    assert sites_por_mid(sessao) == esperado
    with engine.begin() as conn:
        reclassificar_sites(conn)
    assert sites_por_mid(sessao) == esperado  # FR-011
    assert snapshot(sessao) == antes  # FR-013


# --- 002 US4: gravação dos sites junto com a nota -------------------------------------
def sites_de(sessao, mid):
    return sites_por_mid(sessao).get(mid, set())


def test_salvar_ao_vivo_grava_e_troca_sites(sessao):
    salvar_ao_vivo(sessao, dados(1, tipo="link"), sites=frozenset({"a.com"}))
    assert sites_de(sessao, 1) == {"a.com"}
    salvar_ao_vivo(sessao, dados(1, tipo="link"), sites=frozenset({"b.com"}))  # edição
    assert sites_de(sessao, 1) == {"b.com"}
    salvar_ao_vivo(sessao, dados(1, tipo="texto"), sites=frozenset())  # deixou de ser link
    assert sites_de(sessao, 1) == set()
    salvar_ao_vivo(sessao, dados(2, tipo="link"))  # link sem sites informados nunca fica fora
    assert sites_de(sessao, 2) == {""}
    salvar_ao_vivo(sessao, dados(3, tipo="foto"), sites=frozenset({"c.com"}))  # só link tem site
    assert sites_de(sessao, 3) == set()


def test_salvar_importada_grava_sites_so_ao_criar(sessao):
    from notas.repositorio import salvar_importada

    assert salvar_importada(sessao, dados(1, tipo="link"), sites=frozenset({"c.com"}))
    assert not salvar_importada(sessao, dados(1, tipo="link"), sites=frozenset({"d.com"}))
    assert sites_de(sessao, 1) == {"c.com"}


def test_registrar_falha_mantem_sites(sessao):
    salvar_ao_vivo(sessao, dados(1, tipo="link"), sites=frozenset({"a.com"}))
    registrar_falha(sessao, chat_id=-1001234567890, message_id=1, erro="x", bruto=None,
                    enviada_em="2026-11-05T10:00:00+00:00", link="l")
    assert sites_de(sessao, 1) == {"a.com"}


# --- 002 Polish: desempenho (SC-003, SC-004) ------------------------------------------
@pytest.mark.lento
def test_abas_sites_e_reclassificacao_com_10000_notas(sessao, engine):
    import time

    from sqlalchemy import insert as insert_core

    base = carregar_fixture("bot_api/link_entidade.json")
    linhas = []
    for i in range(1, 10_001):
        url = f"https://www.site{i % 200}.com.br/{i}"
        bruto = json.dumps(base | {"message_id": i, "text": f"ver {url}",
                                   "entities": [{"type": "url", "offset": 4, "length": len(url)}]})
        linhas.append(dados(mid=i, texto=f"ver {url} mercado", tipo="link" if i % 2 else "texto", bruto=bruto,
                            enviada_em=f"2026-01-01T00:00:00+00:00:{i:05d}") | {"origem": "ao_vivo", "criada_em": "x"})
    sessao.execute(insert_core(Nota), linhas)
    sessao.commit()

    inicio = time.perf_counter()
    with engine.begin() as conn:
        assert reclassificar_sites(conn) == 5_000
    assert time.perf_counter() - inicio < 60  # SC-004

    for f in (lambda: contar_por_tipo(sessao), lambda: contar_sites(sessao),
              lambda: buscar(sessao, tipo="link", site="site7.com.br", q="mercado")):
        inicio = time.perf_counter()
        f()
        assert time.perf_counter() - inicio < 1.0  # SC-003
    assert len(contar_sites(sessao)) == 100  # links só nos ímpares → 100 dos 200 sites
