import json
import re
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from notas.painel import criar_app
from notas.repositorio import salvar_ao_vivo

BASE_URL = "http://127.0.0.1:8000"


def nota(mid, **extra):
    return {
        "chat_id": -1001234567890, "message_id": mid,
        "enviada_em": f"2026-11-05T10:00:{mid:02d}+00:00", "editada_em": None,
        "tipo": "texto", "texto": f"nota {mid}", "link": f"https://t.me/c/1234567890/{mid}",
        "arquivo_caminho": None, "arquivo_nome": None, "arquivo_tamanho": None,
        "situacao": "ok", "erro": None, "bruto": None,
    } | extra


@pytest.fixture
def cliente(engine, config_teste, sessao):
    return TestClient(criar_app(config_teste, engine), base_url=BASE_URL)


def test_lista(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1, texto="comprar pão"))
    r = cliente.get("/")
    assert r.status_code == 200
    assert "comprar pão" in r.text and "https://t.me/c/1234567890/1" in r.text
    assert "<html" in r.text and "/static/htmx.min.js" in r.text


def test_host_estranho_recusado(cliente):
    assert cliente.get("/", headers={"Host": "exemplo.com"}).status_code == 400
    assert cliente.get("/", headers={"Host": "localhost:8000"}).status_code == 200


def test_post_de_outra_origem_recusado(cliente):
    r = cliente.post("/importar", data={"pasta": "x"}, headers={"Origin": "http://malicioso.com"})
    assert r.status_code == 403


@pytest.mark.parametrize("query", ["tipo=xyz", "pagina=0", "pagina=abc"])
def test_parametros_invalidos(cliente, query):
    assert cliente.get(f"/?{query}").status_code == 422


def test_sem_resultados(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1))
    assert "Nada encontrado para “xyzxyz”" in cliente.get("/?q=xyzxyz").text


def test_busca_e_filtro(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1, texto="Reunião"))
    salvar_ao_vivo(sessao, nota(2, texto="reunião foto", tipo="foto"))
    r = cliente.get("/", params={"q": "reuniao", "tipo": "texto"})
    assert "Reunião" in r.text and "reunião foto" not in r.text


def test_aviso_de_novas_so_na_primeira_pagina_sem_filtro(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1))
    assert 'id="novas"' in cliente.get("/").text
    for q in ("/?pagina=2", "/?q=nota", "/?tipo=texto"):
        assert 'id="novas"' not in cliente.get(q).text, q


def test_previas_de_midia(cliente, sessao, config_teste):
    config_teste.media_dir.mkdir(parents=True)
    (config_teste.media_dir / "1_a.jpg").write_bytes(b"img")
    salvar_ao_vivo(sessao, nota(1, tipo="foto", texto="praia", arquivo_caminho="1_a.jpg"))
    salvar_ao_vivo(sessao, nota(2, tipo="audio", texto="", arquivo_caminho="2_b.ogg"))
    salvar_ao_vivo(sessao, nota(3, tipo="documento", arquivo_caminho="3_c.pdf", arquivo_nome="boleto.pdf"))
    salvar_ao_vivo(sessao, nota(4, tipo="documento", situacao="grande_demais", arquivo_nome="g.pdf"))
    salvar_ao_vivo(sessao, nota(5, tipo="foto", situacao="sem_arquivo"))
    salvar_ao_vivo(sessao, nota(6, situacao="falha", erro="ValueError: quebrou"))
    html = cliente.get("/").text
    assert re.search(r'<a class="ampliar" href="/media/1_a.jpg"[^>]*>\s*<img loading="lazy" src="/media/1_a.jpg" alt="praia"', html)
    assert '<audio controls src="/media/2_b.ogg"' in html
    assert "boleto.pdf" in html and re.search(r'href="/baixar/\d+">Baixar</a>', html)
    assert "acima de 20 MB" in html
    assert "não veio na exportação" in html
    assert re.search(r'class="cartao nota tipo-\w+ falha"', html) and "ValueError: quebrou" in html


