"""Regras determinísticas (Princípio II). Sem import de Telegram nem de banco: só dicionários.

Cada fonte (Bot API ao vivo, exportação do Telegram Desktop) tem um adaptador que produz
MensagemNormalizada; `classificar` é a mesma para as duas (FR-018).
"""

import mimetypes
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath

URL = re.compile(r"https?://\S+", re.IGNORECASE)
LIMITE_DOWNLOAD = 20 * 1024 * 1024
# Bot API: tipos que não são foto/áudio/vídeo/documento viram "outro" (animação antes de documento!)
OUTROS_BOT_API = ("animation", "sticker", "video_note", "poll", "dice", "game", "story", "paid_media")


@dataclass(frozen=True)
class MensagemNormalizada:
    chat_id: int
    message_id: int
    remetente_id: int | None
    enviada_em: str
    editada_em: str | None
    texto: str = ""
    tem_url: bool = False
    midia: str | None = None  # foto | audio | video | documento | outro
    midia_tamanho: int | None = None
    midia_nome: str | None = None
    midia_ext: str = ""
    midia_ref: str | None = None  # file_id (Bot API) ou caminho relativo (exportação)
    midia_uid: str | None = None
    localizacao: tuple[float, float] | None = None
    contato: tuple[str, str] | None = None


@dataclass(frozen=True)
class Classificacao:
    tipo: str
    texto: str


def iso_utc(unix: int | float | str) -> str:
    return datetime.fromtimestamp(int(unix), UTC).isoformat(timespec="seconds")


def _ext(nome: str | None, mime: str | None, padrao: str = "") -> str:
    if nome and PurePath(nome).suffix:
        return PurePath(nome).suffix.lower()
    return padrao or (mimetypes.guess_extension(mime) if mime else None) or ""


def _tem_url(texto: str, entidades: list | None) -> bool:
    if entidades is not None:
        return any(e.get("type") in ("url", "text_link", "link") for e in entidades)
    return bool(URL.search(texto))


def normalizar_bot_api(d: dict) -> MensagemNormalizada:
    texto = d.get("text") or d.get("caption") or ""
    entidades = d.get("entities", d.get("caption_entities"))
    campos: dict = {}

    outro = next((k for k in OUTROS_BOT_API if k in d), None)
    if outro:
        campos["midia"] = "outro"
        texto = texto or d.get("poll", {}).get("question", "") or d.get("sticker", {}).get("emoji", "")
    elif "photo" in d:
        maior = max(d["photo"], key=lambda p: p.get("file_size") or p.get("width", 0) * p.get("height", 0))
        campos.update(midia="foto", midia_ext=".jpg", f=maior)
    elif "voice" in d:
        campos.update(midia="audio", midia_ext=".ogg", f=d["voice"])
    elif "audio" in d:
        campos.update(midia="audio", f=d["audio"])
    elif "video" in d:
        campos.update(midia="video", f=d["video"])
    elif "document" in d:
        campos.update(midia="documento", f=d["document"])
    elif "location" in d or "venue" in d:
        loc = d.get("location") or d["venue"]["location"]
        campos["localizacao"] = (float(loc["latitude"]), float(loc["longitude"]))
    elif "contact" in d:
        c = d["contact"]
        nome = f"{c.get('first_name', '')} {c.get('last_name') or ''}".strip()
        campos["contato"] = (nome, c.get("phone_number", ""))

    if f := campos.pop("f", None):
        campos.update(
            midia_tamanho=f.get("file_size"),
            midia_nome=f.get("file_name"),
            midia_ext=campos.get("midia_ext") or _ext(f.get("file_name"), f.get("mime_type")),
            midia_ref=f["file_id"],
            midia_uid=f["file_unique_id"],
        )

    return MensagemNormalizada(
        chat_id=int(d["chat"]["id"]),
        message_id=int(d["message_id"]),
        remetente_id=(d.get("from") or {}).get("id"),
        enviada_em=iso_utc(d["date"]),
        editada_em=iso_utc(d["edit_date"]) if d.get("edit_date") else None,
        texto=texto,
        tem_url=_tem_url(texto, entidades),
        **campos,
    )


