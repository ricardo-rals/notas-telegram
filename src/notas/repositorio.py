"""Acesso a dados. Cada função grava e faz commit da própria unidade de trabalho."""

import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, delete, false, func, insert as insert_core, literal_column, not_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notas.db import TIPOS, Importacao, Link, Nota, Previa, Tag, agora
from notas.regras import (
    GRUPOS_DOCUMENTO,
    SEM_SITE,
    ItemLink,
    itens_de_link,
    itens_do_texto,
    normalizar_bot_api,
    normalizar_exportacao,
    tags,
)

# Campos que a captura ao vivo reescreve numa edição; enviada_em, criada_em e origem nunca mudam.
ATUALIZAVEIS = (
    "editada_em", "tipo", "texto", "link", "arquivo_caminho", "arquivo_nome",
    "arquivo_tamanho", "situacao", "erro", "bruto",
)


def _linhas_link(nota_id: int, tipo: str, itens, enviada_em: str) -> list[dict]:
    """Só link tem itens, e link nunca fica sem nenhum (sentinela, FR-007 da 002)."""
    if tipo != "link":
        return []
    itens = list(itens) or [ItemLink(0, "", SEM_SITE, enviada_em, None)]
    return [{"nota_id": nota_id, "posicao": i.posicao, "url": i.url, "site": i.site, "data": i.data,
             "autor": i.autor} for i in itens]


def _gravar_links(sessao: Session, nota_id: int, tipo: str, itens, enviada_em: str) -> None:
    """Substitui os itens de link da nota inteiros (FR-004)."""
    sessao.execute(delete(Link).where(Link.nota_id == nota_id))
    linhas = _linhas_link(nota_id, tipo, itens, enviada_em)
    if linhas:
        sessao.execute(insert_core(Link), linhas)
        _previas_pendentes(sessao, linhas)


def _previas_pendentes(conn, linhas: list[dict]) -> None:
    """Uma prévia por URL (FR-005): cria `pendente` só se ainda não existe."""
    urls = [{"url": u} for u in dict.fromkeys(linha["url"] for linha in linhas) if u]
    if urls:
        conn.execute(insert(Previa).on_conflict_do_nothing(), urls)


def _gravar_tags(sessao: Session, nota_id: int, texto: str | None) -> None:
    """Substitui as tags da nota pelas hashtags do texto atual (FR-002 da 005)."""
    sessao.execute(delete(Tag).where(Tag.nota_id == nota_id))
    nomes = tags(texto)
    if nomes:
        sessao.execute(insert_core(Tag), [{"nota_id": nota_id, "nome": n} for n in nomes])


def salvar_ao_vivo(sessao: Session, dados: dict, itens: Iterable[ItemLink] = (), origem: str = "ao_vivo") -> None:
    """Upsert: captura ao vivo e sincronização (009); edição reescreve ATUALIZAVEIS."""
    stmt = insert(Nota).values(**dados, origem=origem, criada_em=agora())
    stmt = stmt.on_conflict_do_update(
        index_elements=["chat_id", "message_id"],
        set_={c: stmt.excluded[c] for c in ATUALIZAVEIS},
    ).returning(Nota.id)
    nota_id = sessao.execute(stmt).scalar_one()
    _gravar_links(sessao, nota_id, dados["tipo"], itens, dados["enviada_em"])
    _gravar_tags(sessao, nota_id, dados.get("texto"))
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


PALAVRA = re.compile(r"\w+")


def consulta_fts(q: str) -> str | None:
    """Cada palavra vira `palavra:*` (prefixo) e todas são exigidas (E lógico). Só caracteres de
    palavra chegam ao `to_tsquery`, então a sintaxe do PostgreSQL nunca chega crua."""
    palavras = PALAVRA.findall(q)
    return " & ".join(f"{p}:*" for p in palavras) or None


def _casa(coluna, fts: str):
    return coluna.op("@@")(func.to_tsquery(literal_column("'notas'::regconfig"), fts))


def _com_tag(tag: str):
    return Nota.id.in_(select(Tag.nota_id).where(Tag.nome == tag.lower()))


def _do_grupo(grupo: str):
    """Documentos do grupo pela extensão do nome (FR-006 da 005); "outro" = nenhum dos demais."""
    nome = func.lower(func.coalesce(Nota.arquivo_nome, ""))
    def casa(exts):
        return or_(*(nome.like(f"%.{e}") for e in exts)) if exts else false()
    if grupo == "outro":
        return not_(or_(*(casa(exts) for _, exts in GRUPOS_DOCUMENTO.values() if exts)))
    return casa(GRUPOS_DOCUMENTO.get(grupo, ("", ()))[1])


