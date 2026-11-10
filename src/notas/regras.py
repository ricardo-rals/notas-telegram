"""Regras determinísticas (Princípio II). Sem import de Telegram nem de banco: só dicionários.

Cada fonte (Bot API ao vivo, exportação do Telegram Desktop) tem um adaptador que produz
MensagemNormalizada; `classificar` é a mesma para as duas (FR-018).
"""

import ipaddress
from bisect import bisect_right
import mimetypes
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from urllib.parse import urlsplit

from publicsuffixlist import PublicSuffixList

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
    urls: tuple[str, ...] = ()
    posicoes: tuple[int, ...] = ()  # índice de cada URL no texto, paralelo a urls


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


# Pontuação que a regex pega colada no fim da URL ("veja https://a.com,").
FIM_URL = ".,;:!?)]}>'\""


def _urls(texto: str, entidades: list | None) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """URLs na ordem, sem repetir, e a posição (índice de caractere no texto) de cada uma.
    Serve às duas fontes: a Bot API marca `url`/`text_link` por offset/length (em UTF-16); a
    exportação marca `link` com `text` e `text_link` com `href`, sem offset (a posição é a soma
    dos trechos anteriores)."""
    achadas: list[tuple[str, int]] = []
    if entidades is None:
        achadas = [(m.group().rstrip(FIM_URL), m.start()) for m in URL.finditer(texto)]
    else:
        utf16 = texto.encode("utf-16-le")
        corrido = 0  # exportação: posição acumulada dos trechos
        for e in entidades:
            tipo = e.get("type")
            if "offset" in e:
                pos = len(utf16[: e["offset"] * 2].decode("utf-16-le", errors="ignore"))
            else:
                pos = corrido
                corrido += len(e.get("text", ""))
            if tipo == "text_link":
                achadas.append((e.get("url") or e.get("href") or "", pos))
            elif tipo == "url" and "offset" in e:
                ini, fim = e["offset"] * 2, (e["offset"] + e["length"]) * 2
                achadas.append((utf16[ini:fim].decode("utf-16-le", errors="ignore"), pos))
            elif tipo in ("url", "link"):
                achadas.append((e.get("text", ""), pos))
    vistas: dict[str, int] = {}
    for u, pos in achadas:
        limpa = u.strip()
        if limpa and limpa not in vistas:
            vistas[limpa] = pos + (len(u) - len(u.lstrip()))
    return tuple(vistas), tuple(vistas.values())


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
        **dict(zip(("urls", "posicoes"), _urls(texto, entidades))),
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
        **dict(zip(("urls", "posicoes"), _urls(texto, item.get("text_entities") or None))),
        **campos,
    )


# --- Sites dos links (002) ------------------------------------------------------------
PSL = PublicSuffixList()  # lista embutida no pacote; nunca baixada em execução (Princípio I)
ESQUEMA = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
SEM_SITE = ""  # "Sem site identificado"


def _legivel(label: str) -> str:
    if label.startswith("xn--"):
        try:
            return label.encode("ascii").decode("idna")
        except UnicodeError:
            return label
    return label


def site(url: str) -> str | None:
    """Domínio registrável da URL (`music.youtube.com` → `youtube.com`); IP e host sem ponto
    ficam como estão; None se não há host válido ou o host é só um sufixo (`com.br`)."""
    try:
        if not ESQUEMA.match(url):
            url = "http://" + url
        host = (urlsplit(url).hostname or "").rstrip(".")
        if not host:
            return None
        try:
            return str(ipaddress.ip_address(host))
        except ValueError:
            pass
        labels = [_legivel(lab) for lab in host.split(".")]
        if not all(lab and all(ch.isalnum() or ch == "-" for ch in lab) for lab in labels):
            return None
        host = ".".join(labels).lower()
        if "." not in host:
            return host
        return PSL.privatesuffix(host)
    except Exception:
        return None


# --- Itens de link e linhas do WhatsApp (003) -----------------------------------------
# "[12:40, 05/11/2026] Usuario: " ou "[05/11/2026, 12:40] Usuario: " (vírgula opcional)
WHATSAPP = re.compile(
    r"^\[(?:(?P<h1>\d{1,2}:\d{2}), (?P<d1>\d{1,2}/\d{1,2}/\d{4})"
    r"|(?P<d2>\d{1,2}/\d{1,2}/\d{4}),? (?P<h2>\d{1,2}:\d{2}))\] (?P<autor>[^:\n]{1,60}): "
)


@dataclass(frozen=True)
class ItemLink:
    posicao: int
    url: str
    site: str
    data: str
    autor: str | None


