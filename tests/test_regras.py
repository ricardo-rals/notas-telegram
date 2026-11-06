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
