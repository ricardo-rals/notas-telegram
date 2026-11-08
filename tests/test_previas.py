"""Prévias de links (003 US2). Nenhum teste acessa a internet: as páginas vêm de um servidor
HTTP local, e o resolvedor de nomes é falso (trata 127.0.0.1 como se fosse um IP público)."""

import hashlib
import http.server
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest

from notas.previas import buscar_previa, destino_permitido, extrair_metadados

PAGINAS = Path(__file__).parent / "fixtures" / "paginas"
GLOBAL = "93.184.216.34"


def resolver_falso(host, *args, **kwargs):
    """127.0.0.1 (o servidor de teste) passa como público; o resto resolve literalmente."""
    ip = GLOBAL if host in ("127.0.0.1", "publico.exemplo") else host
    if host == "privado.exemplo":
        ip = "10.1.2.3"
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


# --- extrair_metadados ----------------------------------------------------------------
def html(nome):
    return (PAGINAS / nome).read_bytes().decode("latin-1" if nome == "og_completo.html" else "utf-8")


def test_og_completo():
    m = extrair_metadados(html("og_completo.html"), "https://site.exemplo/a/b")
    assert m == {
        "titulo": "Receita de pão caseiro",
        "descricao": "Uma receita simples (inventada).",
        "imagem": "https://site.exemplo/img.png",
    }


def test_so_twitter_e_so_title():
    assert extrair_metadados(html("so_twitter.html"), "https://x.exemplo/") == {
        "titulo": "Título do Twitter", "descricao": "Descrição do Twitter", "imagem": "https://cdn.exemplo/x.png",
    }
    assert extrair_metadados(html("so_title.html"), "https://x.exemplo/") == {
        "titulo": "Só o título", "descricao": "desc meta", "imagem": None,
    }


def test_sem_metadados_e_malicioso():
    assert extrair_metadados(html("sem_metadados.html"), "https://x.exemplo/") == {
        "titulo": None, "descricao": None, "imagem": None,
    }
    m = extrair_metadados(html("malicioso.html"), "https://x.exemplo/")
    assert m["descricao"] == "<b>negrito</b>"  # texto puro; o template escapa
    assert "Oi" in (m["titulo"] or "") or m["titulo"] is None


def test_corte_de_tamanho():
    longo = '<head><meta property="og:title" content="' + "a" * 500 + '"><meta property="og:description" content="' + "b" * 500 + '"></head>'
    m = extrair_metadados(longo, "https://x.exemplo/")
    assert len(m["titulo"]) == 200 and len(m["descricao"]) == 300


# --- destino_permitido -----------------------------------------------------------------
@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://publico.exemplo/x", True),
        ("http://127.0.0.1:9/x", True),  # só porque o resolvedor falso diz que é público
        ("http://localhost/", False),
        ("http://10.0.0.1/", False),
        ("http://192.168.1.1/", False),
        ("http://169.254.1.1/", False),
        ("http://[::1]/", False),
        ("https://privado.exemplo/", False),
        ("ftp://publico.exemplo/", False),
        ("file:///etc/passwd", False),
    ],
)
def test_destino_permitido(url, ok):
    assert destino_permitido(url, resolver_falso) is ok


def test_destino_com_resolvedor_real_recusa_loopback():
    assert destino_permitido("http://127.0.0.1/") is False


# --- buscar_previa contra servidor local -------------------------------------------------
class Pagina(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def responder(self, codigo, tipo, corpo, extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):  # noqa: N802
        p = self.path
        if p == "/og":
            self.responder(200, "text/html; charset=iso-8859-1", (PAGINAS / "og_completo.html").read_bytes())
        elif p == "/img.png":
            self.responder(200, "image/png", (PAGINAS / "img.png").read_bytes())
        elif p == "/pdf":
            self.responder(200, "application/pdf", b"%PDF-1.4")
        elif p == "/404":
            self.responder(404, "text/html", b"nao")
        elif p == "/redir-local":
            self.responder(302, "text/html", b"", {"Location": "http://10.0.0.1/"})
        elif p.startswith("/loop"):
            self.responder(302, "text/html", b"", {"Location": "/loop"})
        elif p == "/redir-og":
            self.responder(301, "text/html", b"", {"Location": "/og"})
        elif p == "/grande":
            corpo = b"<head><title>grande</title></head>" + b"x" * (2 * 1024 * 1024)
            self.responder(200, "text/html", corpo)
        elif p == "/img-grande":
            self.responder(200, "text/html", b'<head><title>t</title><meta property="og:image" content="/big.png"></head>')
        elif p == "/big.png":
            self.responder(200, "image/png", b"\x89PNG" + b"0" * (6 * 1024 * 1024))
        elif p == "/lento":
            time.sleep(2)
            self.responder(200, "text/html", b"<title>tarde</title>")
        else:
            self.responder(404, "text/html", b"")


@pytest.fixture(scope="module")
def servidor():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Pagina)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture
def cliente():
    with httpx.Client(timeout=0.5) as c:
        yield c


def buscar(url, cliente, tmp_path):
    return buscar_previa(url, cliente, resolver_falso, tmp_path)


def test_previa_ok_com_imagem(servidor, cliente, tmp_path):
    r = buscar(f"{servidor}/og", cliente, tmp_path)
    assert (r.situacao, r.titulo, r.descricao) == ("ok", "Receita de pão caseiro", "Uma receita simples (inventada).")
    nome = hashlib.sha1(f"{servidor}/og".encode()).hexdigest()
    assert r.imagem == f"previas/{nome}.png" and (tmp_path / r.imagem).read_bytes().startswith(b"\x89PNG")


def test_previa_segue_redirecionamento_publico(servidor, cliente, tmp_path):
    assert buscar(f"{servidor}/redir-og", cliente, tmp_path).titulo == "Receita de pão caseiro"


@pytest.mark.parametrize(
    "caminho, definitiva",
    [("/pdf", True), ("/404", False), ("/redir-local", True), ("/loop", False), ("/lento", False)],
)
def test_previa_indisponivel(servidor, cliente, tmp_path, caminho, definitiva):
    r = buscar(f"{servidor}{caminho}", cliente, tmp_path)
    assert r.situacao == "indisponivel" and r.definitiva is definitiva and r.erro


def test_endereco_local_nem_conecta(cliente, tmp_path):
    r = buscar_previa("http://192.168.0.1/", cliente, resolver_falso, tmp_path)
    assert (r.situacao, r.definitiva, r.erro) == ("indisponivel", True, "endereço local")


def test_limites_de_tamanho(servidor, cliente, tmp_path):
    assert buscar(f"{servidor}/grande", cliente, tmp_path).titulo == "grande"  # lê só o começo
    r = buscar(f"{servidor}/img-grande", cliente, tmp_path)
    assert r.situacao == "ok" and r.imagem is None
