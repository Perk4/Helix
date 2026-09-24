import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.database import BASELINE_TABLES, upgrade_to_head
from app.models import Base


def test_an_unversioned_baseline_schema_is_adopted_before_upgrading():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    baseline_tables = [Base.metadata.tables[name] for name in BASELINE_TABLES]
    Base.metadata.create_all(engine, tables=baseline_tables)

    upgrade_to_head(engine)

    schema = inspect(engine)
    assert {"intake_jobs", "content_drafts", "chat_messages"} <= set(schema.get_table_names())
    assert "draft_version" in {column["name"] for column in schema.get_columns("chat_messages")}
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "c24154d7a8e9"


def test_a_partial_unversioned_schema_is_not_falsely_stamped():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[Base.metadata.tables["audit_events"]])

    with pytest.raises(RuntimeError, match="does not match the Alembic baseline"):
        upgrade_to_head(engine)

    assert "alembic_version" not in inspect(engine).get_table_names()
