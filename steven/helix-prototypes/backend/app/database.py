from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import Settings
from .models import Base

BASELINE_REVISION = "bf13e5f55c15"
MIGRATED_TABLES = frozenset({"intake_jobs", "content_drafts", "chat_messages"})
BASELINE_TABLES = frozenset(Base.metadata.tables) - MIGRATED_TABLES


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
        _adopt_unversioned_baseline(connection, config, command)
        command.upgrade(config, "head")


def _adopt_unversioned_baseline(connection: Connection, config: object,
                                  command: object) -> None:
    """Stamp a schema created by the former ``create_all`` startup path.

    Adoption is deliberately conservative. A partially-created or drifted
    schema must stop with an actionable error rather than being stamped as a
    baseline it does not match.
    """
    schema = inspect(connection)
    existing = set(schema.get_table_names())
    if "alembic_version" in existing or not (existing & BASELINE_TABLES):
        return

    missing_tables = BASELINE_TABLES - existing
    unexpected_migrated_tables = (existing - BASELINE_TABLES) & MIGRATED_TABLES
    mismatched_columns: list[str] = []
    for table_name in BASELINE_TABLES & existing:
        expected = set(Base.metadata.tables[table_name].columns.keys())
        actual = {column["name"] for column in schema.get_columns(table_name)}
        if expected != actual:
            mismatched_columns.append(table_name)

    if missing_tables or unexpected_migrated_tables or mismatched_columns:
        details = []
        if missing_tables:
            details.append(f"missing tables: {', '.join(sorted(missing_tables))}")
        if unexpected_migrated_tables:
            details.append(
                "post-baseline tables already exist: "
                + ", ".join(sorted(unexpected_migrated_tables))
            )
        if mismatched_columns:
            details.append(f"column mismatch: {', '.join(sorted(mismatched_columns))}")
        raise RuntimeError(
            "Unversioned HELIX schema does not match the Alembic baseline; "
            "refusing to stamp it (" + "; ".join(details) + ").")

    command.stamp(config, BASELINE_REVISION)


def _serialize_sqlite_writers(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _connect(dbapi_connection: SQLiteConnection, _connection_record: object) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
