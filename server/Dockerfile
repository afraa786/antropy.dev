FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || \
    uv sync --no-dev --no-install-project

COPY . .

RUN uv sync --no-dev


# ---------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------

FROM python:3.12-slim AS runtime

#
# Create application user
#
RUN groupadd -r appsec && \
    useradd -r -m -d /home/appsec -g appsec appsec

#
# Install runtime dependencies
#
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium && \
    rm -rf /var/lib/apt/lists/*

#
# Copy ProjectDiscovery binaries
#
COPY --from=projectdiscovery/nuclei:latest /usr/local/bin/nuclei /usr/local/bin/nuclei
COPY --from=projectdiscovery/katana:latest /usr/local/bin/katana /usr/local/bin/katana

#
# Prepare HOME directories
#
RUN mkdir -p \
    /home/appsec/.config/nuclei \
    /home/appsec/.config/uncover \
    /home/appsec/.cache/nuclei \
    /home/appsec/.pdcp

#
# Give ownership BEFORE switching user
#
RUN chown -R appsec:appsec /home/appsec

ENV HOME=/home/appsec

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    CHROME_PATH="/usr/bin/chromium"

#
# IMPORTANT
#
# Switch to appsec BEFORE updating templates.
#
USER appsec

#
# Download templates as appsec.
# This prevents root-owned config files.
#
RUN nuclei -update-templates || true

EXPOSE 8000

CMD ["uvicorn", "appsec.main:app","--host","0.0.0.0","--port","8000"]