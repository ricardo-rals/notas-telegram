import pytest

from conftest import CHAT, carregar_fixture
from notas.regras import classificar, link_mensagem, normalizar_bot_api


def tipo_texto(nome):
    c = classificar(normalizar_bot_api(carregar_fixture(f"bot_api/{nome}.json")))
    return c.tipo, c.texto


@pytest.mark.parametrize(
    "nome, tipo, texto",
    [
        ("texto", "texto", "comprar pão"),
        ("link_entidade", "link", "olha isso https://exemplo.com"),
        ("link_text_link", "link", "veja aqui"),
        ("foto_legenda", "foto", "quadro da reunião"),
        ("voz", "audio", ""),
        ("audio", "audio", ""),
        ("video", "video", "vídeo curto"),
        ("documento_pequeno", "documento", ""),
        ("animacao", "outro", ""),
        ("figurinha", "outro", "👍"),
        ("nota_video", "outro", ""),
        ("enquete", "outro", "almoço onde?"),
        ("localizacao", "localizacao", "-23.55052, -46.633308"),
        ("venue", "localizacao", "-22.9068, -43.1729"),
        ("contato", "contato", "Fulano de Tal, +5511999990000"),
        ("encaminhada", "texto", "encaminhei isso"),
    ],
)
def test_classificacao(nome, tipo, texto):
    assert tipo_texto(nome) == (tipo, texto)


def test_url_sem_entidades_cai_na_regex():
    d = carregar_fixture("bot_api/texto.json") | {"text": "anota http://a.b/c"}
    assert tipo_texto_d(d) == "link"


def tipo_texto_d(d):
    return classificar(normalizar_bot_api(d)).tipo


def test_mensagem_vazia_e_outro():
    d = carregar_fixture("bot_api/texto.json")
    del d["text"]
    assert tipo_texto_d(d) == "outro"


def test_normalizacao_basica():
    m = normalizar_bot_api(carregar_fixture("bot_api/foto_legenda.json"))
    assert m.chat_id == CHAT and m.remetente_id == 111
    assert m.enviada_em.startswith("2025-11-05T10:00") and m.enviada_em.endswith("+00:00")
    assert m.editada_em is None
    assert m.midia == "foto" and m.midia_tamanho == 3_000_000 and m.midia_uid == "FOTO1"


def test_animacao_nao_vira_documento():
    m = normalizar_bot_api(carregar_fixture("bot_api/animacao.json"))
    assert m.midia == "outro" and m.midia_ref is None


def test_link_mensagem():
    assert link_mensagem(-1001234567890, 42) == "https://t.me/c/1234567890/42"
    with pytest.raises(ValueError):
        link_mensagem(-12345, 42)


# --- US4: só o dono -------------------------------------------------------------
from notas.regras import e_do_dono  # noqa: E402


@pytest.mark.parametrize(
    "nome, esperado",
    [("texto", True), ("encaminhada", True), ("outro_usuario", False), ("outro_chat", False), ("admin_anonimo", False)],
)
def test_e_do_dono(nome, esperado):
    m = normalizar_bot_api(carregar_fixture(f"bot_api/{nome}.json"))
    assert e_do_dono(m, CHAT, 111) is esperado


# --- US5: exportação do Telegram Desktop ----------------------------------------------
from notas.regras import normalizar_exportacao  # noqa: E402


def itens_exportacao():
    return {m["id"]: m for m in carregar_fixture("exportacao_ok/result.json")["messages"]}


@pytest.mark.parametrize(
    "export_id, bot_api",
    [(101, "texto"), (102, "link_entidade"), (103, "foto_legenda"), (104, "voz"),
     (106, "video"), (107, "localizacao"), (108, "contato"), (109, "figurinha")],
)
def test_exportacao_classifica_igual_a_bot_api(export_id, bot_api):
    exp = classificar(normalizar_exportacao(itens_exportacao()[export_id], CHAT))
    viva = classificar(normalizar_bot_api(carregar_fixture(f"bot_api/{bot_api}.json")))
    assert exp.tipo == viva.tipo
    if bot_api not in ("voz",):
        assert exp.texto == viva.texto


