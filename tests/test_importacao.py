import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select, text

from conftest import FIXTURES
from notas.db import Importacao, Nota
from notas.importacao import ErroImportacao, ImportacaoEmAndamento, importar
from notas.repositorio import salvar_ao_vivo

OK = FIXTURES / "exportacao_ok"


def ja_capturada(sessao, mid, texto="versão ao vivo"):
    salvar_ao_vivo(sessao, {
        "chat_id": -1001234567890, "message_id": mid, "enviada_em": "2025-11-05T10:00:00+00:00",
        "editada_em": None, "tipo": "texto", "texto": texto, "link": "l", "arquivo_caminho": None,
        "arquivo_nome": None, "arquivo_tamanho": None, "situacao": "ok", "erro": None, "bruto": None,
    })


def contagens(r):
    return (r.criadas, r.existentes, r.ignoradas, r.falhas)


def nota(sessao, mid):
    sessao.expire_all()
    return sessao.scalars(select(Nota).where(Nota.message_id == mid)).one()


def test_importacao_completa(sessao, config_teste):
    for mid in (101, 102, 103):
        ja_capturada(sessao, mid)
    r = importar(OK, "terminal", sessao, config_teste)
    assert contagens(r) == (7, 3, 2, 1) and r.status == "concluida"
    assert nota(sessao, 101).texto == "versão ao vivo"  # FR-019: existente não muda
    voz = nota(sessao, 104)
    assert (voz.tipo, voz.origem, voz.situacao) == ("audio", "importacao", "ok")
    assert (config_teste.media_dir / voz.arquivo_caminho).read_bytes() == b"abc"
    assert nota(sessao, 105).arquivo_nome == "boleto.pdf"
    assert nota(sessao, 106).arquivo_caminho is None  # vídeo nunca é copiado
    assert nota(sessao, 110).editada_em is not None
    ruim = nota(sessao, 111)
    assert ruim.situacao == "falha" and ruim.erro and ruim.origem == "importacao"
    assert nota(sessao, 101).link == "l"
    assert nota(sessao, 104).link == "https://t.me/c/1234567890/104"


def test_importacao_repetida_nao_cria_nada(sessao, config_teste):
    importar(OK, "terminal", sessao, config_teste)
    r = importar(OK, "painel", sessao, config_teste)
    assert contagens(r) == (0, 11, 2, 0)


def test_midia_de_terceiros_nao_e_copiada(sessao, config_teste):
    importar(OK, "terminal", sessao, config_teste)
    assert not any("photo_outro" in p.name for p in config_teste.media_dir.iterdir())


def test_arquivo_nao_incluido(sessao, config_teste):
    importar(FIXTURES / "exportacao_sem_midia", "terminal", sessao, config_teste)
    assert nota(sessao, 120).situacao == "sem_arquivo"


@pytest.mark.parametrize("pasta", ["exportacao_outro_chat", "exportacao_quebrada", "nao_existe"])
def test_exportacao_invalida_nao_toca_nas_notas(sessao, config_teste, pasta):
    ja_capturada(sessao, 101)
    with pytest.raises(ErroImportacao):
        importar(FIXTURES / pasta, "terminal", sessao, config_teste)
    assert sessao.scalar(text("SELECT count(*) FROM nota")) == 1
    assert sessao.scalars(select(Importacao)).one().status == "falha"


def test_uma_importacao_por_vez(sessao, config_teste):
    sessao.add(Importacao(pasta="x", via="painel", status="rodando"))
    sessao.commit()
    with pytest.raises(ImportacaoEmAndamento):
        importar(OK, "terminal", sessao, config_teste)


def test_importacao_abandonada_e_liberada(sessao, config_teste):
    velha = (datetime.now(UTC) - timedelta(hours=2)).isoformat(timespec="seconds")
    sessao.add(Importacao(pasta="x", via="painel", status="rodando", iniciada_em=velha))
    sessao.commit()
    assert importar(OK, "terminal", sessao, config_teste).status == "concluida"
    assert sessao.scalars(select(Importacao).where(Importacao.pasta == "x")).one().status == "falha"


