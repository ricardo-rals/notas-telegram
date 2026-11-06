import pytest
from fastapi.testclient import TestClient

from notas.painel import criar_app
from notas.repositorio import salvar_ao_vivo

BASE_URL = "http://127.0.0.1:8000"


def nota(mid, **extra):
    return {
        "chat_id": -1001234567890, "message_id": mid,
        "enviada_em": f"2026-11-05T10:00:{mid:02d}+00:00", "editada_em": None,
        "tipo": "texto", "texto": f"nota {mid}", "link": f"https://t.me/c/1234567890/{mid}",
        "arquivo_caminho": None, "arquivo_nome": None, "arquivo_tamanho": None,
        "situacao": "ok", "erro": None, "bruto": None,
    } | extra


@pytest.fixture
def cliente(engine, config_teste, sessao):
    return TestClient(criar_app(config_teste, engine), base_url=BASE_URL)


def test_lista(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1, texto="comprar pão"))
    r = cliente.get("/")
    assert r.status_code == 200
    assert "comprar pão" in r.text and "https://t.me/c/1234567890/1" in r.text
    assert "<html" in r.text and "/static/htmx.min.js" in r.text


def test_host_estranho_recusado(cliente):
    assert cliente.get("/", headers={"Host": "exemplo.com"}).status_code == 400
    assert cliente.get("/", headers={"Host": "localhost:8000"}).status_code == 200


def test_post_de_outra_origem_recusado(cliente):
    r = cliente.post("/importar", data={"pasta": "x"}, headers={"Origin": "http://malicioso.com"})
    assert r.status_code == 403


@pytest.mark.parametrize("query", ["tipo=xyz", "pagina=0", "pagina=abc"])
def test_parametros_invalidos(cliente, query):
    assert cliente.get(f"/?{query}").status_code == 422


def test_sem_resultados(cliente):
    assert "Nenhuma nota encontrada" in cliente.get("/?q=xyzxyz").text


def test_htmx_devolve_fragmento(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1))
    r = cliente.get("/", headers={"HX-Request": "true"})
    assert "nota 1" in r.text and "<html" not in r.text


def test_busca_e_filtro(cliente, sessao):
    salvar_ao_vivo(sessao, nota(1, texto="Reunião"))
    salvar_ao_vivo(sessao, nota(2, texto="reunião foto", tipo="foto"))
    r = cliente.get("/", params={"q": "reuniao", "tipo": "texto"})
    assert "Reunião" in r.text and "reunião foto" not in r.text


def test_atualizacao_automatica_so_na_primeira_pagina(cliente):
    assert 'every 10s' in cliente.get("/").text
    assert 'every 10s' not in cliente.get("/?pagina=2").text


def test_previas_de_midia(cliente, sessao, config_teste):
    salvar_ao_vivo(sessao, nota(1, tipo="foto", texto="praia", arquivo_caminho="1_a.jpg"))
    salvar_ao_vivo(sessao, nota(2, tipo="audio", texto="", arquivo_caminho="2_b.ogg"))
    salvar_ao_vivo(sessao, nota(3, tipo="documento", arquivo_caminho="3_c.pdf", arquivo_nome="boleto.pdf"))
    salvar_ao_vivo(sessao, nota(4, tipo="documento", situacao="grande_demais", arquivo_nome="g.pdf"))
    salvar_ao_vivo(sessao, nota(5, tipo="foto", situacao="sem_arquivo"))
    salvar_ao_vivo(sessao, nota(6, situacao="falha", erro="ValueError: quebrou"))
    html = cliente.get("/").text
    assert '<img loading="lazy" src="/media/1_a.jpg" alt="praia"' in html
    assert '<audio controls src="/media/2_b.ogg"' in html
    assert 'href="/media/3_c.pdf"' in html and "boleto.pdf" in html
    assert "acima de 20 MB" in html
    assert "não veio na exportação" in html
    assert 'class="nota falha"' in html and "ValueError: quebrou" in html


def test_media(cliente, config_teste):
    config_teste.media_dir.mkdir(parents=True)
    (config_teste.media_dir / "1_a.jpg").write_bytes(b"img")
    assert cliente.get("/media/1_a.jpg").content == b"img"
    assert cliente.get("/media/inexistente.jpg").status_code == 404
    assert cliente.get("/media/..%2F..%2Fnotas.db").status_code == 404


# --- US5: importação pelo painel ----------------------------------------------------
import time  # noqa: E402

from conftest import FIXTURES  # noqa: E402
from notas.db import Importacao  # noqa: E402


def esperar_fim(cliente, segundos=10):
    fim = time.time() + segundos
    while time.time() < fim:
        html = cliente.get("/importar/status").text
        if "rodando" not in html:
            return html
        time.sleep(0.05)
    raise AssertionError("importação não terminou")


def test_formulario_importar(cliente):
    r = cliente.get("/importar")
    assert r.status_code == 200 and 'name="pasta"' in r.text


def test_importar_pelo_painel(cliente):
    r = cliente.post("/importar", data={"pasta": str(FIXTURES / "exportacao_ok")},
                     headers={"Origin": BASE_URL})
    assert r.status_code == 202
    html = esperar_fim(cliente)
    assert "concluída" in html and "criadas: 10" in html and "ignoradas: 2" in html and "falhas: 1" in html


def test_importar_pasta_sem_result_json(cliente, tmp_path):
    assert cliente.post("/importar", data={"pasta": str(tmp_path)}).status_code == 422


def test_importar_com_outra_rodando(cliente, sessao):
    sessao.add(Importacao(pasta="x", via="terminal", status="rodando"))
    sessao.commit()
    r = cliente.post("/importar", data={"pasta": str(FIXTURES / "exportacao_ok")})
    assert r.status_code == 409 and "em andamento" in r.text
