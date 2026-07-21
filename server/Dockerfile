FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev

FROM python:3.12-slim AS runtime

# Give appsec a real home dir — nuclei writes its config/templates there and
# fails with "permission denied: mkdir /home/appsec" without it.
RUN groupadd -r appsec && useradd -r -g appsec -m -d /home/appsec appsec

# System deps. Chromium is required for katana's -jc flag (JavaScript endpoint
# crawling); ca-certificates for HTTPS; curl/unzip to fetch the scanner
# binaries below; libpcap for naabu's raw-socket port scanning.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates chromium curl unzip libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the ProjectDiscovery tools from their official glibc Linux releases.
# NB: do NOT copy binaries out of the projectdiscovery/*:latest images — those
# are Alpine/musl-linked and fail with "no such file or directory" on this
# Debian/glibc base (the musl loader is missing).
ARG NUCLEI_VERSION=3.3.7
ARG KATANA_VERSION=1.1.2
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) pd_arch=amd64 ;; \
      arm64) pd_arch=arm64 ;; \
      *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    cd /tmp; \
    curl -fsSL -o nuclei.zip "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_${pd_arch}.zip"; \
    curl -fsSL -o katana.zip "https://github.com/projectdiscovery/katana/releases/download/v${KATANA_VERSION}/katana_${KATANA_VERSION}_linux_${pd_arch}.zip"; \
    unzip -o nuclei.zip nuclei -d /usr/local/bin; \
    unzip -o katana.zip katana -d /usr/local/bin; \
    chmod +x /usr/local/bin/nuclei /usr/local/bin/katana; \
    rm -f nuclei.zip katana.zip

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    CHROME_PATH="/usr/bin/chromium" \
    HOME="/home/appsec"

USER appsec

# Pre-fetch nuclei templates as the appsec user so the first scan doesn't pay
# the download cost (and so the template cache is owned by the runtime user).
RUN nuclei -update-templates || true

EXPOSE 8000

CMD ["uvicorn", "appsec.main:app", "--host", "0.0.0.0", "--port", "8000"]
