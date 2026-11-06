from pathlib import Path

from alembic import context

from notas.db import criar_engine

url = context.config.get_main_option("sqlalchemy.url")
if url:
    caminho = Path(url.removeprefix("sqlite:///"))
else:
    from notas.config import carregar

    caminho = carregar().database_path

engine = criar_engine(caminho)
with engine.connect() as conn:
    context.configure(connection=conn, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
