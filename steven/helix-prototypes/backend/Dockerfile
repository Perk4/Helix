FROM python:3.13-slim

RUN pip install --no-cache-dir uv==0.12.15

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
# create_schema() runs Alembic on PostgreSQL (the compose database) and reads these
# relative to app/, so the image must carry them or startup fails before /health.
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY backend/openapi.json ./openapi.json
COPY synthetic-e2e /app/synthetic-e2e

# Runtime resources, not build inputs. `codex_repository_root` defaults to
# /app, and the service reads the agent skill, its section presentation
# contracts, and the evidence-pipeline contracts and section packages from
# there. Without these the container starts and answers /health, then raises
# FileNotFoundError on the first section run, because `_file_hash` reads the
# skill with no guard. Architecture doc, Priority 0.
COPY .agents/skills/helix-section-agent /app/.agents/skills/helix-section-agent
COPY skills/helix-evidence-pipeline /app/skills/helix-evidence-pipeline

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
