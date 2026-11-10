"""009: sincronização pela API MTProto oficial (Telethon), só leitura. Tudo inventado, sem rede."""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from telethon.tl import types as t

from conftest import CHAT, DONO
from notas.db import Importacao, Nota
from notas.regras import classificar, normalizar_bot_api
from notas.repositorio import iniciar_importacao, salvar_ao_vivo
from notas.sincronizacao import para_bot_api, sincronizar

QUANDO = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
CANAL = int(str(CHAT)[4:])


def msg(mid, texto="", media=None, entidades=None, de=DONO, editada=None):
    return t.Message(id=mid, peer_id=t.PeerChannel(CANAL), date=QUANDO, message=texto, media=media,
                     entities=entidades, from_id=t.PeerUser(de) if de else None, edit_date=editada)


def doc(*atributos, mime="application/octet-stream", tamanho=1000, id_=77):
    return t.MessageMediaDocument(document=t.Document(
        id=id_, access_hash=0, file_reference=b"", date=QUANDO, mime_type=mime, size=tamanho, dc_id=1,
        attributes=list(atributos)))


def classe(m):
    n = normalizar_bot_api(para_bot_api(m, CHAT))
    return classificar(n), n


@pytest.mark.parametrize("m,tipo,texto", [
    (msg(1, "comprar pão"), "texto", "comprar pão"),
    (msg(2, "olha https://exemplo.com", entidades=[t.MessageEntityUrl(5, 19)]), "link", None),
    (msg(3, "clique aqui", entidades=[t.MessageEntityTextUrl(0, 11, "https://a.com")]), "link", None),
    (msg(4, "praia", media=t.MessageMediaPhoto(photo=t.Photo(
        id=9, access_hash=0, file_reference=b"", date=QUANDO, dc_id=1,
        sizes=[t.PhotoSize("m", 320, 240, 5000), t.PhotoSizeProgressive("y", 1280, 960, [1000, 90000])]))),
     "foto", "praia"),
    (msg(5, media=doc(t.DocumentAttributeAudio(duration=3, voice=True), mime="audio/ogg")), "audio", ""),
    (msg(6, media=doc(t.DocumentAttributeAudio(duration=200, title="Música"),
                      t.DocumentAttributeFilename("m.mp3"), mime="audio/mpeg")), "audio", ""),
    (msg(7, "filme", media=doc(t.DocumentAttributeVideo(duration=10, w=1, h=1), mime="video/mp4")), "video", "filme"),
    (msg(8, media=doc(t.DocumentAttributeVideo(duration=5, w=1, h=1, round_message=True), mime="video/mp4")),
     "outro", ""),
    (msg(9, media=doc(t.DocumentAttributeSticker(alt="😀", stickerset=t.InputStickerSetEmpty()),
                      mime="image/webp")), "outro", "😀"),
    (msg(10, "boleto", media=doc(t.DocumentAttributeFilename("boleto.pdf"), mime="application/pdf")),
     "documento", "boleto"),
    (msg(11, media=t.MessageMediaGeo(geo=t.GeoPoint(long=-46.6, lat=-23.5, access_hash=0))),
     "localizacao", "-23.5, -46.6"),
    (msg(12, media=t.MessageMediaVenue(geo=t.GeoPoint(long=1.5, lat=2.5, access_hash=0), title="Bar",
                                       address="Rua", provider="", venue_id="", venue_type="")),
     "localizacao", "2.5, 1.5"),
    (msg(13, media=t.MessageMediaContact(phone_number="+5511999", first_name="Maria", last_name="Silva",
                                         vcard="", user_id=0)), "contato", "Maria Silva, +5511999"),
    (msg(14, media=t.MessageMediaPoll(poll=t.Poll(id=1, question=t.TextWithEntities("Pizza?", []),
                                                  answers=[], hash=0), results=t.PollResults())),
     "outro", "Pizza?"),
    (msg(15, "veja https://site.com", entidades=[t.MessageEntityUrl(5, 16)],
         media=t.MessageMediaWebPage(webpage=t.WebPageEmpty(id=1))), "link", None),
])
def test_para_bot_api(m, tipo, texto):
    c, n = classe(m)
    assert c.tipo == tipo
    if texto is not None:
        assert c.texto == texto
    assert n.chat_id == CHAT and n.message_id == m.id and n.enviada_em == "2026-11-08T12:00:00+00:00"


