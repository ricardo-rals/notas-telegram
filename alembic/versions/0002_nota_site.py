"""nota_site: sites (domínio registrável) das notas de link

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Só o esquema: a 0003 substitui esta tabela por `link` e reconstrói tudo a partir de
    # `nota`, então preencher aqui seria trabalho jogado fora (research R1 da 003).
    op.execute(
        """
        CREATE TABLE nota_site (
            nota_id INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE,
            site TEXT NOT NULL,
            PRIMARY KEY (nota_id, site)
        )
        """
    )
    op.execute("CREATE INDEX nota_site_site ON nota_site (site, nota_id)")


def downgrade() -> None:
    op.execute("DROP TABLE nota_site")
