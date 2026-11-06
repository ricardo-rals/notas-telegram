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
    # Classifica as notas já guardadas (FR-011) com as mesmas regras da captura.
    # ponytail: importa código da aplicação; se regras mudar a ponto de quebrar banco novo, congelar a função aqui
    from notas.repositorio import reclassificar_sites

    reclassificar_sites(op.get_bind())


def downgrade() -> None:
    op.execute("DROP TABLE nota_site")
