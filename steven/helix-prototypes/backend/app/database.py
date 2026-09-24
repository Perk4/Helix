from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import Settings
from .models import Base


def create_database_engine(settings: Settings) -> Engine:
    options: dict[str, object] = {"pool_pre_ping": True}
    sqlite = settings.database_url.startswith("sqlite")
    memory = sqlite and settings.database_url.endswith(":memory:")
    if sqlite:
        options["connect_args"] = {"check_same_thread": False, "timeout": 30.0}
        if memory:
            options["poolclass"] = StaticPool
    engine = create_engine(settings.database_url, **options)
    if sqlite and not memory:
        _serialize_sqlite_writers(engine)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_schema(engine: Engine) -> None:
    """Bring the database to the current schema.

    `Base.metadata.create_all` only creates tables that are missing; it never
    alters one that already exists. So a column added to a model after a
    database was created simply never appears, the service starts cleanly, and
    the failure surfaces later as `UndefinedColumn` on a query. That happened
    when `section_runs` gained `drafting_cycle_id`.

    Migrations are therefore authoritative on a real database. `create_all` is
    kept only for SQLite, where every test builds a throwaway database from
    scratch and stamping a migration chain would cost time for no safety.
    """
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
        return
    upgrade_to_head(engine)


def upgrade_to_head(engine: Engine) -> None:
    """Run Alembic against an existing engine, inside its connection.

    Sharing the connection matters: `HELIX_DATABASE_URL` may carry a
    `search_path`, and `alembic_version` has to land in the same schema as the
    tables it tracks rather than in `public`.
    """
    from alembic import command
    from alembic.config import Config

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location",
                           str(Path(__file__).resolve().parents[1] / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def _serialize_sqlite_writers(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _connect(dbapi_connection: SQLiteConnection, _connection_record: object) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
