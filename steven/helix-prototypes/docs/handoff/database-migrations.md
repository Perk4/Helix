# Database migrations

`create_schema()` was `Base.metadata.create_all(engine)`. That creates tables that are
**missing** and never alters one that already exists, so a column added to a model after
a database was created simply never appears. The service starts cleanly and the failure
surfaces later, on a query:

```
column section_runs.drafting_cycle_id does not exist
```

That is not hypothetical — it is what happened to `helix_team03`, created hours before
`SectionRunRow` gained `drafting_cycle_id`, `attempt` and `uq_section_run_attempt`.

## What changed

Alembic, with the baseline generated from the current models
(`bf13e5f55c15`, 12 tables).

```python
def create_schema(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)   # throwaway test databases
        return
    upgrade_to_head(engine)                # anything real
```

SQLite keeps `create_all` deliberately: every test builds a fresh database and stamping a
migration chain would cost time for no safety. Postgres runs migrations.

`migrations/env.py` takes the URL from `get_settings()`, never from `alembic.ini`, so the
migration and the running service cannot point at different databases. When the app calls
Alembic it passes its own connection, so the migration runs in the same transaction and
the same `search_path` — which is why `alembic_version` lands in `helix_team03` rather
than in `public`.

## Verified

| | |
|---|---|
| baseline matches the models | `alembic revision --autogenerate` on a migrated database produces **0 operations** |
| fresh Postgres schema | 13 tables, `alembic_version = bf13e5f55c15`, `drafting_cycle_id` present |
| re-running is a no-op | version unchanged |
| `alembic_version` placement | created in the target schema, not `public` |
| test suite | 84 failed / 87 passed — identical to the `origin/main` baseline, **0 new failures** |

## Adopting databases created before Alembic

At startup, an unversioned schema created by the former `create_all` path is checked before
any migration runs. If every baseline table and column is present, the app stamps
`bf13e5f55c15` and applies later migrations. Existing tables are never replayed.

The check is deliberately conservative. A partial schema, an already-present post-baseline
table, or a baseline column mismatch stops startup with an `Unversioned HELIX schema does
not match` error. Automatically stamping one of those databases would record a false
revision and hide drift.

For a rejected schema, inspect the difference before taking action:

```bash
HELIX_DATABASE_URL='...?options=-csearch_path%3Dhelix_team03' \
  uv run alembic revision --autogenerate -m "probe"
```

Delete the probe after inspection. Apply a reviewed corrective migration, or — only for a
sandbox with reproducible data — drop and rebuild. Do not manually stamp a mismatched
schema.

## Adding a migration

```bash
# after changing a model
HELIX_DATABASE_URL='sqlite+pysqlite:///./scratch.db' \
  uv run alembic upgrade head
HELIX_DATABASE_URL='sqlite+pysqlite:///./scratch.db' \
  uv run alembic revision --autogenerate -m "what changed"
```

Read the generated file before committing it. Autogenerate does not always get JSON
variants right — the baseline needed `from sqlalchemy import Text` added by hand, because
it rendered `JSONB(astext_type=Text())` without importing `Text`.
