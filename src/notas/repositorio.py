"""Acesso a dados. Cada função grava e faz commit da própria unidade de trabalho."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, column, func, select, text, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notas.db import Importacao, Nota, agora

# Campos que a captura ao vivo reescreve numa edição; enviada_em, criada_em e origem nunca mudam.
ATUALIZAVEIS = (
    "editada_em", "tipo", "texto", "link", "arquivo_caminho", "arquivo_nome",
    "arquivo_tamanho", "situacao", "erro", "bruto",
)


def salvar_ao_vivo(sessao: Session, dados: dict) -> None:
    stmt = insert(Nota).values(**dados, origem="ao_vivo", criada_em=agora())
    stmt = stmt.on_conflict_do_update(
        index_elements=["chat_id", "message_id"],
        set_={c: stmt.excluded[c] for c in ATUALIZAVEIS},
    )
    sessao.execute(stmt)
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


def buscar(sessao: Session, q: str = "", tipo: str = "", pagina: int = 1) -> tuple[list[Nota], int]:
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
    total = sessao.scalar(select(func.count()).select_from(filtro.subquery()))
    itens = sessao.scalars(
        filtro.order_by(Nota.enviada_em.desc(), Nota.id.desc())
        .limit(POR_PAGINA).offset((pagina - 1) * POR_PAGINA)
    ).all()
    return list(itens), total


# --- Importação (US5) ---------------------------------------------------------------
ABANDONO = timedelta(hours=1)


class ImportacaoEmAndamento(Exception):
    pass


def nota_existe(sessao: Session, chat_id: int, message_id: int) -> bool:
    return sessao.scalar(
        select(Nota.id).where(Nota.chat_id == chat_id, Nota.message_id == message_id)
    ) is not None


def salvar_importada(sessao: Session, dados: dict) -> bool:
    """Nunca altera nota existente (FR-019). Devolve True se criou."""
    stmt = insert(Nota).values(**dados, origem="importacao", criada_em=agora()).on_conflict_do_nothing()
    criou = sessao.execute(stmt).rowcount == 1
    sessao.commit()
    return criou


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
