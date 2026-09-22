FROM python:3.13-slim

RUN pip install --no-cache-dir uv==0.12.15

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY backend/openapi.json ./openapi.json
COPY synthetic-e2e /app/synthetic-e2e

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