def _casa_links(fts: str):
    """Notas com algum link cujo autor/site/endereço ou prévia casa com a busca (FR-001 da 008)."""
    return Nota.id.in_(
        select(Link.nota_id).outerjoin(Previa, Previa.url == Link.url)
        .where(_casa(literal_column("link.busca"), fts) | _casa(literal_column("previa.busca"), fts))
    )


def buscar(
    sessao: Session, q: str = "", tipo: str = "", pagina: int = 1, tag: str = "", grupo: str = "",
    de: str | None = None, ate: str | None = None,
) -> tuple[list[Nota], int]:
    """Lista de notas (todas as abas, exceto a de links, que usa `buscar_links`).
    `de`/`ate` são ISO UTC, comparados como texto com `enviada_em` (gravada no mesmo formato)."""
    filtro = select(Nota)
    if de:
        filtro = filtro.where(Nota.enviada_em >= de)
    if ate:
        filtro = filtro.where(Nota.enviada_em <= ate)
    if tag:
        filtro = filtro.where(_com_tag(tag))
    if grupo:
        filtro = filtro.where(_do_grupo(grupo))
    if q.strip():
        fts = consulta_fts(q)
        if fts is None:
            return [], 0
        filtro = filtro.where(_casa(literal_column("nota.busca"), fts) | _casa_links(fts))
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


def contar_novas(sessao: Session, desde: str) -> int:
    """Notas mais novas que a primeira exibida (aviso da 004); `desde` vazio conta todas."""
    filtro = select(func.count()).select_from(Nota)
    if desde:
        filtro = filtro.where(Nota.enviada_em > desde)
    return sessao.scalar(filtro)


def contar_por_tipo(sessao: Session) -> dict[str, int]:
    """Contagens do caderno inteiro (FR-002 da 002): uma por tipo, mais `falha` e `todas`.
    A aba link conta itens de link; as demais (e `todas`) contam notas (FR-002 da 003)."""
    c = {t: 0 for t in TIPOS} | dict(sessao.execute(select(Nota.tipo, func.count()).group_by(Nota.tipo)).all())
    c["link"] = sessao.scalar(select(func.count()).select_from(Link).join(Nota).where(Nota.tipo == "link"))
    c["todas"] = sum(c[t] for t in TIPOS)  # com "link" já em itens: conta a linha do tempo (010)
    c["falha"] = sessao.scalar(select(func.count()).where(Nota.situacao == "falha"))
    return c


def tags_das_notas(sessao: Session, ids) -> dict[int, list[str]]:
    r: dict[int, list[str]] = {}
    for nota_id, nome in sessao.execute(select(Tag.nota_id, Tag.nome).where(Tag.nota_id.in_(list(ids))).order_by(Tag.nome)):
        r.setdefault(nota_id, []).append(nome)
    return r


def contar_tags(sessao: Session) -> list[tuple[str, int]]:
    """Tags do caderno, da mais usada para a menos usada; empate em ordem alfabética."""
    n = func.count().label("n")
    return [tuple(r) for r in sessao.execute(select(Tag.nome, n).group_by(Tag.nome).order_by(n.desc(), Tag.nome))]


def contar_grupos_documento(sessao: Session) -> list[tuple[str, int]]:
    """Grupos presentes na categoria Documento, na ordem de GRUPOS_DOCUMENTO.
    ponytail: conta em Python sobre os nomes; com dezenas de milhares de documentos, um CASE no SQL."""
    from collections import Counter

    from notas.regras import grupo_documento

    c = Counter(grupo_documento(n) for n in sessao.scalars(select(Nota.arquivo_nome).where(Nota.tipo == "documento")))
    return [(g, c[g]) for g in GRUPOS_DOCUMENTO if c[g]]


def contar_sites(sessao: Session) -> list[tuple[str, int]]:
    """Itens de link por site, do mais usado ao menos usado; "sem site" sempre por último."""
    n = func.count().label("n")
    return [tuple(r) for r in sessao.execute(
        select(Link.site, n).join(Nota).where(Nota.tipo == "link")
        .group_by(Link.site).order_by(Link.site == "", n.desc(), Link.site)
    ).all()]


