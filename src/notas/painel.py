"""Painel local: `uv run --env-file .env python -m notas.painel` (sempre em 127.0.0.1)."""

import logging
import math
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from notas.config import Config, ErroConfig, carregar
from notas.db import TIPOS, Nota, criar_engine, exigir_revisao_atual
from notas.importacao import encontrar_exportacoes, executar
from notas import backup, sincronizacao
from notas.previas import iniciar_thread
from notas.regras import GRUPOS_DOCUMENTO, periodo_utc
from notas.repositorio import (
    POR_PAGINA,
    ImportacaoEmAndamento,
    buscar,
    buscar_links,
    contar_grupos_documento,
    contar_novas,
    contar_por_tipo,
    contar_tags,
    contar_sites,
    iniciar_importacao,
    links_das_notas,
    tags_das_notas,
    ultima_importacao,
)

AQUI = Path(__file__).parent
log = logging.getLogger("notas.painel")
HOST = "127.0.0.1"  # fixo: o painel nunca escuta em outra interface (Princípio IV)
ROTULOS = {
    "texto": "Texto", "link": "Link", "foto": "Foto", "audio": "Áudio", "video": "Vídeo",
    "documento": "Documento", "localizacao": "Localização", "contato": "Contato", "outro": "Outro",
}
CSP = ("default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; frame-ancestors 'none'")  # research R7 da 003: nada carregado de fora
ROTULOS_PLURAIS = {
    "texto": "textos", "link": "links", "foto": "fotos", "audio": "áudios", "video": "vídeos",
    "documento": "documentos", "localizacao": "localizações", "contato": "contatos", "outro": "outras",
}
PASTAS_EXPORTACAO = [Path.home() / "Downloads" / "Telegram Desktop", Path.home() / "Downloads"]


def href(q: str = "", tipo: str = "", site: str = "", pagina: int | None = None, tag: str = "", grupo: str = "",
         de: str = "", ate: str = "") -> str:
    """Endereço da lista só com os parâmetros preenchidos (FR-009 da 002)."""
    params = {"q": q, "tipo": tipo, "site": site, "tag": tag, "grupo": grupo, "de": de, "ate": ate, "pagina": pagina}
    query = urlencode({k: v for k, v in params.items() if v})
    return f"/?{query}" if query else "/"


def extensao(nome: str | None) -> str:
    """Selo do cartão de documento: "PDF", "XLSX"; sem extensão curta, "ARQ" (research R7 da 004)."""
    ext = Path(nome or "").suffix[1:]
    return ext.upper() if 0 < len(ext) <= 5 and ext.isalnum() else "ARQ"


def tamanho(n: int | None) -> str:
    if n is None:
        return ""
    for unidade, base in (("GB", 1024**3), ("MB", 1024**2)):
        if n >= base:
            return f"{n / base:.1f} {unidade}".replace(".", ",")
    return f"{round(n / 1024)} KB" if n >= 1024 else f"{n} B"


COORD = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def mapa(texto: str | None) -> str | None:
    """Link do OpenStreetMap para "lat, lon"; o painel nunca carrega o mapa (Princípio I)."""
    m = COORD.match(texto or "")
    if not m or abs(float(m[1])) > 90 or abs(float(m[2])) > 180:
        return None
    lat, lon = m[1], m[2]
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"


def contato(texto: str | None) -> tuple[str, str, str | None]:
    """(nome, telefone, href tel:) a partir de "nome, telefone" (FR-005 da 001)."""
    nome, _, tel = (texto or "").rpartition(",")
    if not nome:
        return (texto or "").strip(), "", None
    tel = tel.strip()
    digitos = re.sub(r"[^\d+]", "", tel)
    return nome.strip(), tel, f"tel:{digitos}" if digitos else None


def atalhos_periodo(q, tipo, site, tag, grupo) -> list[tuple[str, str]]:
    """Hoje, 7 dias, 30 dias e limpar (FR-004 da 008), no formato do input datetime-local."""
    agora = datetime.now()
    hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    fmt = "%Y-%m-%dT%H:%M"
    base = dict(q=q, tipo=tipo, site=site, tag=tag, grupo=grupo)
    return [
        ("Hoje", href(**base, de=hoje.strftime(fmt))),
        ("7 dias", href(**base, de=(agora - timedelta(days=7)).strftime(fmt))),
        ("30 dias", href(**base, de=(agora - timedelta(days=30)).strftime(fmt))),
        ("Limpar período", href(**base)),
    ]


