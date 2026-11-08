"""link, previa, previa_fts; remove nota_site

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    CREATE TABLE link (
        id INTEGER PRIMARY KEY,
        nota_id INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE,
        posicao INTEGER NOT NULL,
        url TEXT NOT NULL,
        site TEXT NOT NULL,
        data TEXT NOT NULL,
        autor TEXT,
        UNIQUE (nota_id, url),
        UNIQUE (nota_id, posicao)
    )
    """,
    "CREATE INDEX link_site_data ON link (site, data DESC)",
    "CREATE INDEX link_data ON link (data DESC, posicao)",
    """
    CREATE TABLE previa (
        url TEXT PRIMARY KEY,
        situacao TEXT NOT NULL CHECK (situacao IN ('pendente','ok','indisponivel')),
        titulo TEXT,
        descricao TEXT,
        imagem TEXT,
        erro TEXT,
        definitiva INTEGER NOT NULL DEFAULT 0,
        tentativas INTEGER NOT NULL DEFAULT 0,
        buscada_em TEXT,
        tentar_depois_de TEXT
    )
    """,
    "CREATE INDEX previa_fila ON previa (situacao, tentar_depois_de)",
    """
    CREATE VIRTUAL TABLE previa_fts USING fts5(
        titulo, descricao, content='previa', content_rowid='rowid',
        tokenize='unicode61 remove_diacritics 2'
    )
    """,
    """
    CREATE TRIGGER previa_ai AFTER INSERT ON previa BEGIN
        INSERT INTO previa_fts (rowid, titulo, descricao) VALUES (new.rowid, new.titulo, new.descricao);
    END
    """,
    """
    CREATE TRIGGER previa_ad AFTER DELETE ON previa BEGIN
        INSERT INTO previa_fts (previa_fts, rowid, titulo, descricao)
        VALUES ('delete', old.rowid, old.titulo, old.descricao);
    END
    """,
    """
    CREATE TRIGGER previa_au AFTER UPDATE OF titulo, descricao ON previa BEGIN
        INSERT INTO previa_fts (previa_fts, rowid, titulo, descricao)
        VALUES ('delete', old.rowid, old.titulo, old.descricao);
        INSERT INTO previa_fts (rowid, titulo, descricao) VALUES (new.rowid, new.titulo, new.descricao);
    END
    """,
]

DOWNGRADE = [
    "DROP TRIGGER previa_au",
    "DROP TRIGGER previa_ad",
    "DROP TRIGGER previa_ai",
    "DROP TABLE previa_fts",
    "DROP TABLE previa",
    "DROP TABLE link",
    # Volta à 002 com nota_site vazia; reclassificar os sites fica fora do escopo.
    """
    CREATE TABLE nota_site (
        nota_id INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE,
        site TEXT NOT NULL,
        PRIMARY KEY (nota_id, site)
    )
    """,
    "CREATE INDEX nota_site_site ON nota_site (site, nota_id)",
]


def upgrade() -> None:
    for sql in UPGRADE:
        op.execute(sql)
    # Itens de link das notas já guardadas (FR-015), com as mesmas regras da captura.
    # ponytail: importa código da aplicação; se regras mudar a ponto de quebrar banco novo, congelar a função aqui
    from notas.repositorio import reconstruir_links

    reconstruir_links(op.get_bind())
    op.execute("DROP TABLE nota_site")


def downgrade() -> None:
    for sql in DOWNGRADE:
        op.execute(sql)
