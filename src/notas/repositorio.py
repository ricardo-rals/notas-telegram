"""Acesso a dados. Cada função grava e faz commit da própria unidade de trabalho."""

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, Integer, column, delete, func, insert as insert_core, select, text, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notas.db import TIPOS, Importacao, Nota, NotaSite, agora
from notas.regras import normalizar_bot_api, normalizar_exportacao, sites_da_nota, sites_do_texto

# Campos que a captura ao vivo reescreve numa edição; enviada_em, criada_em e origem nunca mudam.
ATUALIZAVEIS = (
    "editada_em", "tipo", "texto", "link", "arquivo_caminho", "arquivo_nome",
    "arquivo_tamanho", "situacao", "erro", "bruto",
)


def _gravar_sites(sessao: Session, nota_id: int, tipo: str, sites: frozenset[str]) -> None:
    """Substitui os sites da nota. Só link tem site, e link nunca fica sem nenhum (FR-007)."""
    sessao.execute(delete(NotaSite).where(NotaSite.nota_id == nota_id))
    if tipo == "link":
        sessao.add_all(NotaSite(nota_id=nota_id, site=s) for s in (sites or {""}))


def salvar_ao_vivo(sessao: Session, dados: dict, sites: frozenset[str] = frozenset()) -> None:
    stmt = insert(Nota).values(**dados, origem="ao_vivo", criada_em=agora())
    stmt = stmt.on_conflict_do_update(
        index_elements=["chat_id", "message_id"],
        set_={c: stmt.excluded[c] for c in ATUALIZAVEIS},
    ).returning(Nota.id)
    _gravar_sites(sessao, sessao.execute(stmt).scalar_one(), dados["tipo"], sites)
    sessao.commit()


def registrar_falha(
    sessao: Session, *, chat_id: int, message_id: int, erro: str, bruto: str | None,
    enviada_em: str, link: str, editada_em: str | None = None, origem: str = "ao_vivo",
) -> None:
    """Falha visível (Princípio VIII). Se a nota já existe, mantém o conteúdo e só marca a falha."""
    stmt = insert(Nota).values(
        chat_id=chat_id, message_id=message_id, enviada_em=enviada_em, editada_em=editada_em,
        tipo="outro", texto="", link=link, situacao="falha", erro=erro, origem=origem,
        bruto=bruto, criada_em=agora(),
    )
    set_ = {"situacao": "falha", "erro": erro, "bruto": bruto}
    if editada_em:
        set_["editada_em"] = editada_em
    sessao.execute(stmt.on_conflict_do_update(index_elements=["chat_id", "message_id"], set_=set_))
    sessao.commit()


POR_PAGINA = 50


def consulta_fts(q: str) -> str | None:
    """Cada palavra vira um token entre aspas (E lógico); a sintaxe do FTS5 nunca chega crua."""
    palavras = [p for p in q.split() if any(ch.isalnum() for ch in p)]
    return " ".join('"' + p.replace('"', '""') + '"' for p in palavras) or None


def buscar(
    sessao: Session, q: str = "", tipo: str = "", pagina: int = 1, site: str | None = None
) -> tuple[list[Nota], int]:
    """`site` só vale na aba link; `''` = sem site identificado; None = todos."""
    filtro = select(Nota)
    if q.strip():
        fts = consulta_fts(q)
        if fts is None:
            return [], 0
        ids = text("SELECT rowid FROM nota_fts WHERE nota_fts MATCH :fts").bindparams(fts=fts)
        filtro = filtro.where(Nota.id.in_(ids.columns(column("rowid", Integer))))
    if tipo == "falha":
        filtro = filtro.where(Nota.situacao == "falha")
    elif tipo:
        filtro = filtro.where(Nota.tipo == tipo)
    if tipo == "link" and site is not None:
        filtro = filtro.where(Nota.id.in_(select(NotaSite.nota_id).where(NotaSite.site == site)))
    total = sessao.scalar(select(func.count()).select_from(filtro.subquery()))
    itens = sessao.scalars(
        filtro.order_by(Nota.enviada_em.desc(), Nota.id.desc())
        .limit(POR_PAGINA).offset((pagina - 1) * POR_PAGINA)
    ).all()
    return list(itens), total


def contar_por_tipo(sessao: Session) -> dict[str, int]:
    """Contagens do caderno inteiro (FR-002): um por tipo, mais `falha` e `todas`."""
    c = {t: 0 for t in TIPOS} | dict(sessao.execute(select(Nota.tipo, func.count()).group_by(Nota.tipo)).all())
    c["falha"] = sessao.scalar(select(func.count()).where(Nota.situacao == "falha"))
    c["todas"] = sum(c[t] for t in TIPOS)
    return c