def classificar(m: MensagemNormalizada) -> Classificacao:
    if m.midia:
        return Classificacao(m.midia, m.texto)
    if m.localizacao:
        return Classificacao("localizacao", f"{m.localizacao[0]}, {m.localizacao[1]}")
    if m.contato:
        return Classificacao("contato", ", ".join(p for p in m.contato if p))
    if m.tem_url:
        return Classificacao("link", m.texto)
    if m.texto:
        return Classificacao("texto", m.texto)
    return Classificacao("outro", "")


def link_mensagem(chat_id: int, message_id: int) -> str:
    s = str(chat_id)
    if not s.startswith("-100"):
        raise ValueError(f"chat {chat_id} não é supergrupo; não há link para mensagens")
    return f"https://t.me/c/{s[4:]}/{message_id}"


def e_do_dono(m: MensagemNormalizada, chat_id: int, user_id: int) -> bool:
    return m.chat_id == chat_id and m.remetente_id == user_id


def deve_baixar(m: MensagemNormalizada) -> bool | None:
    """True = baixar; False = grande demais; None = não se baixa (sem mídia, vídeo, outro)."""
    if m.midia not in ("foto", "audio", "documento"):
        return None
    return m.midia_tamanho is None or m.midia_tamanho <= LIMITE_DOWNLOAD


# --- Exportação JSON do Telegram Desktop (result.json) -----------------------------------
NAO_INCLUIDO = "(File not included"
MEDIA_TYPE_EXPORT = {
    "voice_message": "audio", "audio_file": "audio", "video_file": "video",
    "video_message": "outro", "animation": "outro", "sticker": "outro",
}


def chat_id_exportacao(id_export: int) -> int:
    """A exportação grava o supergrupo sem o prefixo -100."""
    return int(f"-100{id_export}") if id_export > 0 else id_export


def _texto_exportacao(item: dict) -> str:
    if item.get("text_entities"):
        return "".join(e.get("text", "") for e in item["text_entities"])
    t = item.get("text", "")
    return t if isinstance(t, str) else "".join(p if isinstance(p, str) else p.get("text", "") for p in t)


def normalizar_exportacao(item: dict, chat_id: int) -> MensagemNormalizada:
    texto = _texto_exportacao(item)
    remetente = item.get("from_id") or ""
    campos: dict = {}

    if "photo" in item:
        ref, tamanho, nome, midia = item["photo"], item.get("photo_file_size"), None, "foto"
    elif "file" in item:
        ref, tamanho, nome = item["file"], item.get("file_size"), item.get("file_name")
        midia = MEDIA_TYPE_EXPORT.get(item.get("media_type"), "documento")
    else:
        ref = midia = None

    if midia == "outro" or "poll" in item:
        campos["midia"] = "outro"
        texto = texto or (item.get("poll") or {}).get("question", "") or item.get("sticker_emoji", "")
    elif midia:
        incluido = isinstance(ref, str) and not ref.startswith(NAO_INCLUIDO)
        campos.update(
            midia=midia,
            midia_tamanho=tamanho,
            midia_nome=nome,
            midia_ext=".jpg" if midia == "foto" else _ext(nome or (ref if incluido else None), item.get("mime_type")),
            midia_ref=ref if incluido else None,
        )
    elif "location_information" in item:
        loc = item["location_information"]
        campos["localizacao"] = (float(loc["latitude"]), float(loc["longitude"]))
    elif "contact_information" in item:
        c = item["contact_information"]
        nome_c = f"{c.get('first_name', '')} {c.get('last_name') or ''}".strip()
        campos["contato"] = (nome_c, c.get("phone_number", ""))

    return MensagemNormalizada(
        chat_id=chat_id,
        message_id=int(item["id"]),
        remetente_id=int(remetente[4:]) if remetente.startswith("user") else None,
        enviada_em=iso_utc(item["date_unixtime"]),
        editada_em=iso_utc(item["edited_unixtime"]) if item.get("edited_unixtime") else None,
        texto=texto,
        tem_url=_tem_url(texto, item.get("text_entities") or None),
        **campos,
    )
