"""Prévia de links: título, descrição e miniatura que a página declara para compartilhamento.

Roda numa thread do painel (research R3 da 003), só com PREVIAS_LINKS=1 (Princípio I, item b).
Antes de cada acesso, inclusive a cada redirecionamento, o destino precisa resolver só para
IPs públicos (FR-009). Nada daqui é renderizado como HTML: o painel escapa tudo (FR-010).
"""

import hashlib
import ipaddress
import logging
import mimetypes
import re
import socket
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from sqlalchemy import Engine
from sqlalchemy.orm import Session

log = logging.getLogger("notas.previas")

USER_AGENT = "notas-telegram/0.3 (+previa de link)"
LIMITE_HTML = 512 * 1024
LIMITE_IMAGEM = 5 * 1024 * 1024
MAX_REDIRECIONAMENTOS = 5
TIMEOUT = 10.0
INTERVALO = 5.0
LOTE = 5


@dataclass(frozen=True)
class ResultadoPrevia:
    situacao: str  # ok | indisponivel
    definitiva: bool = False
    titulo: str | None = None
    descricao: str | None = None
    imagem: str | None = None  # relativo a MEDIA_DIR
    erro: str | None = None


class _Falha(Exception):
    def __init__(self, motivo: str, definitiva: bool = False):
        super().__init__(motivo)
        self.definitiva = definitiva


# --- Metadados -------------------------------------------------------------------------
TITULO = ("og:title", "twitter:title")
DESCRICAO = ("og:description", "twitter:description", "description")
IMAGEM = ("og:image", "og:image:url", "twitter:image")


