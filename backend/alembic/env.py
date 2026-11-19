import sys
from os.path import abspath, dirname
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool, text, Table, MetaData, Column, String, PrimaryKeyConstraint
from alembic import context
from alembic.ddl.impl import DefaultImpl

# Guarantee that alembic_version table uses VARCHAR(64) for descriptive revision identifiers
def _custom_version_table_impl(
    self,
    *,
    version_table: str,
    version_table_schema: str | None,
    version_table_pk: bool,
    **kw,
) -> Table:
    vt = Table(
        version_table,
        MetaData(),
        Column("version_num", String(64), nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        vt.append_constraint(
            PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc")
        )
    return vt

DefaultImpl.version_table_impl = _custom_version_table_impl

# Add root directory to sys.path
sys.path.insert(0, abspath(dirname(dirname(dirname(__file__)))))

from backend.app.core.config import settings
from backend.app.database.base import Base
import backend.app.models  # Ensure all models are registered

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use configured sqlalchemy.url if provided, otherwise default to application settings
db_url = config.get_main_option("sqlalchemy.url")
if not db_url:
    db_url = settings.DATABASE_URL
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if "-pooler" in url:
        # Per Neon best practice: DDL migrations require direct unpooled connection
        url = url.replace("-pooler", "")

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    from sqlalchemy import create_engine
    connectable = create_engine(url, connect_args=connect_args, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        # Guarantee existing alembic_version column is VARCHAR(64) on PostgreSQL
        try:
            connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)"))
            connection.commit()
        except Exception:
            connection.rollback()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