def contar_sites(sessao: Session) -> list[tuple[str, int]]:
    """Sites das notas de link, do mais usado ao menos usado; "sem site" sempre por último."""
    n = func.count().label("n")
    return [tuple(r) for r in sessao.execute(
        select(NotaSite.site, n).join(Nota, Nota.id == NotaSite.nota_id).where(Nota.tipo == "link")
        .group_by(NotaSite.site).order_by(NotaSite.site == "", n.desc(), NotaSite.site)
    ).all()]


def _sites_guardados(origem: str, bruto: str | None, texto: str, chat_id: int) -> frozenset[str]:
    """Sites de uma nota já gravada: pelo JSON original, com as mesmas regras da captura;
    sem JSON utilizável, pela regex sobre o texto."""
    try:
        d = json.loads(bruto)
        m = normalizar_bot_api(d) if origem == "ao_vivo" else normalizar_exportacao(d, chat_id)
        return sites_da_nota(m)
    except Exception:
        return sites_do_texto(texto)


def reclassificar_sites(conn: Connection) -> int:
    """Recalcula nota_site de todas as notas de link (FR-011). Idempotente; não toca em `nota`.
    Não faz commit: roda dentro da transação de quem chama (migração ou teste)."""
    t = NotaSite.__table__
    conn.execute(delete(t).where(t.c.nota_id.in_(select(Nota.id).where(Nota.tipo != "link"))))
    notas = conn.execute(
        select(Nota.id, Nota.origem, Nota.bruto, Nota.texto, Nota.chat_id).where(Nota.tipo == "link")
    ).all()
    conn.execute(delete(t).where(t.c.nota_id.in_(select(Nota.id).where(Nota.tipo == "link"))))
    linhas = [
        {"nota_id": n.id, "site": s}
        for n in notas
        for s in _sites_guardados(n.origem, n.bruto, n.texto, n.chat_id)
    ]
    if linhas:
        conn.execute(insert_core(t), linhas)
    return len(notas)


# --- Importação (US5) ---------------------------------------------------------------
ABANDONO = timedelta(hours=1)


class ImportacaoEmAndamento(Exception):
    pass


def nota_existe(sessao: Session, chat_id: int, message_id: int) -> bool:
    return sessao.scalar(
        select(Nota.id).where(Nota.chat_id == chat_id, Nota.message_id == message_id)
    ) is not None


def salvar_importada(sessao: Session, dados: dict, sites: frozenset[str] = frozenset()) -> bool:
    """Nunca altera nota existente (FR-019). Devolve True se criou."""
    stmt = (
        insert(Nota).values(**dados, origem="importacao", criada_em=agora())
        .on_conflict_do_nothing().returning(Nota.id)
    )
    nota_id = sessao.execute(stmt).scalar()
    if nota_id is not None:
        _gravar_sites(sessao, nota_id, dados["tipo"], sites)
    sessao.commit()
    return nota_id is not None


def iniciar_importacao(sessao: Session, pasta: str, via: str) -> int:
    """Trava entre processos: índice único parcial em status='rodando' (FR-021)."""
    limite = (datetime.now(UTC) - ABANDONO).isoformat(timespec="seconds")
    sessao.execute(
        update(Importacao)
        .where(Importacao.status == "rodando", Importacao.iniciada_em < limite)
        .values(status="falha", erro="abandonada (mais de 1 h sem terminar)", terminada_em=agora())
    )
    sessao.commit()
    imp = Importacao(pasta=pasta, via=via, status="rodando")
    sessao.add(imp)
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise ImportacaoEmAndamento("já existe uma importação em andamento") from None
    return imp.id


def concluir_importacao(
    sessao: Session, imp_id: int, status: str, contagens: dict, erro: str | None = None
) -> Importacao:
    imp = sessao.get(Importacao, imp_id)
    imp.status, imp.erro, imp.terminada_em = status, erro, agora()
    for campo in ("criadas", "existentes", "ignoradas", "falhas"):
        setattr(imp, campo, contagens.get(campo, 0))
    sessao.commit()
    return imp


def ultima_importacao(sessao: Session) -> Importacao | None:
    return sessao.scalars(select(Importacao).order_by(Importacao.id.desc()).limit(1)).first()