def buscar_links(
    sessao: Session, site: str | None = None, q: str = "", pagina: int = 1, tag: str = "",
    de: str | None = None, ate: str | None = None,
) -> tuple[list[tuple[Link, Nota, Previa | None]], int]:
    """Aba Link: um item por link (FR-002), do mais recente ao mais antigo pela data do item
    (FR-017). `q` casa com o texto da nota ou com a prévia; `site=''` = sem site identificado."""
    filtro = select(Link, Nota, Previa).join(Nota).outerjoin(Previa, Previa.url == Link.url).where(Nota.tipo == "link")
    if site is not None:
        filtro = filtro.where(Link.site == site)
    if tag:
        filtro = filtro.where(_com_tag(tag))
    if de:
        filtro = filtro.where(Link.data >= de)
    if ate:
        filtro = filtro.where(Link.data <= ate)
    if q.strip():
        fts = consulta_fts(q)
        if fts is None:
            return [], 0
        filtro = filtro.where(
            _casa(literal_column("nota.busca"), fts) | _casa(literal_column("previa.busca"), fts)
            | _casa(literal_column("link.busca"), fts)
        )
    total = sessao.scalar(select(func.count()).select_from(filtro.subquery()))
    linhas = sessao.execute(
        filtro.order_by(Link.data.desc(), Link.nota_id.desc(), Link.posicao)
        .limit(POR_PAGINA).offset((pagina - 1) * POR_PAGINA)
    ).all()
    return [tuple(r) for r in linhas], total


def buscar_linha_do_tempo(
    sessao: Session, q: str = "", pagina: int = 1, tag: str = "", de: str | None = None, ate: str | None = None,
) -> tuple[list[tuple[str, Nota, Link | None, Previa | None]], int]:
    """Aba Todas (010): notas que não são de link e um item por link, numa lista só, do mais
    recente ao mais antigo (links pela data do item, como na aba Link). Devolve
    `[("nota", nota, None, None) | ("link", nota, link, previa)]` e o total de itens."""
    notas = select(Nota.id.label("nota_id"), literal_column("NULL::bigint").label("link_id"),
                   Nota.enviada_em.label("data")).where(Nota.tipo != "link")
    links = (select(Link.nota_id, Link.id, Link.data).join(Nota, Nota.id == Link.nota_id)
             .outerjoin(Previa, Previa.url == Link.url).where(Nota.tipo == "link"))
    if tag:
        notas, links = notas.where(_com_tag(tag)), links.where(_com_tag(tag))
    if de:
        notas, links = notas.where(Nota.enviada_em >= de), links.where(Link.data >= de)
    if ate:
        notas, links = notas.where(Nota.enviada_em <= ate), links.where(Link.data <= ate)
    if q.strip():
        fts = consulta_fts(q)
        if fts is None:
            return [], 0
        notas = notas.where(_casa(literal_column("nota.busca"), fts))
        links = links.where(_casa(literal_column("nota.busca"), fts) | _casa(literal_column("previa.busca"), fts)
                            | _casa(literal_column("link.busca"), fts))
    uniao = notas.union_all(links).subquery()
    total = sessao.scalar(select(func.count()).select_from(uniao))
    pagina_ids = sessao.execute(
        select(uniao.c.nota_id, uniao.c.link_id)
        .order_by(uniao.c.data.desc(), uniao.c.nota_id.desc(), uniao.c.link_id)
        .limit(POR_PAGINA).offset((pagina - 1) * POR_PAGINA)
    ).all()
    por_nota = {n.id: n for n in sessao.scalars(select(Nota).where(Nota.id.in_({i for i, _ in pagina_ids})))}
    por_link = {lk.id: (lk, pv) for lk, pv in sessao.execute(
        select(Link, Previa).outerjoin(Previa, Previa.url == Link.url)
        .where(Link.id.in_({lid for _, lid in pagina_ids if lid is not None})))}
    itens = [("link", por_nota[nid], *por_link[lid]) if lid is not None else ("nota", por_nota[nid], None, None)
             for nid, lid in pagina_ids]
    return itens, total


def links_das_notas(sessao: Session, ids: list[int]) -> dict[int, list[tuple[Link, Previa | None]]]:
    """Itens de link de várias notas numa consulta só (mini-cartões fora da aba Link)."""
    if not ids:
        return {}
    r: dict[int, list] = {}
    for lk, previa in sessao.execute(
        select(Link, Previa).outerjoin(Previa, Previa.url == Link.url)
        .where(Link.nota_id.in_(ids)).order_by(Link.nota_id, Link.posicao)
    ).all():
        r.setdefault(lk.nota_id, []).append((lk, previa))
    return r