def test_media(cliente, config_teste):
    config_teste.media_dir.mkdir(parents=True)
    (config_teste.media_dir / "1_a.jpg").write_bytes(b"img")
    assert cliente.get("/media/1_a.jpg").content == b"img"
    assert cliente.get("/media/inexistente.jpg").status_code == 404
    assert cliente.get("/media/..%2F..%2Fnotas.db").status_code == 404


# --- US5: importação pelo painel ----------------------------------------------------
import time  # noqa: E402

from conftest import FIXTURES  # noqa: E402
from notas.db import Importacao  # noqa: E402


def esperar_fim(cliente, segundos=10):
    fim = time.time() + segundos
    while time.time() < fim:
        html = cliente.get("/importar/status").text
        if "rodando" not in html:
            return html
        time.sleep(0.05)
    raise AssertionError("importação não terminou")


def test_formulario_importar(cliente):
    r = cliente.get("/importar")
    assert r.status_code == 200 and 'name="pasta"' in r.text


def test_importar_pelo_painel(cliente):
    r = cliente.post("/importar", data={"pasta": str(FIXTURES / "exportacao_ok")},
                     headers={"Origin": BASE_URL})
    assert r.status_code == 202
    html = esperar_fim(cliente)
    assert "concluída" in html and "criadas: 10" in html and "ignoradas: 2" in html and "falhas: 1" in html


def test_importar_pasta_sem_result_json(cliente, tmp_path):
    assert cliente.post("/importar", data={"pasta": str(tmp_path)}).status_code == 422


def test_importar_com_outra_rodando(cliente, sessao):
    sessao.add(Importacao(pasta="x", via="terminal", status="rodando"))
    sessao.commit()
    r = cliente.post("/importar", data={"pasta": str(FIXTURES / "exportacao_ok")})
    assert r.status_code == 409 and "em andamento" in r.text


# --- 002 US1: abas por tipo -----------------------------------------------------------
import re  # noqa: E402

def categorias(html):
    nav = re.search(r'<nav aria-label="Categorias"[^>]*>(.*?)</nav>', html, re.S).group(1)
    return [(href, bool(cur), rot.strip(), int(n)) for href, cur, rot, n in re.findall(
        r'<a href="([^"]*)"( aria-current="page")?[^>]*>([^<]*)<span class="n">(\d+)</span></a>', nav)]


def test_barra_lateral_so_com_tipos_usados(cliente, sessao):
    for i in range(1, 8):
        salvar_ao_vivo(sessao, nota(i, tipo="foto"))
    salvar_ao_vivo(sessao, nota(8, texto="palavra"))
    c = categorias(cliente.get("/").text)
    assert [(rot, n) for _, _, rot, n in c] == [("Todas", 8), ("Texto", 1), ("Foto", 7)]
    assert [rot for _, cur, rot, _ in c if cur] == ["Todas"]
    # contagens ignoram a busca; links levam o q e não levam site/pagina
    c = categorias(cliente.get("/", params={"q": "palavra", "tipo": "foto", "pagina": 1}).text)
    assert [rot for _, cur, rot, _ in c if cur] == ["Foto"]
    assert all("q=palavra" in href and "site" not in href and "pagina" not in href for href, _, _, _ in c)
    # tipo do endereço sem notas aparece destacado; falha não é categoria
    c = categorias(cliente.get("/?tipo=video").text)
    assert ("Vídeo", 0) in [(rot, n) for _, _, rot, n in c] and "Falhas" not in [x[2] for x in c]


def test_aviso_de_falhas(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1))
    assert "aviso-falhas" not in cliente.get("/").text
    salvar_ao_vivo(sessao, nota(2, situacao="falha", erro="x"))
    salvar_ao_vivo(sessao, nota(3, situacao="falha", erro="y"))
    assert re.search(r'<a class="aviso-falhas" href="/\?tipo=falha">\s*2 falhas', cliente.get("/").text)


