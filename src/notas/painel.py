"""Painel local: `uv run --env-file .env python -m notas.painel` (sempre em 127.0.0.1)."""

import logging
import math
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from notas.config import Config, ErroConfig, carregar
from notas.db import TIPOS, criar_engine, exigir_revisao_atual
from notas.importacao import executar
from notas.repositorio import (
    POR_PAGINA,
    ImportacaoEmAndamento,
    buscar,
    contar_por_tipo,
    contar_sites,
    iniciar_importacao,
    ultima_importacao,
)

AQUI = Path(__file__).parent
log = logging.getLogger("notas.painel")
HOST = "127.0.0.1"  # fixo: o painel nunca escuta em outra interface (Princípio IV)
ROTULOS = {
    "texto": "Texto", "link": "Link", "foto": "Foto", "audio": "Áudio", "video": "Vídeo",
    "documento": "Documento", "localizacao": "Localização", "contato": "Contato", "outro": "Outro",
}
FILTROS = list(ROTULOS.items()) + [("falha", "Falhas")]
ABAS = [("todas", "", "Todas")] + [(v, v, r) for v, r in FILTROS]  # (chave da contagem, tipo, rótulo)


def href(q: str = "", tipo: str = "", site: str = "", pagina: int | None = None) -> str:
    """Endereço da lista só com os parâmetros preenchidos (FR-009)."""
    params = {"q": q, "tipo": tipo, "site": site, "pagina": pagina}
    query = urlencode({k: v for k, v in params.items() if v})
    return f"/?{query}" if query else "/"


def data_local(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def criar_app(cfg: Config, engine: Engine) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    hosts = {f"127.0.0.1:{cfg.painel_port}", f"localhost:{cfg.painel_port}"}
    origens = {f"http://{h}" for h in hosts}
    templates = Jinja2Templates(directory=AQUI / "templates")
    templates.env.filters["data_local"] = data_local

    @app.middleware("http")
    async def so_local(request: Request, call_next):
        # Host errado = DNS rebinding; Origin de outro site num POST = CSRF.
        if request.headers.get("host") not in hosts:
            return PlainTextResponse("host não permitido", status_code=400)
        origem = request.headers.get("origin")
        if request.method != "GET" and origem is not None and origem not in origens:
            return PlainTextResponse("origem não permitida", status_code=403)
        return await call_next(request)

    @app.get("/")
    def lista(request: Request, q: str = "", tipo: str = "", site: str = "", pagina: int = Query(1, ge=1)):
        if tipo and tipo not in TIPOS and tipo != "falha":
            raise HTTPException(422, "tipo inválido")
        with Session(engine) as sessao:
            # site na URL: "-" = sem site identificado (''), vazio = todos; outro valor vai como veio (FR-015)
            filtro_site = {"": None, "-": ""}.get(site, site)
            notas, total = buscar(sessao, q=q, tipo=tipo, pagina=pagina, site=filtro_site)
            contagens = contar_por_tipo(sessao)
            sites = contar_sites(sessao) if tipo == "link" else []
        contexto = {
            "notas": notas, "total": total, "q": q, "tipo": tipo, "pagina": pagina,
            "por_pagina": POR_PAGINA, "paginas": max(1, math.ceil(total / POR_PAGINA)),
            "rotulos": ROTULOS, "abas": ABAS, "contagens": contagens, "href": href,
            "sites": sites, "site": site,
            "consulta": lambda p: href(q, tipo, site, pagina=p),
        }
        modelo = "_notas.html" if request.headers.get("hx-request") else "lista.html"
        return templates.TemplateResponse(request, modelo, contexto)

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
        return templates.TemplateResponse(request, "importar.html", {"imp": imp, "aviso": None})

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

    app.mount("/static", StaticFiles(directory=AQUI / "static"), name="static")
    app.mount("/media", StaticFiles(directory=cfg.media_dir, check_dir=False), name="media")
    return app


def main() -> None:
    import uvicorn

    try:
        cfg = carregar()
    except ErroConfig as e:
        raise SystemExit(f"Configuração inválida: {e}") from None
    engine = criar_engine(cfg.database_path)
    exigir_revisao_atual(engine)
    cfg.media_dir.mkdir(parents=True, exist_ok=True)
    print(f"Painel em http://{HOST}:{cfg.painel_port}")
    uvicorn.run(criar_app(cfg, engine), host=HOST, port=cfg.painel_port)


if __name__ == "__main__":
    main()