def _itens_guardados(origem: str, bruto: str | None, texto: str, chat_id: int, enviada_em: str) -> list[ItemLink]:
    """Itens de uma nota já gravada: pelo JSON original, com as mesmas regras da captura;
    sem JSON utilizável, pela regex sobre o texto."""
    try:
        d = json.loads(bruto)
        m = normalizar_bot_api(d) if origem == "ao_vivo" else normalizar_exportacao(d, chat_id)
        return itens_de_link(m)
    except Exception:
        return itens_do_texto(texto, enviada_em)


def reconstruir_links(conn: Connection) -> int:
    """Refaz os itens de todas as notas de link (FR-015). Idempotente; não toca em `nota`.
    Não faz commit: roda dentro da transação de quem chama (migração ou teste)."""
    t = Link.__table__
    notas = conn.execute(
        select(Nota.id, Nota.origem, Nota.bruto, Nota.texto, Nota.chat_id, Nota.enviada_em)
        .where(Nota.tipo == "link")
    ).all()
    conn.execute(delete(t))
    linhas = [
        linha
        for n in notas
        for linha in _linhas_link(
            n.id, "link", _itens_guardados(n.origem, n.bruto, n.texto, n.chat_id, n.enviada_em), n.enviada_em
        )
    ]
    if linhas:
        conn.execute(insert_core(t), linhas)
        _previas_pendentes(conn, linhas)
    return len(notas)


# --- Fila de prévias (003 US2) -------------------------------------------------------
RECUO = (timedelta(hours=1), timedelta(hours=6), timedelta(hours=24), timedelta(days=7))


def proximas_previas(sessao: Session, agora_: datetime, limite: int = 5) -> list[str]:
    """Pendentes e indisponíveis não definitivas cujo recuo já venceu."""
    vencida = (Previa.tentar_depois_de.is_(None)) | (Previa.tentar_depois_de <= agora_.isoformat(timespec="seconds"))
    return list(sessao.scalars(
        select(Previa.url)
        .where(Previa.situacao.in_(("pendente", "indisponivel")), Previa.definitiva == 0, vencida)
        .order_by(Previa.tentar_depois_de.is_not(None), Previa.tentar_depois_de, Previa.url)
        .limit(limite)
    ))


def registrar_previa(sessao: Session, url: str, r, agora_: datetime) -> None:
    """Transições de data-model: ok (fim), falha temporária (recuo 1 h, 6 h, 24 h, 7 d), definitiva (fim)."""
    p = sessao.get(Previa, url) or Previa(url=url, tentativas=0)
    p.buscada_em = agora_.isoformat(timespec="seconds")
    if r.situacao == "ok":
        p.situacao, p.titulo, p.descricao, p.imagem, p.erro = "ok", r.titulo, r.descricao, r.imagem, None
        p.tentar_depois_de = None
    else:
        p.situacao, p.erro = "indisponivel", r.erro
        p.tentativas = (p.tentativas or 0) + 1
        if r.definitiva:
            p.definitiva, p.tentar_depois_de = 1, None
        else:
            espera = RECUO[min(p.tentativas, len(RECUO)) - 1]
            p.tentar_depois_de = (agora_ + espera).isoformat(timespec="seconds")
    sessao.add(p)
    sessao.commit()


# --- Importação (US5) ---------------------------------------------------------------
ABANDONO = timedelta(hours=1)


class ImportacaoEmAndamento(Exception):
    pass


def nota_existe(sessao: Session, chat_id: int, message_id: int) -> bool:
    return sessao.scalar(
        select(Nota.id).where(Nota.chat_id == chat_id, Nota.message_id == message_id)
    ) is not None


def salvar_importada(sessao: Session, dados: dict, itens: Iterable[ItemLink] = ()) -> bool:
    """Nunca altera nota existente (FR-019). Devolve True se criou."""
    stmt = (
        insert(Nota).values(**dados, origem="importacao", criada_em=agora())
        .on_conflict_do_nothing().returning(Nota.id)
    )
    nota_id = sessao.execute(stmt).scalar()
    if nota_id is not None:
        _gravar_links(sessao, nota_id, dados["tipo"], itens, dados["enviada_em"])
        _gravar_tags(sessao, nota_id, dados.get("texto"))
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