def test_detalhes_de_midia():
    _, foto = classe(msg(4, media=t.MessageMediaPhoto(photo=t.Photo(
        id=9, access_hash=0, file_reference=b"", date=QUANDO, dc_id=1,
        sizes=[t.PhotoSize("m", 320, 240, 5000), t.PhotoSizeProgressive("y", 1280, 960, [1000, 90000])]))))
    assert (foto.midia_ref, foto.midia_uid, foto.midia_tamanho, foto.midia_ext) == ("tg:4", "9", 90000, ".jpg")
    _, pdf = classe(msg(10, media=doc(t.DocumentAttributeFilename("boleto.pdf"), mime="application/pdf",
                                      tamanho=30_000_000)))
    assert (pdf.midia_nome, pdf.midia_tamanho, pdf.midia_ext) == ("boleto.pdf", 30_000_000, ".pdf")
    sem_dono = para_bot_api(msg(20, "anônimo", de=None), CHAT)
    assert sem_dono["from"] is None or "id" not in (sem_dono["from"] or {})
    editada = para_bot_api(msg(21, "x", editada=QUANDO), CHAT)
    assert editada["edit_date"] == int(QUANDO.timestamp())


# --- sincronizar ---------------------------------------------------------------------------
class ClienteFalso:
    """Imita o pedaço do TelegramClient que a sincronização usa (só leitura)."""

    def __init__(self, mensagens, falhar_em=None):
        self.mensagens, self.falhar_em = mensagens, falhar_em
        self.pedidos, self.baixados = [], []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get_entity(self, peer):
        assert peer == t.PeerChannel(CANAL)  # nunca outro chat (FR-003)
        return "grupo"

    async def iter_messages(self, entidade, min_id=0, reverse=False):
        self.pedidos.append((entidade, min_id, reverse))
        for m in sorted(self.mensagens, key=lambda x: x.id):
            if m.id > min_id:
                if m.id == self.falhar_em:
                    raise ConnectionError("rede caiu")
                yield m

    async def download_media(self, m, file):
        self.baixados.append(m.id)
        with open(file, "wb") as f:
            f.write(b"conteudo")
        return file


def rodar(sessao, engine, cfg, cliente):
    imp = iniciar_importacao(sessao, "Telegram", "sincronizacao")
    try:
        asyncio.run(sincronizar(imp, cliente, engine, cfg))
    except ConnectionError:
        pass  # a falha fica registrada na importação; quem chama (thread do painel) só loga
    sessao.expire_all()
    return sessao.get(Importacao, imp)


def dados(mid):
    return {"chat_id": CHAT, "message_id": mid, "enviada_em": "2026-11-01T00:00:00+00:00", "editada_em": None,
            "tipo": "texto", "texto": "antiga", "link": "l", "arquivo_caminho": None, "arquivo_nome": None,
            "arquivo_tamanho": None, "situacao": "ok", "erro": None, "bruto": None}


def test_sincronizar(sessao, engine, config_teste):
    salvar_ao_vivo(sessao, dados(120))
    cliente = ClienteFalso([
        msg(100, "antes da última"),
        msg(121, "nova #receita"),
        msg(122, "de outra pessoa", de=999),
        t.MessageService(id=123, peer_id=t.PeerChannel(CANAL), date=QUANDO, action=t.MessageActionPinMessage()),
        msg(124, "foto", media=t.MessageMediaPhoto(photo=t.Photo(
            id=5, access_hash=0, file_reference=b"", date=QUANDO, dc_id=1, sizes=[t.PhotoSize("m", 1, 1, 10)]))),
        msg(125, "vídeo", media=doc(t.DocumentAttributeVideo(duration=1, w=1, h=1), mime="video/mp4")),
    ])
    imp = rodar(sessao, engine, config_teste, cliente)
    assert cliente.pedidos == [("grupo", 120, True)]
    assert (imp.status, imp.criadas, imp.ignoradas, imp.falhas) == ("concluida", 3, 2, 0)
    notas = {n.message_id: n for n in sessao.scalars(select(Nota))}
    assert sorted(notas) == [120, 121, 124, 125]
    assert {notas[m].origem for m in (121, 124, 125)} == {"sincronizacao"}
    assert notas[124].arquivo_caminho == "124_5.jpg" and (config_teste.media_dir / "124_5.jpg").is_file()
    assert cliente.baixados == [124]  # vídeo não é baixado (001)
    # segunda vez: nada novo (SC-002)
    cliente2 = ClienteFalso(cliente.mensagens)
    imp2 = rodar(sessao, engine, config_teste, cliente2)
    assert cliente2.pedidos == [("grupo", 125, True)] and imp2.criadas == 0


def test_caderno_vazio_pega_tudo_e_erro_no_meio_mantem_o_que_veio(sessao, engine, config_teste):
    cliente = ClienteFalso([msg(1, "um"), msg(2, "dois"), msg(3, "três")], falhar_em=3)
    imp = rodar(sessao, engine, config_teste, cliente)
    assert cliente.pedidos[0][1] == 0
    assert imp.status == "falha" and "rede caiu" in imp.erro and imp.criadas == 2
    assert sorted(sessao.scalars(select(Nota.message_id))) == [1, 2]
    cliente2 = ClienteFalso([msg(1, "um"), msg(2, "dois"), msg(3, "três")])
    imp2 = rodar(sessao, engine, config_teste, cliente2)
    assert cliente2.pedidos[0][1] == 2 and imp2.criadas == 1  # continua de onde parou