def test_tipo_oculto_na_busca(cliente, sessao):
    html = cliente.get("/?tipo=foto").text
    assert "<select" not in html
    assert re.search(r'<input type="hidden" id="f-tipo" name="tipo" value="foto"', html)


# --- 002/003: botões de site e cartões de link -----------------------------------------
from conftest import carregar_fixture  # noqa: E402
from notas.regras import ItemLink, itens_de_link, normalizar_bot_api  # noqa: E402

DATA = "2026-11-05T10:00:00+00:00"


def link_com_sites(sessao, mid, sites, **extra):
    itens = [ItemLink(i, f"https://{s or 'com.br'}/{mid}/{i}", s, DATA, None) for i, s in enumerate(sites)]
    salvar_ao_vivo(sessao, nota(mid, **({"tipo": "link"} | extra)), itens=itens)


def botoes(html):
    m = re.search(r'<nav aria-label="Sites"[^>]*>(.*?)</nav>', html, re.S)
    return m and re.findall(r'<a href="([^"]*)"( aria-current="page")?>([^<]*)</a>', m.group(1))


def cartoes_link(html):
    return re.findall(r'<article class="cartao link">', html)


def popular(sessao):
    for mid in (1, 2, 3):
        link_com_sites(sessao, mid, ["youtube.com"], texto=f"yt {mid}")
    link_com_sites(sessao, 4, ["instagram.com"], texto="insta")
    link_com_sites(sessao, 5, [""], texto="sem site")


def test_botoes_de_site(cliente, sessao):
    popular(sessao)
    b = botoes(cliente.get("/?tipo=link").text)
    assert [rot for _, _, rot in b] == ["Todos os sites", "youtube.com (3)", "instagram.com (1)",
                                        "Sem site identificado (1)"]
    assert [rot for _, cur, rot in b if cur] == ["Todos os sites"]
    assert botoes(cliente.get("/?tipo=foto").text) is None


def test_filtrar_por_site(cliente, sessao):
    popular(sessao)
    html = cliente.get("/", params={"tipo": "link", "site": "youtube.com", "q": "yt"}).text
    assert len(cartoes_link(html)) == 3 and "https://instagram.com/4/0" not in html
    ativo = [(href, rot) for href, cur, rot in botoes(html) if cur]
    assert ativo == [("/?q=yt&amp;tipo=link", "youtube.com (3)")]  # clicar de novo desmarca
    assert re.search(r'<input type="hidden" id="f-site" name="site" value="youtube.com"', html)


def test_sem_site_e_site_inexistente(cliente, sessao):
    popular(sessao)
    html = cliente.get("/?tipo=link&site=-").text
    assert len(cartoes_link(html)) == 1 and "https://com.br/5/0" in html
    salvar_ao_vivo(sessao, nota(9, tipo="link", texto="link escondido"))  # sem URL → sentinela
    html = cliente.get("/?tipo=link&site=-").text
    assert len(cartoes_link(html)) == 2 and "link escondido" in html
    r = cliente.get("/?tipo=link&site=nao-existe.com")
    assert r.status_code == 200 and "Nenhuma nota nesta categoria" in r.text


def test_paginacao_de_itens_preserva_site(cliente, sessao):
    link_com_sites(sessao, 1, ["a.com"] * 52)  # 52 itens do mesmo site
    html = cliente.get("/?tipo=link&site=a.com").text
    assert len(cartoes_link(html)) == 50
    assert "site=a.com" in html.split('class="paginas"')[1]


