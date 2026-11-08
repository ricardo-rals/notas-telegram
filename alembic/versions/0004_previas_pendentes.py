"""enfileira prévias dos links gravados antes da fila (0003 sem previa)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-08
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT OR IGNORE INTO previa (url, situacao, definitiva, tentativas) "
        "SELECT DISTINCT url, 'pendente', 0, 0 FROM link WHERE url <> ''"
    )


def downgrade() -> None:
    pass  # ponytail: prévias pendentes a mais não fazem mal; nada a desfazer
