import asyncio

from sqlalchemy import select

from conftest import carregar_fixture
from notas.bot import processar_mensagem
from notas.db import Nota


class BaixarFalso:
    def __init__(self, erro=None):
        self.chamadas = []
        self.erro = erro

    async def __call__(self, file_id, destino):
        self.chamadas.append((file_id, destino))
        if self.erro:
            raise self.erro
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"x")


def processar(nome_ou_dict, sessao, cfg, baixar=None):
    msg = carregar_fixture(f"bot_api/{nome_ou_dict}.json") if isinstance(nome_ou_dict, str) else nome_ou_dict
    baixar = baixar or BaixarFalso()
    asyncio.run(processar_mensagem(msg, sessao, cfg, baixar))
    return baixar


def notas(sessao):
    sessao.expire_all()
    return sessao.scalars(select(Nota).order_by(Nota.message_id)).all()


def test_foto_baixa_maior_tamanho(sessao, config_teste):
    b = processar("foto_legenda", sessao, config_teste)
    [(file_id, destino)] = b.chamadas
    assert file_id == "FFOTO1_l"
    n = notas(sessao)[0]
    assert n.arquivo_caminho == f"{n.message_id}_FOTO1.jpg"
    assert (config_teste.media_dir / n.arquivo_caminho).exists()
    assert (n.tipo, n.texto, n.situacao, n.origem) == ("foto", "quadro da reunião", "ok", "ao_vivo")
    assert n.link == f"https://t.me/c/1234567890/{n.message_id}"


def test_documento_grande_nao_baixa(sessao, config_teste):
    b = processar("documento_25mb", sessao, config_teste)
    assert b.chamadas == []
    n = notas(sessao)[0]
    assert (n.tipo, n.situacao, n.arquivo_caminho, n.arquivo_nome) == ("documento", "grande_demais", None, "grande.pdf")


def test_video_nunca_baixa(sessao, config_teste):
    b = processar("video", sessao, config_teste)
    assert b.chamadas == []
    assert notas(sessao)[0].situacao == "ok"


def test_documento_e_voz_mantem_extensao(sessao, config_teste):
    processar("documento_pequeno", sessao, config_teste)
    processar("voz", sessao, config_teste)
    por_tipo = {n.tipo: n for n in notas(sessao)}
    doc, voz = por_tipo["documento"], por_tipo["audio"]
    assert doc.arquivo_caminho.endswith("_doc1.pdf") and doc.arquivo_nome == "boleto.pdf"
    assert voz.arquivo_caminho.endswith("_voz1.ogg")


def test_falha_no_download_vira_nota_com_erro(sessao, config_teste):
    processar("foto_legenda", sessao, config_teste, BaixarFalso(erro=RuntimeError("rede caiu")))
    n = notas(sessao)[0]
    assert (n.tipo, n.texto, n.situacao) == ("foto", "quadro da reunião", "falha")
    assert "rede caiu" in n.erro and n.arquivo_caminho is None and n.bruto


def test_mensagem_ilegivel_vira_falha(sessao, config_teste):
    msg = carregar_fixture("bot_api/texto.json") | {"location": {"latitude": "x"}}
    processar(msg, sessao, config_teste)
    n = notas(sessao)[0]
    assert (n.situacao, n.tipo) == ("falha", "outro") and n.erro


def test_album_gera_uma_nota_por_item(sessao, config_teste):
    processar("album_1", sessao, config_teste)
    processar("album_2", sessao, config_teste)
    assert [n.tipo for n in notas(sessao)] == ["foto", "foto"]


# --- US3: edição --------------------------------------------------------------


def test_edicao_atualiza_a_mesma_nota(sessao, config_teste):
    processar("texto", sessao, config_teste)
    processar("editada_texto", sessao, config_teste)
    [n] = notas(sessao)
    assert n.texto == "comprar pão e leite" and n.editada_em and n.tipo == "texto"


def test_edicao_com_url_vira_link(sessao, config_teste):
    processar("texto", sessao, config_teste)
    processar("editada_com_url", sessao, config_teste)
    [n] = notas(sessao)
    assert n.tipo == "link"


def test_edicao_de_mensagem_nunca_capturada_cria_nota(sessao, config_teste):
    processar("editada_texto", sessao, config_teste)
    [n] = notas(sessao)
    assert n.texto == "comprar pão e leite"


def test_edicao_com_download_falhando_marca_falha(sessao, config_teste):
    processar("foto_legenda", sessao, config_teste)
    editada = carregar_fixture("bot_api/foto_legenda.json") | {"caption": "nova legenda", "edit_date": 1762337800}
    processar(editada, sessao, config_teste, BaixarFalso(erro=OSError("disco cheio")))
    [n] = notas(sessao)
    assert n.situacao == "falha" and "disco cheio" in n.erro and n.texto == "nova legenda"


# --- US4: ignorar o que não é meu --------------------------------------------------
import pytest  # noqa: E402


@pytest.mark.parametrize("nome", ["outro_usuario", "outro_chat", "admin_anonimo"])
def test_mensagens_de_terceiros_nao_geram_nada(sessao, config_teste, nome):
    processar(nome, sessao, config_teste)
    assert notas(sessao) == []


def test_terceiro_com_mensagem_ilegivel_tambem_nao_gera_falha(sessao, config_teste):
    msg = carregar_fixture("bot_api/outro_usuario.json") | {"location": {"latitude": "x"}}
    processar(msg, sessao, config_teste)
    assert notas(sessao) == []


# --- 002 US4 ------------------------------------------------------------------------
from notas.db import NotaSite  # noqa: E402


def sites(sessao, mid):
    sessao.expire_all()
    return set(sessao.scalars(
        select(NotaSite.site).join(Nota, Nota.id == NotaSite.nota_id).where(Nota.message_id == mid)
    ))


def test_link_grava_sites(sessao, config_teste):
    processar("link_varios_sites", sessao, config_teste)
    assert sites(sessao, 40) == {"youtube.com", "instagram.com"}


def test_edicao_troca_site(sessao, config_teste):
    processar("link_varios_sites", sessao, config_teste)
    msg = carregar_fixture("bot_api/link_varios_sites.json")
    t = "https://m.facebook.com/evento"
    msg |= {"text": t, "entities": [{"type": "url", "offset": 0, "length": len(t)}], "edit_date": 1762337000}
    processar(msg, sessao, config_teste)
    assert sites(sessao, 40) == {"facebook.com"}


def test_edicao_com_url_vira_link_com_site(sessao, config_teste):
    processar("editada_com_url", sessao, config_teste)
    n = notas(sessao)[0]
    assert n.tipo == "link" and sites(sessao, n.message_id) - {""}


def test_foto_com_url_na_legenda_sem_site(sessao, config_teste):
    msg = carregar_fixture("bot_api/foto_legenda.json") | {"caption": "https://a.com"}
    processar(msg, sessao, config_teste)
    assert sites(sessao, msg["message_id"]) == set()