def test_mensagem_de_exemplo_aba_link_e_todas(cliente, sessao):
    m = normalizar_bot_api(carregar_fixture("bot_api/whatsapp_9_links.json"))
    salvar_ao_vivo(sessao, nota(60, tipo="link", texto=m.texto, enviada_em=m.enviada_em), itens=itens_de_link(m))
    html = cliente.get("/?tipo=link").text
    assert len(cartoes_link(html)) == 9
    assert "instagram.com (8)" in html and ("Link", 9) in [(r, n) for _, _, r, n in categorias(html)]
    assert "05/11/2026 12:40 · Usuario" in html and "05/11/2026 20:41 · Usuario" in html
    assert len(cartoes_link(cliente.get("/?tipo=link&site=instagram.com").text)) == 8
    todas = cliente.get("/").text
    assert todas.count('<article class="cartao nota') == 1 and len(cartoes_link(todas)) == 9
    assert ("Todas", 1) in [(r, n) for _, _, r, n in categorias(todas)]


# --- 003 US2: prévia no cartão e CSP ---------------------------------------------------
from datetime import UTC, datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from notas.repositorio import registrar_previa  # noqa: E402

CSP = ("default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; frame-ancestors 'none'")


def previa(sessao, url, situacao="ok", **kw):
    r = dict(titulo=None, descricao=None, imagem=None, erro=None if situacao == "ok" else "x") | kw
    registrar_previa(sessao, url, SimpleNamespace(situacao=situacao, definitiva=False, **r), datetime.now(UTC))


def test_cartao_com_previa_e_escape(cliente, sessao):
    link_com_sites(sessao, 1, ["a.com", "b.com", "c.com"])
    previa(sessao, "https://a.com/1/0", titulo="<script>alert(1)</script>Receita", descricao="Pão", imagem="previas/x.png")
    previa(sessao, "https://b.com/1/1", situacao="indisponivel")
    html = cliente.get("/?tipo=link").text
    assert '<img src="/media/previas/x.png" alt="" loading="lazy">' in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;Receita" in html and "<script>alert" not in html
    assert '<p class="descricao">Pão</p>' in html
    assert "<h3>https://b.com/1/1</h3>" in html and "prévia indisponível" in html
    assert "<h3>https://c.com/1/2</h3>" in html  # pendente: só a URL
    assert html.split("<dialog")[0].count("<img") == 1  # o <img> do dialog da foto não conta


def test_csp_em_toda_resposta(cliente):
    for caminho in ("/", "/importar", "/?tipo=link"):
        assert cliente.get(caminho).headers["content-security-policy"] == CSP


def test_thread_de_previas_so_quando_ligada(engine, config_teste):
    from dataclasses import replace

    chamadas = []
    criar_app(replace(config_teste, previas_links=True), engine, iniciar_previas=lambda *a: chamadas.append(a))
    criar_app(replace(config_teste, previas_links=False), engine, iniciar_previas=lambda *a: chamadas.append(a))
    assert len(chamadas) == 1


# --- 003 US3: abrir o link e a mensagem original --------------------------------------
def test_cartao_um_link_externo_e_telegram_depois(cliente, sessao):
    link_com_sites(sessao, 1, ["a.com", "b.com"])
    previa(sessao, "https://a.com/1/0", titulo="Título A", imagem="previas/a.png")
    salvar_ao_vivo(sessao, nota(2, tipo="link", texto="sem url nenhuma"))  # sentinela
    html = cliente.get("/?tipo=link").text
    cartoes = re.findall(r'<article class="cartao link">(.*?)</article>', html, re.S)
    assert len(cartoes) == 3
    com_previa = next(c for c in cartoes if "Título A" in c)
    externos = re.findall(r'<a class="previa" href="([^"]+)" target="_blank" rel="noopener noreferrer">', com_previa)
    assert externos == ["https://a.com/1/0"]
    assert re.search(r'<a class="previa"[^>]*>\s*<img[^>]*>\s*<h3>Título A</h3>\s*</a>', com_previa)
    assert re.search(r'<a class="previa"[^>]*>\s*<h3>https://b.com/1/1</h3>', html)
    for c in cartoes:
        assert c.index("abrir no Telegram") > (c.find('class="previa"') if 'class="previa"' in c else -1)
    sentinela = next(c for c in cartoes if "sem url nenhuma" in c)
    assert 'class="previa"' not in sentinela and "t.me/c/" in sentinela
    assert not re.search(r'tabindex="[1-9]', html)