class _Cabecalho(HTMLParser):
    """Coleta <meta property|name content> e o primeiro <title>; para no fim do <head>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas: dict[str, str] = {}
        self.titulo: str | None = None
        self._no_titulo = False
        self.fim = False

    def handle_starttag(self, tag, attrs):
        if self.fim:
            return
        a = dict(attrs)
        if tag == "meta":
            chave = (a.get("property") or a.get("name") or "").strip().lower()
            if chave and a.get("content") and chave not in self.metas:
                self.metas[chave] = a["content"]
        elif tag == "title" and self.titulo is None:
            self._no_titulo, self.titulo = True, ""
        elif tag == "body":
            self.fim = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._no_titulo = False
        elif tag == "head":
            self.fim = True

    def handle_data(self, data):
        if self._no_titulo and not self.fim:
            self.titulo += data


def _limpo(texto: str | None, limite: int) -> str | None:
    texto = " ".join((texto or "").split())
    return texto[:limite] or None


def extrair_metadados(html: str, base_url: str) -> dict:
    p = _Cabecalho()
    try:
        p.feed(html)
    except Exception:  # HTML quebrado: fica com o que já foi lido
        pass
    primeiro = lambda chaves: next((p.metas[c] for c in chaves if p.metas.get(c)), None)  # noqa: E731
    imagem = primeiro(IMAGEM)
    return {
        "titulo": _limpo(primeiro(TITULO) or p.titulo, 200),
        "descricao": _limpo(primeiro(DESCRICAO), 300),
        "imagem": urljoin(base_url, imagem.strip()) if imagem else None,
    }


# --- Rede ------------------------------------------------------------------------------
def destino_permitido(url: str, resolver=socket.getaddrinfo) -> bool:
    """Só http(s) e só se TODOS os IPs do host forem públicos (FR-009).
    ponytail: checar antes de conectar deixa a janela de DNS rebinding entre checagem e conexão;
    para caderno pessoal basta. Se precisar, um transport que conecta no IP já checado."""
    try:
        partes = urlsplit(url)
        if partes.scheme not in ("http", "https") or not partes.hostname:
            return False
        ips = {info[4][0] for info in resolver(partes.hostname, partes.port or 80, proto=socket.IPPROTO_TCP)}
        return bool(ips) and all(ipaddress.ip_address(ip.split("%")[0]).is_global for ip in ips)
    except Exception:
        return False


CHARSET_META = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.IGNORECASE)


def _obter(url: str, cliente: httpx.Client, resolver, limite: int, aceitos: tuple[str, ...]):
    """GET com redirecionamentos seguidos à mão, cada destino checado. Devolve
    (url final, content-type, até `limite` bytes, charset)."""
    for _ in range(MAX_REDIRECIONAMENTOS + 1):
        if not destino_permitido(url, resolver):
            raise _Falha("endereço local", definitiva=True)
        try:
            with cliente.stream("GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=False) as r:
                if r.is_redirect and "location" in r.headers:
                    url = urljoin(url, r.headers["location"])
                    continue
                if r.status_code != 200:
                    raise _Falha(f"HTTP {r.status_code}")
                tipo = r.headers.get("content-type", "").split(";")[0].strip().lower()
                if not tipo.startswith(aceitos):
                    raise _Falha(f"conteúdo {tipo or 'desconhecido'}", definitiva=True)
                corpo = bytearray()
                for pedaco in r.iter_bytes():
                    corpo += pedaco
                    if len(corpo) > limite:
                        break
                return url, tipo, bytes(corpo), r.charset_encoding, len(corpo) > limite
        except httpx.HTTPError as e:
            raise _Falha(type(e).__name__) from None
    raise _Falha("redirecionamentos demais")


def _imagem(url: str, cliente, resolver, media_dir: Path, chave: str) -> str | None:
    try:
        _, tipo, corpo, _, cortado = _obter(url, cliente, resolver, LIMITE_IMAGEM, ("image/",))
    except _Falha:
        return None
    if cortado:
        return None
    ext = mimetypes.guess_extension(tipo) or ".img"
    destino = media_dir / "previas" / f"{chave}{ext}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(corpo)
    return f"previas/{destino.name}"


def buscar_previa(url: str, cliente: httpx.Client, resolver, media_dir: Path) -> ResultadoPrevia:
    """Nunca levanta: toda falha vira `indisponivel` com o motivo (FR-008)."""
    try:
        final, _, corpo, charset, _ = _obter(url, cliente, resolver, LIMITE_HTML, ("text/html",))
        if not charset and (m := CHARSET_META.search(corpo[:2048])):
            charset = m.group(1).decode("ascii")
        try:
            html = corpo.decode(charset or "utf-8", errors="replace")
        except LookupError:
            html = corpo.decode("utf-8", errors="replace")
        meta = extrair_metadados(html, final)
        chave = hashlib.sha1(url.encode()).hexdigest()
        imagem = _imagem(meta["imagem"], cliente, resolver, media_dir, chave) if meta["imagem"] else None
        return ResultadoPrevia("ok", titulo=meta["titulo"], descricao=meta["descricao"], imagem=imagem)
    except _Falha as f:
        return ResultadoPrevia("indisponivel", definitiva=f.definitiva, erro=str(f))
    except Exception as e:
        return ResultadoPrevia("indisponivel", erro=type(e).__name__)


# --- Thread do painel ------------------------------------------------------------------
def rodar_fila(engine: Engine, media_dir: Path, parar: threading.Event, resolver=socket.getaddrinfo) -> None:
    """Laço: pega até LOTE prévias vencidas e busca uma de cada vez.
    ponytail: uma busca por vez (~1/s); depois de importar milhares de links demora. Se incomodar,
    um pool pequeno de threads."""
    from notas.repositorio import proximas_previas, registrar_previa

    with httpx.Client(timeout=TIMEOUT) as cliente:
        while not parar.is_set():
            try:
                with Session(engine) as sessao:
                    for url in proximas_previas(sessao, datetime.now(UTC), LOTE):
                        r = buscar_previa(url, cliente, resolver, media_dir)
                        registrar_previa(sessao, url, r, datetime.now(UTC))
            except Exception as e:  # banco ocupado etc.: tenta de novo no próximo ciclo
                log.warning("fila de prévias: %s", type(e).__name__)
            parar.wait(INTERVALO)


def iniciar_thread(engine: Engine, media_dir: Path) -> threading.Event:
    parar = threading.Event()
    threading.Thread(target=rodar_fila, args=(engine, media_dir, parar), name="previas", daemon=True).start()
    return parar
