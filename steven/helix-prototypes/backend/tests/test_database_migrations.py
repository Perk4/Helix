import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.database import RUN_EVENT_TABLES, upgrade_to_head
from app.models import Base

HEAD_REVISION = "9edd082c07ae"


def test_an_unversioned_baseline_schema_is_adopted_before_upgrading():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    baseline_tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name != "intake_jobs" and name not in RUN_EVENT_TABLES
    ]
    Base.metadata.create_all(engine, tables=baseline_tables)

    upgrade_to_head(engine)

    assert "intake_jobs" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == HEAD_REVISION


def test_running_migrations_in_process_keeps_the_server_loggers_enabled():
    """`create_schema` runs Alembic inside the service at startup on PostgreSQL.

    Alembic's env.py loads logging from alembic.ini; with fileConfig's default it
    disabled uvicorn's loggers, so the service stopped logging requests and errors.
    """
    loggers = [logging.getLogger(name) for name in ("uvicorn.error", "uvicorn.access", "app")]
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)

    upgrade_to_head(engine)

    assert [logger.disabled for logger in loggers] == [False, False, False]


def test_a_partial_unversioned_schema_is_not_falsely_stamped():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Base.metadata.tables["audit_events"]])

    with pytest.raises(RuntimeError, match="does not match the Alembic baseline"):
        upgrade_to_head(engine)

    assert "alembic_version" not in inspect(engine).get_table_names()


# --- Run-event tables (#25) under Alembic -------------------------------------------------



BACKEND = Path(__file__).resolve().parents[1]


def _config(connection) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.attributes["connection"] = connection
    return config


def _drift(engine: Engine) -> list[object]:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        return list(compare_metadata(context, Base.metadata))


def _version(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


@pytest.fixture(params=["sqlite", "postgresql"])
def migration_engine(request: pytest.FixtureRequest, tmp_path: Path, tmp_path_factory) -> Iterator[Engine]:
    if request.param == "sqlite":
        engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'migrations.db'}")
        yield engine
        engine.dispose()
        return
    from test_journey_run_events import _postgres_url

    urls = _postgres_url(tmp_path_factory)
    url = next(urls)
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()
        urls.close()


def test_head_includes_run_event_tables_with_no_model_drift(migration_engine: Engine) -> None:
    upgrade_to_head(migration_engine)
    assert _version(migration_engine) == HEAD_REVISION
    assert set(inspect(migration_engine).get_table_names()) >= RUN_EVENT_TABLES
    assert _drift(migration_engine) == []


def test_run_event_migration_downgrades_and_upgrades_cleanly(migration_engine: Engine) -> None:
    upgrade_to_head(migration_engine)
    with migration_engine.begin() as connection:
        command.downgrade(_config(connection), "b53f9ec18cf2")
    tables = set(inspect(migration_engine).get_table_names())
    assert not (RUN_EVENT_TABLES & tables)
    assert "intake_jobs" in tables
    with migration_engine.begin() as connection:
        command.downgrade(_config(connection), "base")
    assert set(inspect(migration_engine).get_table_names()) <= {"alembic_version"}
    upgrade_to_head(migration_engine)
    assert _version(migration_engine) == HEAD_REVISION
    assert _drift(migration_engine) == []


def test_a_steven_workspace_create_all_schema_with_run_events_is_adopted(migration_engine: Engine) -> None:
    """feat/steven-workspace created run_events/run_journey_states via create_all, unversioned."""
    pre_alembic = [table for name, table in Base.metadata.tables.items() if name != "intake_jobs"]
    Base.metadata.create_all(migration_engine, tables=pre_alembic)
    with migration_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO run_journey_states (run_id, study_id, last_sequence, "
                "oldest_retained_sequence, stages, actions) VALUES ('RUN-1', 'STUDY-1', 3, 1, '{}', '{}')"
            )
        )

    upgrade_to_head(migration_engine)

    assert _version(migration_engine) == HEAD_REVISION
    assert "intake_jobs" in inspect(migration_engine).get_table_names()
    with migration_engine.connect() as connection:
        assert connection.scalar(text("SELECT last_sequence FROM run_journey_states")) == 3
    assert _drift(migration_engine) == []


def test_a_drifted_run_event_table_is_not_falsely_stamped() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    baseline = [
        table
        for name, table in Base.metadata.tables.items()
        if name != "intake_jobs" and name not in RUN_EVENT_TABLES
    ]
    Base.metadata.create_all(engine, tables=baseline)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE run_events (id INTEGER PRIMARY KEY, event_id VARCHAR(120))"))

    with pytest.raises(RuntimeError, match="column mismatch: run_events"):
        upgrade_to_head(engine)
    assert "alembic_version" not in inspect(engine).get_table_names()

