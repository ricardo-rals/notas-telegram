"""tag: hashtags das notas (005)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-08
"""

from alembic import op
from sqlalchemy import text

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tag (
            nota_id INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            PRIMARY KEY (nota_id, nome)
        )
        """
    )
    op.execute("CREATE INDEX tag_nome ON tag (nome)")
    # ponytail: importa a regra da aplicação; se `tags` mudar a ponto de quebrar banco novo, congelar aqui
    from notas.regras import tags

    conn = op.get_bind()
    linhas = [
        {"n": nota_id, "t": nome}
        for nota_id, texto in conn.execute(text("SELECT id, texto FROM nota WHERE texto LIKE '%#%'"))
        for nome in tags(texto)
    ]
    if linhas:
        conn.execute(text("INSERT INTO tag (nota_id, nome) VALUES (:n, :t)"), linhas)


def downgrade() -> None:
    op.execute("DROP TABLE tag")
