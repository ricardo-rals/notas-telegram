"""Sincronização pela API MTProto oficial (Telethon), logada na conta do dono, só leitura (009).

    uv run --env-file .env python -m notas.sincronizacao login   # uma vez: telefone + código
    uv run --env-file .env python -m notas.sincronizacao         # sincroniza pelo terminal

Lê só o grupo configurado, a partir da maior mensagem já salva. Cada mensagem é convertida no
formato da API de bots e passa pelo mesmo `processar_mensagem` da captura ao vivo, para as regras
serem idênticas (FR-002). O cliente nunca envia, edita ou apaga nada (Princípio VII).
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from telethon.tl import types as t

from notas.bot import processar_mensagem
from notas.config import Config, ErroConfig, carregar
from notas.db import Nota, criar_engine, exigir_revisao_atual
from notas.repositorio import ImportacaoEmAndamento, concluir_importacao, iniciar_importacao

log = logging.getLogger("notas.sincronizacao")


class SemConfiguracao(Exception):
    """Falta TELEGRAM_API_ID/HASH ou o login; a mensagem diz o que fazer (FR-006)."""


# --- Telethon → dicionário da API de bots ---------------------------------------------
def _unix(d) -> int | None:
    return int(d.timestamp()) if d else None


def _entidades(lista) -> list[dict]:
    r = []
    for e in lista or []:
        if isinstance(e, t.MessageEntityUrl):
            r.append({"type": "url", "offset": e.offset, "length": e.length})
        elif isinstance(e, t.MessageEntityTextUrl):
            r.append({"type": "text_link", "offset": e.offset, "length": e.length, "url": e.url})
    return r


def _arquivo(m, uid, tamanho, nome=None, mime=None) -> dict:
    return {"file_id": f"tg:{m.id}", "file_unique_id": str(uid), "file_size": tamanho,
            "file_name": nome, "mime_type": mime}


def _tamanho_foto(s) -> int:
    return max(s.sizes) if isinstance(s, t.PhotoSizeProgressive) else getattr(s, "size", 0) or 0


def _midia(m) -> dict:
    """Chaves de mídia no formato da API de bots (o resto das regras fica em `normalizar_bot_api`)."""
    md = m.media
    if md is None or isinstance(md, t.MessageMediaWebPage):  # prévia de link = mensagem de texto
        return {}
    if isinstance(md, t.MessageMediaPhoto) and isinstance(md.photo, t.Photo):
        maior = max(md.photo.sizes, key=_tamanho_foto)
        return {"photo": [_arquivo(m, md.photo.id, _tamanho_foto(maior)) | {"width": getattr(maior, "w", 0),
                                                                          "height": getattr(maior, "h", 0)}]}
    if isinstance(md, t.MessageMediaDocument) and isinstance(md.document, t.Document):
        d = md.document
        attrs = {type(a): a for a in d.attributes}
        nome = getattr(attrs.get(t.DocumentAttributeFilename), "file_name", None)
        arq = _arquivo(m, d.id, d.size, nome, d.mime_type)
        audio, video = attrs.get(t.DocumentAttributeAudio), attrs.get(t.DocumentAttributeVideo)
        if t.DocumentAttributeSticker in attrs:
            return {"sticker": {**arq, "emoji": attrs[t.DocumentAttributeSticker].alt}}
        if t.DocumentAttributeAnimated in attrs:
            return {"animation": arq}
        if audio:
            return {"voice": arq} if audio.voice else {"audio": arq}
        if video:
            return {"video_note": arq} if video.round_message else {"video": arq}
        return {"document": arq}
    if isinstance(md, (t.MessageMediaGeo, t.MessageMediaGeoLive)):
        return {"location": {"latitude": md.geo.lat, "longitude": md.geo.long}}
    if isinstance(md, t.MessageMediaVenue):
        return {"venue": {"location": {"latitude": md.geo.lat, "longitude": md.geo.long}, "title": md.title}}
    if isinstance(md, t.MessageMediaContact):
        return {"contact": {"first_name": md.first_name, "last_name": md.last_name, "phone_number": md.phone_number}}
    if isinstance(md, t.MessageMediaPoll):
        q = md.poll.question
        return {"poll": {"question": getattr(q, "text", q)}}
    if isinstance(md, t.MessageMediaDice):
        return {"dice": {"emoji": md.emoticon}}
    return {"game": {}}  # mídia que a API de bots não tem: nota "outro", nunca descartada (001)


def para_bot_api(m, chat_id: int) -> dict:
    midia = _midia(m)
    chave_texto, chave_ent = ("caption", "caption_entities") if midia else ("text", "entities")
    d = {
        "message_id": m.id,
        "date": _unix(m.date),
        "chat": {"id": chat_id, "type": "supergroup"},
        "from": {"id": m.from_id.user_id} if isinstance(m.from_id, t.PeerUser) else None,
        chave_texto: m.message or "",
        chave_ent: _entidades(m.entities),
        **midia,
    }
    if m.edit_date:
        d["edit_date"] = _unix(m.edit_date)
    return d


# --- Sincronizar ---------------------------------------------------------------------------
async def sincronizar(imp_id: int, cliente, engine: Engine, cfg: Config) -> None:
    """Lê as mensagens depois da maior salva e grava pelas regras da captura ao vivo (FR-001/002)."""
    mapa: dict[int, object] = {}
    contagem = {"criadas": 0, "ignoradas": 0, "falhas": 0}

    async def baixar(ref: str, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        await cliente.download_media(mapa[int(ref.removeprefix("tg:"))], file=str(destino))

    with Session(engine) as sessao:
        try:
            ultima = sessao.scalar(select(func.max(Nota.message_id)).where(Nota.chat_id == cfg.chat_id)) or 0
            async with cliente:
                grupo = await cliente.get_entity(t.PeerChannel(int(str(cfg.chat_id).removeprefix("-100"))))
                async for m in cliente.iter_messages(grupo, min_id=ultima, reverse=True):
                    if isinstance(m, t.MessageService):
                        contagem["ignoradas"] += 1
                        continue
                    mapa[m.id] = m
                    d = para_bot_api(m, cfg.chat_id)
                    if (d["from"] or {}).get("id") != cfg.user_id:
                        contagem["ignoradas"] += 1
                        continue
                    await processar_mensagem(d, sessao, cfg, baixar, origem="sincronizacao")
                    situacao = sessao.scalar(select(Nota.situacao).where(
                        Nota.chat_id == cfg.chat_id, Nota.message_id == m.id))
                    contagem["falhas" if situacao == "falha" else "criadas"] += 1
                    mapa.pop(m.id, None)
        except Exception as e:
            sessao.rollback()
            concluir_importacao(sessao, imp_id, "falha", contagem, erro=f"{type(e).__name__}: {e}")
            raise
        concluir_importacao(sessao, imp_id, "concluida", contagem)


# --- Cliente real -----------------------------------------------------------------------------
def o_que_falta(cfg: Config) -> str | None:
    """Mensagem para o dono quando a sincronização ainda não pode rodar (FR-006)."""
    if not (cfg.api_id and cfg.api_hash):
        return "Configure TELEGRAM_API_ID e TELEGRAM_API_HASH no .env (crie em my.telegram.org)."
    if not Path(f"{cfg.telegram_sessao}.session").is_file():
        return "Faça o login uma vez: uv run --env-file .env python -m notas.sincronizacao login"
    return None


def criar_cliente(cfg: Config, exigir_login: bool = True):
    falta = o_que_falta(cfg)
    if falta and (exigir_login or not (cfg.api_id and cfg.api_hash)):
        raise SemConfiguracao(falta)
    from telethon import TelegramClient

    cfg.telegram_sessao.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(cfg.telegram_sessao), cfg.api_id, cfg.api_hash)


def executar(imp_id: int, engine: Engine, cfg: Config) -> None:
    """Para a thread do painel: um loop asyncio só desta sincronização."""
    asyncio.run(sincronizar(imp_id, criar_cliente(cfg), engine, cfg))


async def _login(cliente) -> str:
    """Pede telefone, código e, se houver, a senha de duas etapas; devolve o nome da conta."""
    async with cliente:
        eu = await cliente.get_me()
        return eu.first_name


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        cfg = carregar()
    except ErroConfig as e:
        raise SystemExit(f"Configuração inválida: {e}") from None
    if sys.argv[1:] == ["login"]:
        try:
            cliente = criar_cliente(cfg, exigir_login=False)
        except SemConfiguracao as e:
            raise SystemExit(str(e)) from None
        print(f"Login feito como {asyncio.run(_login(cliente))}. Sessão em {cfg.telegram_sessao}.session")
        return
    engine = criar_engine(cfg.database_url)
    exigir_revisao_atual(engine)
    with Session(engine) as sessao:
        try:
            imp_id = iniciar_importacao(sessao, "Telegram (sincronização)", "sincronizacao")
        except ImportacaoEmAndamento as e:
            raise SystemExit(f"Sincronização recusada: {e}") from None
    try:
        executar(imp_id, engine, cfg)
    except SemConfiguracao as e:
        raise SystemExit(str(e)) from None
    with Session(engine) as sessao:
        from notas.db import Importacao

        imp = sessao.get(Importacao, imp_id)
        print(f"criadas: {imp.criadas}  ignoradas: {imp.ignoradas}  falhas: {imp.falhas}")


if __name__ == "__main__":
    main()