# --- 003 US4: baixar -------------------------------------------------------------------
def baixavel(sessao, config_teste, mid, caminho, conteudo=b"x", **extra):
    config_teste.media_dir.mkdir(parents=True, exist_ok=True)
    if conteudo is not None:
        (config_teste.media_dir / caminho).write_bytes(conteudo)
    salvar_ao_vivo(sessao, nota(mid, **({"tipo": "documento", "arquivo_caminho": caminho} | extra)))
    return sessao.scalar(text("SELECT id FROM nota WHERE message_id = :m").bindparams(m=mid))


def test_baixar_com_nome_original(cliente, sessao, config_teste):
    i = baixavel(sessao, config_teste, 1, "1_a.pdf", b"PDF!", arquivo_nome="boleto.pdf")
    r = cliente.get(f"/baixar/{i}")
    assert r.status_code == 200 and r.content == b"PDF!"
    assert "attachment" in r.headers["content-disposition"]
    assert 'filename="boleto.pdf"' in r.headers["content-disposition"]  # ASCII; acento vai em filename*
    j = baixavel(sessao, config_teste, 2, "2_b.pdf", arquivo_nome="relatório.pdf")
    assert "relat%C3%B3rio.pdf" in cliente.get(f"/baixar/{j}").headers["content-disposition"]
    k = baixavel(sessao, config_teste, 3, "3_c.jpg", tipo="foto")
    assert "3_c.jpg" in cliente.get(f"/baixar/{k}").headers["content-disposition"]


@pytest.mark.parametrize("caso", ["inexistente", "sem_arquivo", "apagado", "fora"])
def test_baixar_404(cliente, sessao, config_teste, caso):
    if caso == "inexistente":
        i = 999
    elif caso == "sem_arquivo":
        salvar_ao_vivo(sessao, nota(1))
        i = sessao.scalar(text("SELECT id FROM nota"))
    elif caso == "apagado":
        i = baixavel(sessao, config_teste, 1, "1_a.pdf", conteudo=None)
    else:
        (config_teste.media_dir.parent / "fora.txt").parent.mkdir(parents=True, exist_ok=True)
        (config_teste.media_dir.parent / "fora.txt").write_text("segredo")
        i = baixavel(sessao, config_teste, 1, "../fora.txt", conteudo=None)
    r = cliente.get(f"/baixar/{i}")
    assert r.status_code == 404 and "Arquivo não encontrado" in r.text and 'href="/"' in r.text
    assert "segredo" not in r.text


def test_botao_baixar_so_com_arquivo(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1, tipo="video", arquivo_caminho=None))
    salvar_ao_vivo(sessao, nota(2, tipo="documento", situacao="grande_demais", arquivo_nome="g.pdf"))
    salvar_ao_vivo(sessao, nota(3, tipo="foto", situacao="sem_arquivo"))
    assert "/baixar/" not in cliente.get("/").text
    for mid, tipo in ((4, "foto"), (5, "audio"), (6, "documento")):
        salvar_ao_vivo(sessao, nota(mid, tipo=tipo, arquivo_caminho=f"{mid}.bin"))
    assert len(re.findall(r'href="/baixar/\d+">Baixar</a>', cliente.get("/").text)) == 3


# --- 003 US5: estrutura do layout ------------------------------------------------------
def test_estrutura_do_layout(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1, tipo="documento", arquivo_caminho="1.pdf"))
    salvar_ao_vivo(sessao, nota(2, situacao="falha", erro="ValueError: x"))
    html = cliente.get("/").text
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    css = cliente.get("/static/painel.css").text if "/static/painel.css" in html else html
    for trecho in (":focus-visible", "repeat(auto-fill, minmax(260px, 1fr))", "overflow-wrap: anywhere"):
        assert trecho in css, trecho
    doc = re.search(r'<article class="cartao nota tipo-documento">(.*?)</article>', html, re.S).group(1)
    assert doc.index('class="conteudo"') < doc.index('class="meta"') < doc.index('class="acoes"')
    assert re.search(r'<article class="cartao nota tipo-texto falha">.*?ValueError: x', html, re.S)


