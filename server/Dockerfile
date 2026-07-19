FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev

FROM python:3.12-slim AS runtime

RUN groupadd -r appsec && useradd -r -g appsec appsec

# ProjectDiscovery scanner binaries. Chromium is required for katana's -jc flag
# (JavaScript endpoint crawling); ca-certificates for HTTPS scans.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates chromium \
    && rm -rf /var/lib/apt/lists/*
COPY --from=projectdiscovery/nuclei:latest /usr/local/bin/nuclei /usr/local/bin/nuclei
COPY --from=projectdiscovery/katana:latest /usr/local/bin/katana /usr/local/bin/katana

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    CHROME_PATH="/usr/bin/chromium"

# Pre-fetch nuclei templates so the first scan doesn't pay the download cost.
RUN nuclei -update-templates || true

USER appsec

EXPOSE 8000

CMD ["uvicorn", "appsec.main:app", "--host", "0.0.0.0", "--port", "8000"]
