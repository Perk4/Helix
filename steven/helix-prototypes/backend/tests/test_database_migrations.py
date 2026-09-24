import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.database import upgrade_to_head
from app.models import Base


def test_an_unversioned_baseline_schema_is_adopted_before_upgrading():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    baseline_tables = [
        table for name, table in Base.metadata.tables.items() if name != "intake_jobs"
    ]
    Base.metadata.create_all(engine, tables=baseline_tables)

    upgrade_to_head(engine)

    assert "intake_jobs" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "b53f9ec18cf2"


def test_a_partial_unversioned_schema_is_not_falsely_stamped():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Base.metadata.tables["audit_events"]])

    with pytest.raises(RuntimeError, match="does not match the Alembic baseline"):
        upgrade_to_head(engine)

    assert "alembic_version" not in inspect(engine).get_table_names()