def test_exportacao_documento_datas_e_remetente():
    itens = itens_exportacao()
    doc = normalizar_exportacao(itens[105], CHAT)
    assert (classificar(doc).tipo, doc.midia_ref, doc.midia_nome) == ("documento", "files/boleto.pdf", "boleto.pdf")
    ed = normalizar_exportacao(itens[110], CHAT)
    assert ed.enviada_em.endswith("+00:00") and ed.editada_em is not None
    assert ed.chat_id == CHAT and ed.remetente_id == 111
    assert normalizar_exportacao(itens[201], CHAT).remetente_id == 222


def test_exportacao_arquivo_nao_incluido():
    item = carregar_fixture("exportacao_sem_midia/result.json")["messages"][0]
    m = normalizar_exportacao(item, CHAT)
    assert m.midia == "foto" and m.midia_ref is None


# --- 002: sites dos links ------------------------------------------------------------
from notas.regras import itens_de_link, site  # noqa: E402


@pytest.mark.parametrize(
    "url, esperado",
    [
        ("https://www.youtube.com/x", "youtube.com"),
        ("https://m.youtube.com", "youtube.com"),
        ("https://music.youtube.com", "youtube.com"),
        ("HTTPS://YouTube.COM:8080/a", "youtube.com"),
        ("https://pt.wikipedia.org", "wikipedia.org"),
        ("https://folha.uol.com.br/a", "uol.com.br"),
        ("http://exemplo.co.uk", "exemplo.co.uk"),
        ("https://fulano.github.io/p", "fulano.github.io"),
        ("https://www.m.exemplo.com", "exemplo.com"),
        ("http://exemplo.com./", "exemplo.com"),
        ("exemplo.com.br/x", "exemplo.com.br"),
        ("http://192.168.0.1:8000", "192.168.0.1"),
        ("http://[::1]/", "::1"),
        ("http://localhost:3000", "localhost"),
        ("https://xn--bcher-kva.de", "bücher.de"),
        ("https://www.BÜCHER.de", "bücher.de"),
        ("http://com.br", None),
        ("http://", None),
        ("https://", None),
        ("não é url", None),
    ],
)
def test_site(url, esperado):
    assert site(url) == esperado


def urls_bot(nome):
    return normalizar_bot_api(carregar_fixture(f"bot_api/{nome}.json")).urls


@pytest.mark.parametrize(
    "nome, urls",
    [
        ("link_entidade", ("https://exemplo.com",)),
        ("link_text_link", ("https://exemplo.com/x",)),
        ("link_varios_sites", ("https://www.youtube.com/a", "https://m.youtube.com/b", "https://instagram.com/c")),
        ("link_sem_esquema", ("exemplo.com.br",)),
        ("link_idn", ("https://xn--bcher-kva.de/",)),
        ("texto", ()),
    ],
)
def test_urls_bot_api(nome, urls):
    assert urls_bot(nome) == urls


def test_urls_exportacao():
    msgs = carregar_fixture("exportacao_links/result.json")["messages"]
    assert [normalizar_exportacao(m, CHAT).urls for m in msgs] == [
        ("https://m.facebook.com/evento",), ("https://www.youtube.com/x",), (),
    ]


def test_urls_sem_entidades_e_repetidas():
    d = carregar_fixture("bot_api/texto.json") | {"text": "https://a.com e https://a.com"}
    assert normalizar_bot_api(d).urls == ("https://a.com",)


def test_url_sem_site_vira_item_sem_site():
    m = normalizar_bot_api(carregar_fixture("bot_api/texto.json") | {"text": "http://com.br https://a.com"})
    assert [(i.url, i.site) for i in itens_de_link(m)] == [("http://com.br", ""), ("https://a.com", "a.com")]


# --- 003: linhas do WhatsApp e itens de link -----------------------------------------
from datetime import UTC, datetime  # noqa: E402

from notas.regras import ItemLink, itens_de_link, itens_do_texto, linhas_whatsapp  # noqa: E402


def utc_local(*args):
    return datetime(*args).astimezone().astimezone(UTC).isoformat(timespec="seconds")


def test_linhas_whatsapp_formatos():
    esperado = (0, utc_local(2026, 11, 5, 12, 40), "Usuario")
    assert linhas_whatsapp("[12:40, 05/11/2026] Usuario: x")[0] == esperado
    assert linhas_whatsapp("[05/11/2026, 12:40] Usuario: x")[0] == esperado
    assert linhas_whatsapp("[05/11/2026 12:40] Usuario: x")[0] == esperado
    assert linhas_whatsapp("[12:40, 05/11/2026] Ana Maria: x")[0][2] == "Ana Maria"


