from alembic import context

from notas.db import criar_engine

url = context.config.attributes.get("url")
if not url:  # `alembic upgrade head` no terminal: usa o .env
    from notas.config import carregar

    url = carregar().database_url

engine = criar_engine(url)
with engine.connect() as conn:
    context.configure(connection=conn)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