# --- 004: concha, cartões por tipo, notas novas, estados, importar ---------------------
def painel(html):
    return re.search(r'<div id="painel"[^>]*>', html).group(0)


def test_concha(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1))
    html = cliente.get("/").text
    p = painel(html)
    for attr in ('hx-boost="true"', 'hx-target="#painel"', 'hx-select="#painel"', 'hx-swap="outerHTML"'):
        assert attr in p, attr
    antes, depois = html.split('<div id="painel"', 1)
    assert '<form id="filtros"' in antes and '<input id="q" type="search" name="q"' in antes
    assert 'id="f-tipo"' in antes and 'id="f-site"' in antes
    assert depois.count('hx-swap-oob="true"') == 4  # tipo, site, tag, grupo
    assert re.search(r'<dialog id="foto"[^>]*>.*?<img.*?class="legenda".*?<button[^>]*class="fechar"', html, re.S)
    assert '<script src="/static/painel.js" defer></script>' in html
    assert "every 10s" not in html.split('id="novas"')[0]  # a lista não se recarrega sozinha


def test_painel_js(cliente):
    js = cliente.get("/static/painel.js")
    assert js.status_code == 200
    for trecho in ('"/"', "ctrlKey", "Escape", "showModal", "ampliar"):
        assert trecho in js.text, trecho


@pytest.mark.parametrize("nome,esperado", [
    ("boleto.pdf", "PDF"), ("Planilha Final.XLSX", "XLSX"), ("sem_ext", "ARQ"),
    ("arquivo.muitolongo", "ARQ"), (None, "ARQ"), ("a.tar.gz", "GZ"),
])
def test_filtro_extensao(nome, esperado):
    from notas.painel import extensao
    assert extensao(nome) == esperado


@pytest.mark.parametrize("n,esperado", [
    (None, ""), (0, "0 B"), (900, "900 B"), (230 * 1024, "230 KB"), (1468006, "1,4 MB"), (5 * 1024**3, "5,0 GB"),
])
def test_filtro_tamanho(n, esperado):
    from notas.painel import tamanho
    assert tamanho(n) == esperado


def test_filtro_mapa_e_contato():
    from notas.painel import contato, mapa
    assert mapa("-23.55052, -46.633308") == (
        "https://www.openstreetmap.org/?mlat=-23.55052&mlon=-46.633308#map=16/-23.55052/-46.633308")
    for ruim in ("", "abc", "91, 10", "10, 200", "1,2,3"):
        assert mapa(ruim) is None, ruim
    assert contato("Maria da Silva, +55 11 99999-0000") == ("Maria da Silva", "+55 11 99999-0000", "tel:+5511999990000")
    assert contato("Só nome") == ("Só nome", "", None)


def cartao(html, tipo):
    return re.search(rf'<article class="cartao nota tipo-{tipo}[^"]*">(.*?)</article>', html, re.S).group(1)


