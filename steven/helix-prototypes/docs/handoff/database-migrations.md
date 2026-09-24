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

## The limitation, stated plainly

**The baseline assumes an empty database.** Run `upgrade head` against a schema that
already has HELIX tables and it fails on the first `CREATE TABLE`:

```
(psycopg.errors.DuplicateTable) relation "section_runs" already exists
```

So there are two cases, and they need different handling.

**A new database** — nothing to do. The app runs `upgrade head` at startup.

**A database that already has the tables** — decide first whether it matches the baseline.

```bash
# Does the existing schema match the models?
HELIX_DATABASE_URL='...?options=-csearch_path%3Dhelix_team03' \
  uv run alembic revision --autogenerate -m "probe"
```

If the generated file contains **no operations**, the schema matches. Delete the probe and
adopt the baseline without running it:

```bash
uv run alembic stamp head
```

If it contains operations, the schema has drifted and stamping would record a lie. Either
apply the generated migration deliberately after reading it, or — on a sandbox with
reproducible data — drop and rebuild.

`helix_team03` was rebuilt and then stamped, so it is at `bf13e5f55c15` with all four
studies reloaded.

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