def test_linhas_whatsapp_invalidas_e_inicio():
    texto = "[25:99, 31/02/2026] X: y\nsem prefixo\n[08:05, 01/01/2026] Bia: z"
    assert linhas_whatsapp(texto) == [
        (0, None, None), (25, None, None), (37, utc_local(2026, 1, 1, 8, 5), "Bia"),
    ]


def test_itens_mensagem_de_exemplo():
    m = normalizar_bot_api(carregar_fixture("bot_api/whatsapp_9_links.json"))
    itens = itens_de_link(m)
    assert [i.posicao for i in itens] == list(range(9))
    assert [i.site for i in itens] == ["i384100.net"] + ["instagram.com"] * 8
    assert all(i.autor == "Usuario" for i in itens)
    assert itens[0].data == utc_local(2026, 11, 5, 12, 40) and itens[8].data == utc_local(2026, 11, 5, 20, 41)
    assert itens[0].url == "https://imp.i384100.net/cbUijS"


def test_posicoes_com_emoji_e_text_link():
    m = normalizar_bot_api(carregar_fixture("bot_api/link_varios_sites.json"))
    assert [m.texto[p:p + 8] for p in m.posicoes] == ["https://"] * 3
    t = normalizar_bot_api(carregar_fixture("bot_api/link_text_link.json"))
    [item] = itens_de_link(t)
    assert (item.url, item.data, item.autor) == ("https://exemplo.com/x", t.enviada_em, None)


def test_itens_repetidos_mesma_linha_e_sentinela():
    base = carregar_fixture("bot_api/texto.json")
    m = normalizar_bot_api(base | {"text": "[10:00, 01/02/2026] Eu: https://a.com https://b.com https://a.com"})
    itens = itens_de_link(m)
    assert [i.url for i in itens] == ["https://a.com", "https://b.com"]
    assert itens[0].data == itens[1].data == utc_local(2026, 2, 1, 10, 0)
    vazio = normalizar_bot_api(base | {"text": "sem url nenhuma"})
    assert itens_de_link(vazio) == [ItemLink(0, "", "", vazio.enviada_em, None)]


def test_itens_do_texto():
    itens = itens_do_texto("https://a.com\nhttps://b.com", "2026-01-01T00:00:00+00:00")
    assert [(i.url, i.data) for i in itens] == [
        ("https://a.com", "2026-01-01T00:00:00+00:00"), ("https://b.com", "2026-01-01T00:00:00+00:00"),
    ]


def test_posicoes_exportacao():
    msgs = carregar_fixture("exportacao_links/result.json")["messages"]
    m = normalizar_exportacao(msgs[1], CHAT)  # "vídeo " + link
    assert m.posicoes == (6,)


# --- 005: tags e grupos de documento ---------------------------------------------------
from notas.regras import grupo_documento, tags  # noqa: E402


@pytest.mark.parametrize("texto,esperado", [
    ("pão de queijo #Receita #cozinha", ["receita", "cozinha"]),
    ("#trabalho: reunião", ["trabalho"]),
    ("(#ideia) e #ideia de novo, #IDEIA.", ["ideia"]),
    ("#reunião_2026 ok", ["reunião_2026"]),
    ("link https://site.com/pag#secao e https://a.com/?x=1#b", []),
    ("c# e a#b não; # sozinho; #123; ##dupla", []),
    ("#" + "a" * 41, []),
    ("#" + "a" * 40, ["a" * 40]),
    ("", []),
    (None, []),
])
def test_tags(texto, esperado):
    assert tags(texto) == esperado


@pytest.mark.parametrize("nome,grupo", [
    ("boleto.PDF", "pdf"), ("contas.xlsx", "planilha"), ("dados.csv", "planilha"),
    ("carta.docx", "texto"), ("notas.md", "texto"), ("aula.pptx", "apresentacao"),
    ("fotos.zip", "compactado"), ("backup.tar.gz", "compactado"), ("scan.heic", "imagem"),
    ("programa.exe", "outro"), ("sem_extensao", "outro"), (None, "outro"),
])
def test_grupo_documento(nome, grupo):
    assert grupo_documento(nome) == grupo