def linhas_whatsapp(texto: str) -> list[tuple[int, str | None, str | None]]:
    """Para cada linha: (índice de início, data ISO UTC, autor). Fora do padrão ou com data
    impossível → (início, None, None). A hora da linha é a do fuso do computador."""
    r, inicio = [], 0
    for linha in texto.split("\n"):
        data = autor = None
        if m := WHATSAPP.match(linha):
            try:
                local = datetime.strptime(f"{m['d1'] or m['d2']} {m['h1'] or m['h2']}", "%d/%m/%Y %H:%M")
                data = local.astimezone().astimezone(UTC).isoformat(timespec="seconds")
                autor = m["autor"].strip()
            except ValueError:
                pass
        r.append((inicio, data, autor))
        inicio += len(linha) + 1
    return r


def _itens(urls, posicoes, texto: str, enviada_em: str) -> list[ItemLink]:
    linhas = linhas_whatsapp(texto)
    inicios = [ini for ini, _, _ in linhas]
    itens = []
    for i, (url, pos) in enumerate(zip(urls, posicoes)):
        _, data, autor = linhas[max(bisect_right(inicios, pos) - 1, 0)]
        itens.append(ItemLink(i, url, site(url) or SEM_SITE, data or enviada_em, autor if data else None))
    return itens or [ItemLink(0, "", SEM_SITE, enviada_em, None)]


def itens_de_link(m: MensagemNormalizada) -> list[ItemLink]:
    """Um item por URL distinta, na ordem; nunca vazio (sentinela sem URL, FR-007 da 002)."""
    try:
        return _itens(m.urls, m.posicoes, m.texto, m.enviada_em)
    except Exception:
        return [ItemLink(0, "", SEM_SITE, m.enviada_em, None)]


def itens_do_texto(texto: str, enviada_em: str) -> list[ItemLink]:
    """Fallback para nota sem JSON original utilizável: só a regex sobre o texto."""
    try:
        return _itens(*_urls(texto or "", None), texto or "", enviada_em)
    except Exception:
        return [ItemLink(0, "", SEM_SITE, enviada_em, None)]


# --- 005: tags por hashtag e grupos de documento ---------------------------------------
HASHTAG = re.compile(r"(?<![\w#&])#(\w{1,40})(?![\w#])")


def tags(texto: str | None) -> list[str]:
    """Hashtags do texto, em minúsculas, sem repetição, na ordem em que aparecem (FR-001 da 005).
    URLs saem antes, para `/#secao` não virar tag."""
    sem_urls = URL.sub(" ", texto or "")
    vistas: dict[str, None] = {}
    for m in HASHTAG.finditer(sem_urls):
        nome = m[1].lower()
        if any(c.isalpha() for c in nome):
            vistas.setdefault(nome, None)
    return list(vistas)


GRUPOS_DOCUMENTO = {  # (valor, rótulo, extensões); a ordem é a dos botões
    "pdf": ("PDF", ("pdf",)),
    "planilha": ("Planilhas", ("xls", "xlsx", "ods", "csv")),
    "texto": ("Textos", ("doc", "docx", "odt", "txt", "rtf", "md")),
    "apresentacao": ("Apresentações", ("ppt", "pptx", "odp", "key")),
    "compactado": ("Compactados", ("zip", "rar", "7z", "tar", "gz")),
    "imagem": ("Imagens", ("jpg", "jpeg", "png", "gif", "webp", "heic", "svg")),
    "outro": ("Outros", ()),
}


def grupo_documento(nome: str | None) -> str:
    ext = (nome or "").rsplit(".", 1)[-1].lower() if "." in (nome or "") else ""
    return next((g for g, (_, exts) in GRUPOS_DOCUMENTO.items() if ext in exts), "outro")


# --- 008: período ------------------------------------------------------------------------
FUSO_LOCAL = None  # None = fuso do computador; os testes trocam por um fixo


def periodo_utc(valor: str | None, fim: bool) -> str | None:
    """`AAAA-MM-DD` (input date) no fuso local → ISO UTC, como as datas gravadas. O início é 00:00 e
    o fim é 23:59:59 do dia, para o período incluir os dois dias inteiros. Formato inválido levanta
    ValueError."""
    if not valor:
        return None
    dt = datetime.strptime(valor, "%Y-%m-%d")
    if fim:
        dt = dt.replace(hour=23, minute=59, second=59)
    dt = dt.replace(tzinfo=FUSO_LOCAL) if FUSO_LOCAL else dt.astimezone()
    return dt.astimezone(UTC).isoformat(timespec="seconds")
