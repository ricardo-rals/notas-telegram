"""link.busca: autor, site e endereço do link entram na busca (008)

Revision ID: p002
Revises: p001
Create Date: 2026-11-10
"""

from alembic import op

revision = "p002"
down_revision = "p001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # translate troca a pontuação da URL por espaço: "instagram.com/p/abc" vira palavras buscáveis
    op.execute(
        """
        ALTER TABLE link ADD COLUMN busca TSVECTOR GENERATED ALWAYS AS (
            to_tsvector('notas'::regconfig, coalesce(autor, '') || ' ' || site || ' ' ||
                        translate(url, '/.?=&-_:#%+', '           '))
        ) STORED
        """
    )
    op.execute("CREATE INDEX link_busca ON link USING GIN (busca)")


def downgrade() -> None:
    op.execute("ALTER TABLE link DROP COLUMN busca")