def test_cartoes_por_tipo(cliente, sessao, config_teste):
    salvar_ao_vivo(sessao, nota(1, tipo="foto", texto="sumiu", arquivo_caminho="1_x.jpg"))  # arquivo ausente
    salvar_ao_vivo(sessao, nota(2, tipo="documento", texto="", arquivo_caminho="2.pdf",
                                arquivo_nome="boleto.pdf", arquivo_tamanho=230 * 1024))
    salvar_ao_vivo(sessao, nota(3, tipo="localizacao", texto="-23.55052, -46.633308"))
    salvar_ao_vivo(sessao, nota(4, tipo="contato", texto="Maria, +55 11 99999-0000"))
    salvar_ao_vivo(sessao, nota(5, texto="curto"))
    salvar_ao_vivo(sessao, nota(6, texto="x" * 200))
    salvar_ao_vivo(sessao, nota(7, tipo="video", texto="filme"))
    html = cliente.get("/").text
    foto = cartao(html, "foto")
    assert "imagem indisponível" in foto and "<img" not in foto
    doc = cartao(html, "documento")
    assert '<span class="selo">PDF</span>' in doc and "boleto.pdf" in doc and "230 KB" in doc
    loc = cartao(html, "localizacao")
    assert 'href="https://www.openstreetmap.org/?mlat=-23.55052&amp;mlon=-46.633308' in loc
    assert 'target="_blank" rel="noopener noreferrer">Abrir no mapa</a>' in loc
    cont = cartao(html, "contato")
    assert '<a href="tel:+5511999990000">+55 11 99999-0000</a>' in cont and "Maria" in cont
    assert re.search(r'<div class="texto curto">curto</div>', html)
    assert re.search(r'<div class="texto">x{200}</div>', html)
    assert "não é baixado" in cartao(html, "video")


def test_contar_novas_e_rota(cliente, sessao):
    from notas.repositorio import contar_novas
    topo = "2026-11-05T10:00:00+00:00"
    salvar_ao_vivo(sessao, nota(1, enviada_em=topo))
    assert contar_novas(sessao, topo) == 0 and contar_novas(sessao, "") == 1
    r = cliente.get("/novas", params={"desde": topo})
    assert r.status_code == 200 and 'id="novas"' in r.text and 'hx-trigger="every 10s"' in r.text
    assert 'class="novas"' not in r.text
    salvar_ao_vivo(sessao, nota(2, enviada_em="2026-11-05T11:00:00+00:00"))
    assert "1 nota nova · mostrar" in cliente.get("/novas", params={"desde": topo}).text
    salvar_ao_vivo(sessao, nota(3, enviada_em="2026-11-05T12:00:00+00:00"))
    salvar_ao_vivo(sessao, nota(4, enviada_em="2026-11-05T13:00:00+00:00"))
    assert "3 notas novas · mostrar" in cliente.get("/novas", params={"desde": topo}).text
    assert "/novas?desde=2026-11-05T13%3A00%3A00%2B00%3A00" in cliente.get("/").text


def test_estados_vazios(cliente, sessao):
    html = cliente.get("/").text
    assert "Seu caderno está vazio" in html and 'href="/importar"' in html
    salvar_ao_vivo(sessao, nota(1))
    html = cliente.get("/?q=inexistente&tipo=texto").text
    assert "Nada encontrado para “inexistente”" in html
    assert re.search(r'href="/\?tipo=texto"[^>]*>Limpar busca', html)
    html = cliente.get("/?pagina=5").text
    assert "Não há mais notas aqui" in html and re.search(r'href="/"[^>]*>Voltar à primeira página', html)
    assert "Nenhuma nota nesta categoria" in cliente.get("/?tipo=foto").text
    assert '<div class="fantasmas" aria-hidden="true">' in html


def criar_exportacao(base, nome, chat_id=1234567890, mensagens=3, quebrada=False):
    pasta = base / nome
    pasta.mkdir(parents=True)
    corpo = "{quebrado" if quebrada else json.dumps(
        {"name": "Caderno", "type": "private_supergroup", "id": chat_id,
         "messages": [{"id": i, "type": "message"} for i in range(mensagens)]})
    (pasta / "result.json").write_text(corpo, encoding="utf-8")
    return pasta


