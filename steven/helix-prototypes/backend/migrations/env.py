"""Alembic environment.

The database URL comes from the application settings, not from `alembic.ini`, so
migrations and the running service can never disagree about which database they
are pointed at. That also means a `search_path` in `HELIX_DATABASE_URL` is
honoured, and `alembic_version` lands in the same schema as the tables it
tracks rather than in `public`.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    # `%` is the config-interpolation escape, and a URL carrying
    # `options=-csearch_path%3D...` would otherwise be mangled.
    return get_settings().database_url.replace("%", "%%")


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # When the application calls Alembic it passes its own connection, so the
    # migration runs in the same transaction and the same search_path.
    existing = config.attributes.get("connection")
    if existing is not None:
        context.configure(
            connection=existing,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=existing.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    config.set_main_option("sqlalchemy.url", _database_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite cannot ALTER most things in place; batch mode rewrites the
            # table instead, so one migration runs on both backends.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
