"""Copia o caderno do SQLite (fatias 001–006) para o PostgreSQL, uma vez (007).

`uv run --env-file .env python -m notas.migrar_sqlite [arquivo.db]`; sem argumento, usa
`DATABASE_PATH` ou `%LOCALAPPDATA%\\notas-telegram\\notas.db`. O SQLite é aberto só para leitura e
fica intacto. Notas (com os mesmos ids), importações e prévias são copiadas; links e tags são
refeitos com as regras atuais.
"""

import sqlite3
import sys
from pathlib import Path

from sqlalchemy import Engine, func, insert, select, text

from notas.config import ErroConfig, carregar
from notas.db import Importacao, Nota, Previa, Tag, criar_engine, exigir_revisao_atual
from notas.regras import tags
from notas.repositorio import reconstruir_links


class ErroMigracao(Exception):
    pass


def _linhas(src: sqlite3.Connection, tabela: str, destino) -> list[dict]:
    """Só as colunas que existem nos dois lados (o SQLite pode estar numa revisão antiga)."""
    if not src.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabela,)).fetchone():
        return []
    origem = {r[1] for r in src.execute(f"PRAGMA table_info({tabela})")}
    colunas = [c.name for c in destino.__table__.columns if c.name in origem]
    return [dict(zip(colunas, r)) for r in src.execute(f"SELECT {', '.join(colunas)} FROM {tabela}")]


def migrar(origem: Path, engine: Engine) -> dict[str, int]:
    if not Path(origem).is_file():
        raise ErroMigracao(f"não encontrei o SQLite em {origem}")
    src = sqlite3.connect(f"file:{Path(origem).as_posix()}?mode=ro", uri=True)
    try:
        notas, importacoes, previas = (_linhas(src, t, m) for t, m in
                                       (("nota", Nota), ("importacao", Importacao), ("previa", Previa)))
    finally:
        src.close()
    with engine.begin() as conn:
        if conn.scalar(select(func.count()).select_from(Nota)):
            raise ErroMigracao("o PostgreSQL já tem notas; a cópia só roda num banco vazio")
        for modelo, linhas in ((Nota, notas), (Importacao, importacoes), (Previa, previas)):
            if linhas:
                conn.execute(insert(modelo), linhas)
        reconstruir_links(conn)  # links + prévias pendentes das URLs que faltarem
        linhas_tag = [{"nota_id": i, "nome": n} for i, texto in conn.execute(select(Nota.id, Nota.texto))
                      for n in tags(texto)]
        if linhas_tag:
            conn.execute(insert(Tag), linhas_tag)
        for tabela in ("nota", "importacao"):  # próximos ids depois dos copiados
            conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
                              f"coalesce((SELECT max(id) FROM {tabela}), 0) + 1, false)"))
        return {
            "notas": len(notas), "importacoes": len(importacoes), "previas": len(previas),
            "links": conn.scalar(text("SELECT count(*) FROM link")), "tags": len(linhas_tag),
        }


def main() -> None:
    try:
        cfg = carregar()
    except ErroConfig as e:
        raise SystemExit(f"Configuração inválida: {e}") from None
    origem = Path(sys.argv[1]) if len(sys.argv) > 1 else cfg.sqlite_antigo
    engine = criar_engine(cfg.database_url)
    exigir_revisao_atual(engine)
    try:
        c = migrar(origem, engine)
    except ErroMigracao as e:
        raise SystemExit(f"Migração recusada: {e}") from None
    print(f"Copiado de {origem}: {c['notas']} notas, {c['importacoes']} importações, {c['previas']} prévias; "
          f"refeitos {c['links']} links e {c['tags']} tags.")


if __name__ == "__main__":
    main()
