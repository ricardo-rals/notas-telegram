"""inicial: nota, nota_fts, importacao

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

UPGRADE = [
    """
    CREATE TABLE nota (
        id INTEGER PRIMARY KEY,
        chat_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        enviada_em TEXT NOT NULL,
        editada_em TEXT,
        tipo TEXT NOT NULL CHECK (tipo IN ('texto','link','foto','audio','video','documento',
                                           'localizacao','contato','outro')),
        texto TEXT NOT NULL DEFAULT '',
        link TEXT NOT NULL,
        arquivo_caminho TEXT,
        arquivo_nome TEXT,
        arquivo_tamanho INTEGER,
        situacao TEXT NOT NULL CHECK (situacao IN ('ok','grande_demais','sem_arquivo','falha')),
        erro TEXT,
        origem TEXT NOT NULL CHECK (origem IN ('ao_vivo','importacao')),
        bruto TEXT,
        criada_em TEXT NOT NULL,
        UNIQUE (chat_id, message_id),
        CHECK (situacao <> 'falha' OR erro IS NOT NULL)
    )
    """,
    "CREATE INDEX nota_enviada ON nota (enviada_em DESC)",
    "CREATE INDEX nota_tipo_enviada ON nota (tipo, enviada_em DESC)",
    """
    CREATE VIRTUAL TABLE nota_fts USING fts5(
        texto, content='nota', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
    )
    """,
    """
    CREATE TRIGGER nota_ai AFTER INSERT ON nota BEGIN
        INSERT INTO nota_fts (rowid, texto) VALUES (new.id, new.texto);
    END
    """,
    """
    CREATE TRIGGER nota_ad AFTER DELETE ON nota BEGIN
        INSERT INTO nota_fts (nota_fts, rowid, texto) VALUES ('delete', old.id, old.texto);
    END
    """,
    """
    CREATE TRIGGER nota_au AFTER UPDATE OF texto ON nota BEGIN
        INSERT INTO nota_fts (nota_fts, rowid, texto) VALUES ('delete', old.id, old.texto);
        INSERT INTO nota_fts (rowid, texto) VALUES (new.id, new.texto);
    END
    """,
    """
    CREATE TABLE importacao (
        id INTEGER PRIMARY KEY,
        pasta TEXT NOT NULL,
        via TEXT NOT NULL CHECK (via IN ('terminal','painel')),
        status TEXT NOT NULL CHECK (status IN ('rodando','concluida','falha')),
        iniciada_em TEXT NOT NULL,
        terminada_em TEXT,
        criadas INTEGER NOT NULL DEFAULT 0,
        existentes INTEGER NOT NULL DEFAULT 0,
        ignoradas INTEGER NOT NULL DEFAULT 0,
        falhas INTEGER NOT NULL DEFAULT 0,
        erro TEXT
    )
    """,
    "CREATE UNIQUE INDEX importacao_uma_por_vez ON importacao (status) WHERE status = 'rodando'",
]

DOWNGRADE = [
    "DROP TABLE importacao",
    "DROP TRIGGER nota_au",
    "DROP TRIGGER nota_ad",
    "DROP TRIGGER nota_ai",
    "DROP TABLE nota_fts",
    "DROP TABLE nota",
]


def upgrade() -> None:
    for sql in UPGRADE:
        op.execute(sql)


def downgrade() -> None:
    for sql in DOWNGRADE:
        op.execute(sql)