def test_importar_lista_exportacoes(engine, config_teste, tmp_path):
    import os
    base = tmp_path / "Downloads"
    velha = criar_exportacao(base, "ChatExport_2026-10-01", mensagens=5)
    nova = criar_exportacao(base, "ChatExport_2026-11-01", mensagens=7)
    os.utime(velha, (1_700_000_000, 1_700_000_000))
    criar_exportacao(base, "ChatExport_outro", chat_id=9999999999)
    criar_exportacao(base, "ChatExport_ruim", quebrada=True)
    cli = TestClient(criar_app(config_teste, engine, pastas_exportacao=[base]), base_url=BASE_URL)
    html = cli.get("/importar").text
    sec = re.search(r'<section class="exportacoes">(.*?)</section>', html, re.S).group(1)
    pastas = re.findall(r'name="pasta" value="([^"]+)"', sec)
    assert pastas == [str(nova), str(velha)]  # só importáveis, mais recente primeiro
    assert "7 mensagens" in sec and "outro chat" in sec and "exportação ilegível" in sec
    vazio = TestClient(criar_app(config_teste, engine, pastas_exportacao=[tmp_path / "nada"]), base_url=BASE_URL)
    html = vazio.get("/importar").text
    assert "Exportar histórico" in html and 'name="pasta"' in html  # instrução + campo manual


# --- 005: tags e grupos de documento ---------------------------------------------------
def secao_tags(html):
    m = re.search(r'<nav aria-label="Tags"[^>]*>(.*?)</nav>', html, re.S)
    return m and [(href, bool(cur), rot.strip(), int(n)) for href, cur, rot, n in re.findall(
        r'<a href="([^"]*)"( aria-current="page")?[^>]*>([^<]*)<span class="n">(\d+)</span></a>', m.group(1))]


def test_secao_de_tags_e_filtro(cliente, sessao):
    assert secao_tags(cliente.get("/").text) is None  # sem tags, sem seção
    salvar_ao_vivo(sessao, nota(1, texto="bolo #receita", tipo="foto", arquivo_caminho=None))
    salvar_ao_vivo(sessao, nota(2, texto="pão #receita #cozinha"))
    salvar_ao_vivo(sessao, nota(3, texto="#trabalho"))
    t = secao_tags(cliente.get("/").text)
    assert [(r, n) for _, _, r, n in t] == [("#receita", 2), ("#cozinha", 1), ("#trabalho", 1)]
    html = cliente.get("/?tag=receita").text
    assert "bolo" in html and "pão" in html and "#trabalho</a>" not in html.split('aria-label="Tags"')[0]
    assert [r for _, cur, r, _ in secao_tags(html) if cur] == ["#receita"]
    assert [href for href, cur, _, _ in secao_tags(html) if cur] == ["/"]  # clicar de novo desmarca
    assert all("tag=receita" in href for href, _, _, _ in categorias(html))  # categorias preservam a tag
    assert "bolo" not in cliente.get("/?tag=receita&tipo=texto").text
    assert re.search(r'<input type="hidden" id="f-tag" name="tag" value="receita"', html)
    cartao_pao = re.search(r'<article class="cartao nota tipo-texto">(.*?)</article>', html, re.S).group(1)
    assert re.search(r'<a class="etiqueta" href="/\?tag=receita">#receita</a>', cartao_pao)
    assert "Nenhuma nota nesta categoria" in cliente.get("/?tag=inexistente").text


def test_grupos_de_documento_no_painel(cliente, sessao):
    for mid, nome in enumerate(["a.pdf", "b.pdf", "c.xlsx", "d.zip"], start=1):
        salvar_ao_vivo(sessao, nota(mid, tipo="documento", arquivo_nome=nome, texto=f"doc {nome}"))
    assert 'aria-label="Tipos de arquivo"' not in cliente.get("/").text
    html = cliente.get("/?tipo=documento").text
    nav = re.search(r'<nav aria-label="Tipos de arquivo"[^>]*>(.*?)</nav>', html, re.S).group(1)
    assert re.findall(r">([^<]+)</a>", nav) == ["Todos", "PDF (2)", "Planilhas (1)", "Compactados (1)"]
    html = cliente.get("/?tipo=documento&grupo=pdf").text
    assert "doc a.pdf" in html and "doc c.xlsx" not in html
