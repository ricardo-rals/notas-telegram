from sqlalchemy import func, select

from notas.db import Nota
from notas.repositorio import registrar_falha, salvar_ao_vivo


def dados(mid=1, **extra):
    return {
        "chat_id": -1001234567890,
        "message_id": mid,
        "enviada_em": "2026-11-05T10:00:00+00:00",
        "editada_em": None,
        "tipo": "texto",
        "texto": "comprar pão",
        "link": f"https://t.me/c/1234567890/{mid}",
        "arquivo_caminho": None,
        "arquivo_nome": None,
        "arquivo_tamanho": None,
        "situacao": "ok",
        "erro": None,
        "bruto": "{}",
    } | extra


def contar(sessao):
    return sessao.scalar(select(func.count()).select_from(Nota))


def test_salvar_ao_vivo_grava_campos(sessao):
    salvar_ao_vivo(sessao, dados())
    n = sessao.scalars(select(Nota)).one()
    assert (n.tipo, n.texto, n.origem, n.situacao) == ("texto", "comprar pão", "ao_vivo", "ok")
    assert n.criada_em


def test_salvar_ao_vivo_repetido_mantem_uma_linha(sessao):
    salvar_ao_vivo(sessao, dados())
    salvar_ao_vivo(sessao, dados())
    assert contar(sessao) == 1


def test_salvar_ao_vivo_atualiza_sem_mexer_em_envio(sessao):
    salvar_ao_vivo(sessao, dados())
    criada = sessao.scalars(select(Nota)).one().criada_em
    salvar_ao_vivo(
        sessao,
        dados(texto="https://x.y", tipo="link", editada_em="2026-11-05T11:00:00+00:00", enviada_em="outra"),
    )
    sessao.expire_all()
    n = sessao.scalars(select(Nota)).one()
    assert (n.tipo, n.texto, n.editada_em) == ("link", "https://x.y", "2026-11-05T11:00:00+00:00")
    assert n.enviada_em == "2026-11-05T10:00:00+00:00" and n.criada_em == criada


def test_registrar_falha_nova(sessao):
    registrar_falha(sessao, chat_id=-1001234567890, message_id=7, erro="boom", bruto='{"x":1}',
                    enviada_em="2026-11-05T10:00:00+00:00", link="l")
    n = sessao.scalars(select(Nota)).one()
    assert (n.situacao, n.erro, n.tipo, n.texto, n.bruto) == ("falha", "boom", "outro", "", '{"x":1}')


def test_registrar_falha_preserva_conteudo_existente(sessao):
    salvar_ao_vivo(sessao, dados())
    registrar_falha(sessao, chat_id=-1001234567890, message_id=1, erro="boom", bruto="{}",
                    enviada_em="x", link="l", editada_em="2026-11-05T12:00:00+00:00")
    sessao.expire_all()
    n = sessao.scalars(select(Nota)).one()
    assert (n.texto, n.tipo, n.situacao, n.erro) == ("comprar pão", "texto", "falha", "boom")
    assert n.editada_em == "2026-11-05T12:00:00+00:00"


# --- US2: busca -------------------------------------------------------------
import pytest  # noqa: E402

from notas.repositorio import buscar  # noqa: E402


def semear(sessao, textos_tipos):
    for i, (texto, tipo) in enumerate(textos_tipos, start=1):
        salvar_ao_vivo(sessao, dados(mid=i, texto=texto, tipo=tipo, enviada_em=f"2026-11-05T10:{i // 60:02d}:{i % 60:02d}+00:00"))


def test_buscar_pagina_e_ordem(sessao):
    semear(sessao, [(f"nota {i}", "texto") for i in range(1, 121)])
    itens, total = buscar(sessao)
    assert total == 120 and len(itens) == 50
    assert itens[0].texto == "nota 120" and itens[49].texto == "nota 71"
    itens3, _ = buscar(sessao, pagina=3)
    assert len(itens3) == 20
    assert buscar(sessao, pagina=4)[0] == []


def test_buscar_sem_acento_e_maiuscula(sessao):
    semear(sessao, [("Reunião às 15h", "texto"), ("reuniao amanhã", "texto"), ("outra coisa", "texto")])
    itens, total = buscar(sessao, q="REUNIÃO")
    assert total == 2


def test_buscar_varias_palavras_exige_todas(sessao):
    semear(sessao, [("reunião às 15h", "texto"), ("reunião cancelada", "texto")])
    assert [n.texto for n in buscar(sessao, q="reuniao 15h")[0]] == ["reunião às 15h"]


@pytest.mark.parametrize("q", ['"', "*", "-", "(", 'a"b', "NEAR(", "x OR", "^"])
def test_buscar_caracteres_especiais_nao_quebram(sessao, q):
    semear(sessao, [("texto qualquer", "texto")])
    buscar(sessao, q=q)


def test_buscar_tipo_falha_e_combinacao(sessao):
    semear(sessao, [("foto da praia", "foto"), ("praia texto", "texto")])
    salvar_ao_vivo(sessao, dados(mid=50, texto="praia quebrada", situacao="falha", erro="x", tipo="foto"))
    assert {n.texto for n in buscar(sessao, tipo="foto")[0]} == {"foto da praia", "praia quebrada"}
    assert [n.texto for n in buscar(sessao, tipo="falha")[0]] == ["praia quebrada"]
    assert [n.texto for n in buscar(sessao, q="praia", tipo="texto")[0]] == ["praia texto"]


@pytest.mark.lento
def test_busca_com_10000_notas_em_menos_de_1s(sessao):
    import time

    from sqlalchemy import insert as insert_core

    palavras = ["reunião", "mercado", "projeto", "viagem", "leitura", "treino", "conta", "ideia"]
    linhas = [
        dados(mid=i, texto=f"{palavras[i % 8]} nota {i} {palavras[(i * 7) % 8]}",
              tipo="link" if i % 5 == 0 else "texto", enviada_em=f"2026-01-01T00:00:00+00:00:{i:05d}")
        | {"origem": "ao_vivo", "criada_em": "x"}
        for i in range(1, 10_001)
    ]
    sessao.execute(insert_core(Nota), linhas)
    sessao.commit()
    for q, tipo in [("", ""), ("reuniao", ""), ("projeto viagem", ""), ("mercado", "link"), ("", "falha")]:
        inicio = time.perf_counter()
        buscar(sessao, q=q, tipo=tipo, pagina=3)
        assert time.perf_counter() - inicio < 1.0, (q, tipo)