def data_local(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def criar_app(cfg: Config, engine: Engine, iniciar_previas=iniciar_thread, pastas_exportacao=None,
              iniciar_backup=backup.iniciar_thread, sincronizar=None) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    hosts = {f"127.0.0.1:{cfg.painel_port}", f"localhost:{cfg.painel_port}"}
    origens = {f"http://{h}" for h in hosts}
    templates = Jinja2Templates(directory=AQUI / "templates")
    templates.env.filters["data_local"] = data_local
    for f in (extensao, tamanho, mapa, contato):
        templates.env.filters[f.__name__] = f
    pastas_exportacao = PASTAS_EXPORTACAO if pastas_exportacao is None else pastas_exportacao
    sincronizar = sincronizar or sincronizacao.executar

    @app.middleware("http")
    async def so_local(request: Request, call_next):
        # Host errado = DNS rebinding; Origin de outro site num POST = CSRF.
        origem = request.headers.get("origin")
        if request.headers.get("host") not in hosts:
            resposta = PlainTextResponse("host não permitido", status_code=400)
        elif request.method != "GET" and origem is not None and origem not in origens:
            resposta = PlainTextResponse("origem não permitida", status_code=403)
        else:
            resposta = await call_next(request)
        resposta.headers["Content-Security-Policy"] = CSP
        return resposta

    @app.get("/")
    def lista(request: Request, q: str = "", tipo: str = "", site: str = "", tag: str = "", grupo: str = "",
              de: str = "", ate: str = "", pagina: int = Query(1, ge=1)):
        if tipo and tipo not in TIPOS and tipo != "falha":
            raise HTTPException(422, "tipo inválido")
        try:
            de_utc, ate_utc = periodo_utc(de, fim=False), periodo_utc(ate, fim=True)
        except ValueError:
            raise HTTPException(422, "data inválida (use AAAA-MM-DDTHH:MM)") from None
        with Session(engine) as sessao:
            # site na URL: "-" = sem site identificado (''), vazio = todos; outro valor vai como veio (FR-015 da 002)
            filtro_site = {"": None, "-": ""}.get(site, site)
            notas, links, links_por_nota, sites = [], [], {}, []
            if tipo == "link":  # aba Link: um item por link (FR-002 da 003)
                links, total = buscar_links(sessao, site=filtro_site, q=q, pagina=pagina, tag=tag, de=de_utc, ate=ate_utc)
                sites = contar_sites(sessao)
            else:
                notas, total = buscar(sessao, q=q, tipo=tipo, pagina=pagina, tag=tag,
                                      grupo=grupo if tipo == "documento" else "", de=de_utc, ate=ate_utc)
                links_por_nota = links_das_notas(sessao, [n.id for n in notas if n.tipo == "link"])
            contagens = contar_por_tipo(sessao)
            categorias = [("", "Todas", contagens["todas"])] + [
                (t, rot, contagens[t]) for t, rot in ROTULOS.items() if contagens[t] or t == tipo
            ]
            fotos = {n.id for n in notas if n.tipo == "foto" and n.arquivo_caminho
                     and (cfg.media_dir / n.arquivo_caminho).is_file()}
            ids = {n.id for n in notas} | {nota.id for _, nota, _ in links}
            grupos = contar_grupos_documento(sessao) if tipo == "documento" else []
            # aviso de notas novas só na 1ª página sem filtro (FR-008 da 004)
            novas = None
            if pagina == 1 and not (q or tipo or site or tag or de or ate):
                novas = notas[0].enviada_em if notas else ""
            contexto = {
                "notas": notas, "links": links, "links_por_nota": links_por_nota,
                "total": total, "q": q, "tipo": tipo, "pagina": pagina,
                "por_pagina": POR_PAGINA, "paginas": max(1, math.ceil(total / POR_PAGINA)),
                "rotulos": ROTULOS, "plurais": ROTULOS_PLURAIS, "categorias": categorias,
                "contagens": contagens, "falhas": contagens["falha"],
                # todo link do painel leva o período junto (FR-003 da 008)
                "href": lambda *a, **k: href(*a, **({"de": de, "ate": ate} | k)),
                "de": de, "ate": ate, "atalhos": atalhos_periodo(q, tipo, site, tag, grupo),
                "sites": sites, "site": site, "fotos": fotos, "novas_desde": novas,
                "tag": tag, "tags": contar_tags(sessao), "tags_por_nota": tags_das_notas(sessao, ids),
                "grupo": grupo, "grupos": [(g, GRUPOS_DOCUMENTO[g][0], n) for g, n in grupos],
                "consulta": lambda p: href(q, tipo, site, pagina=p, tag=tag, grupo=grupo, de=de, ate=ate),
            }
            # renderiza com a sessão aberta: os objetos ainda são lidos no template
            return templates.TemplateResponse(request, "lista.html", contexto)

    @app.get("/novas")
    def novas(request: Request, desde: str = ""):
        with Session(engine) as sessao:
            n = contar_novas(sessao, desde)
        return templates.TemplateResponse(request, "_novas.html", {"desde": desde, "n": n})

    def status(request: Request, codigo: int = 200, aviso: str | None = None):
        with Session(engine) as sessao:
            imp = ultima_importacao(sessao)
            sessao.expunge_all()
        return templates.TemplateResponse(request, "_status.html", {"imp": imp, "aviso": aviso}, status_code=codigo)

    @app.get("/importar")
    def pagina_importar(request: Request):
        with Session(engine) as sessao:
            imp = ultima_importacao(sessao)
            sessao.expunge_all()
        exportacoes = encontrar_exportacoes(pastas_exportacao, cfg.chat_id)
        ultimo = backup.ultimo_backup(cfg.backup_dir) if cfg.backup_dir else None
        estado_backup = {
            "ultimo": ultimo, "pasta": cfg.backup_dir, "erro": backup.ULTIMO_ERRO["mensagem"],
            "atrasado": ultimo is None or datetime.now() - ultimo > timedelta(hours=48),
        }
        return templates.TemplateResponse(request, "importar.html", {
            "imp": imp, "aviso": None, "exportacoes": exportacoes, "backup": estado_backup})

    @app.get("/importar/status")
    def status_importacao(request: Request):
        return status(request)

    @app.post("/importar")
    def iniciar(request: Request, pasta: str = Form(...)):
        caminho = Path(pasta.strip().strip('"'))
        if not (caminho / "result.json").is_file():
            return status(request, 422, f"{caminho} não tem result.json (exporte em formato JSON).")
        with Session(engine) as sessao:
            try:
                imp_id = iniciar_importacao(sessao, str(caminho), "painel")
            except ImportacaoEmAndamento:
                return status(request, 409, "Já existe uma importação em andamento.")

        def rodar():
            with Session(engine) as sessao:
                try:
                    executar(imp_id, caminho, sessao, cfg)
                except Exception as e:
                    # O motivo normalmente já ficou gravado na importação; o log cobre o caso em que nem isso deu.
                    log.warning("importação %s terminou com erro: %s", imp_id, type(e).__name__)

        # ponytail: uma thread por importação basta; FR-021 garante uma de cada vez.
        threading.Thread(target=rodar, daemon=True).start()
        return status(request, 202)

    @app.get("/baixar/{nota_id}")
    def baixar(request: Request, nota_id: int):
        """Salva com o nome original (research R8 da 003); nada fora de MEDIA_DIR."""
        with Session(engine) as sessao:
            n = sessao.get(Nota, nota_id)
        base = cfg.media_dir.resolve()
        arquivo = (base / n.arquivo_caminho).resolve() if n and n.arquivo_caminho else None
        if arquivo is None or not arquivo.is_relative_to(base) or not arquivo.is_file():
            return templates.TemplateResponse(request, "nao_encontrado.html", {}, status_code=404)
        return FileResponse(arquivo, filename=n.arquivo_nome or n.arquivo_caminho)

    if cfg.previas_links:
        iniciar_previas(engine, cfg.media_dir)
    if cfg.backup_dir:
        iniciar_backup(cfg.database_url, cfg.backup_dir, cfg.backup_manter, cfg.pg_bin)

    @app.post("/sincronizar")
    def iniciar_sincronizacao(request: Request):
        """Um clique: tudo do grupo depois da última nota salva (009). Usa a trava de importação."""
        if falta := sincronizacao.o_que_falta(cfg):
            return status(request, 422, falta)
        with Session(engine) as sessao:
            try:
                imp_id = iniciar_importacao(sessao, "Telegram", "sincronizacao")
            except ImportacaoEmAndamento:
                return status(request, 409, "Já existe uma importação ou sincronização em andamento.")

        def rodar():
            try:
                sincronizar(imp_id, engine, cfg)
            except Exception as e:  # o erro já ficou gravado na importação
                log.warning("sincronização %s terminou com erro: %s", imp_id, type(e).__name__)

        threading.Thread(target=rodar, name="sincronizacao", daemon=True).start()
        return status(request, 202)

    app.mount("/static", StaticFiles(directory=AQUI / "static"), name="static")
    app.mount("/media", StaticFiles(directory=cfg.media_dir, check_dir=False), name="media")
    return app


def main() -> None:
    import uvicorn

    try:
        cfg = carregar()
    except ErroConfig as e:
        raise SystemExit(f"Configuração inválida: {e}") from None
    engine = criar_engine(cfg.database_url)
    exigir_revisao_atual(engine)
    cfg.media_dir.mkdir(parents=True, exist_ok=True)
    print(f"Painel em http://{HOST}:{cfg.painel_port}")
    uvicorn.run(criar_app(cfg, engine), host=HOST, port=cfg.painel_port)


if __name__ == "__main__":
    main()