@pytest.mark.lento
def test_5000_mensagens_em_menos_de_2_minutos(sessao, config_teste, tmp_path):
    msgs = [{"id": i, "type": "message", "date_unixtime": str(1762336800 + i), "from_id": "user111",
             "text": f"nota {i}", "text_entities": [{"type": "plain", "text": f"nota {i}"}]} for i in range(1, 5001)]
    pasta = tmp_path / "grande"
    pasta.mkdir()
    (pasta / "result.json").write_text(json.dumps({"id": 1234567890, "type": "private_supergroup", "messages": msgs}))
    inicio = time.perf_counter()
    r = importar(pasta, "terminal", sessao, config_teste)
    assert r.criadas == 5000 and time.perf_counter() - inicio < 120
    assert importar(pasta, "terminal", sessao, config_teste).criadas == 0


def test_caminho_relativo_da_exportacao_nao_escapa(sessao, config_teste, tmp_path):
    pasta = tmp_path / "exp"
    pasta.mkdir()
    (tmp_path / "segredo.txt").write_text("x")
    item = {"id": 1, "type": "message", "date_unixtime": "1762336800", "from_id": "user111", "text": "",
            "file": "../segredo.txt", "file_name": "segredo.txt", "file_size": 1, "mime_type": "text/plain"}
    (pasta / "result.json").write_text(json.dumps({"id": 1234567890, "messages": [item]}))
    importar(pasta, "terminal", sessao, config_teste)
    n = nota(sessao, 1)
    assert n.arquivo_caminho is None and n.situacao in ("sem_arquivo", "falha")
    assert not Path(config_teste.media_dir).exists() or not any(config_teste.media_dir.iterdir())


# --- 002 US4 ------------------------------------------------------------------------
def test_importacao_grava_itens(sessao, config_teste):
    from notas.db import Link

    r = importar(FIXTURES / "exportacao_links", "terminal", sessao, config_teste)
    assert contagens(r) == (3, 0, 0, 0)
    linhas = sessao.execute(
        select(Nota.message_id, Link.site).join(Link, Link.nota_id == Nota.id)
    ).all()
    assert sorted(linhas) == [(301, "facebook.com"), (302, "youtube.com")]


# --- 004 US7: exportações encontradas em Downloads -------------------------------------
import os  # noqa: E402

from notas.importacao import encontrar_exportacoes  # noqa: E402


def _exportacao(base, nome, chat_id=1234567890, n=2, quebrada=False, mtime=None):
    pasta = base / nome
    pasta.mkdir(parents=True)
    corpo = "{" if quebrada else json.dumps({"name": f"Chat {nome}", "id": chat_id, "messages": [{}] * n})
    (pasta / "result.json").write_text(corpo, encoding="utf-8")
    if mtime:
        os.utime(pasta, (mtime, mtime))
    return pasta


def test_encontrar_exportacoes(tmp_path):
    a, b = tmp_path / "Telegram Desktop", tmp_path / "Downloads"
    _exportacao(a, "ChatExport_1", n=4, mtime=1_700_000_000)
    _exportacao(b, "ChatExport_2", n=1, mtime=1_800_000_000)
    _exportacao(b, "Outro", chat_id=9999999999, mtime=1_750_000_000)
    _exportacao(b, "Ruim", quebrada=True, mtime=1_600_000_000)
    (b / "sem_result").mkdir()
    (b / "solto.txt").write_text("x")
    r = encontrar_exportacoes([a, b, tmp_path / "inexistente"], -1001234567890)
    assert [(e.pasta.name, e.situacao) for e in r] == [
        ("ChatExport_2", "importavel"), ("Outro", "outro_chat"), ("ChatExport_1", "importavel"), ("Ruim", "ilegivel"),
    ]
    um = r[2]
    assert um.mensagens == 4 and um.nome == "Chat ChatExport_1"
    assert encontrar_exportacoes([b], -1001234567890, limite_s=0) == []
