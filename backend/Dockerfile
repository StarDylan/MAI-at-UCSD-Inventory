# ---- Base image ----
FROM python:3.13-slim AS base

ARG S6_OVERLAY_VERSION=3.2.1.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    S6_CMD_WAIT_FOR_SERVICES=0 \
    S6_KILL_GRACETIME=0 \
    S6_SERVICES_READYTIME=5000 \
    GUNICORN_WORKER_CLASS=async \
    WEB_CONCURRENCY=3

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
      nginx curl ca-certificates xz-utils \
      # Uncomment if you need native builds (psycopg, Pillow, etc.):
      # build-essential pkg-config libpq-dev libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Add uv binaries (uv + uvx)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# s6-overlay v3 (noarch + arch)
RUN set -eux; \
  arch="$(dpkg --print-architecture)"; \
  case "$arch" in amd64) s6arch="x86_64";; arm64) s6arch="aarch64";; \
    *) echo "Unsupported arch: $arch"; exit 1;; esac; \
  curl -fsSL -o /tmp/s6-noarch.tar.xz \
    "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz"; \
  curl -fsSL -o /tmp/s6-${s6arch}.tar.xz \
    "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${s6arch}.tar.xz"; \
  tar -C / -Jxpf /tmp/s6-noarch.tar.xz; \
  tar -C / -Jxpf /tmp/s6-${s6arch}.tar.xz; \
  rm -f /tmp/s6-*.tar.xz

# App user + dirs; clean default nginx site
RUN useradd --create-home --shell /bin/bash app && \
    install -d -o app -g app /app /var/log/gunicorn /run && \
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/*

WORKDIR /app


# Copy dependency manifests for caching; copy your app later
COPY pyproject.toml uv.lock /app/

# Prefer uv.lock/pyproject; fallback to requirements.txt — all via uv
RUN uv sync --locked

# ---- Bring in config & service tree ----
COPY docker/nginx.conf /etc/nginx/conf.d/app.conf
COPY docker/gunicorn_conf.py /app/gunicorn_conf.py
COPY docker/s6/ /etc/s6-overlay/s6-rc.d/
RUN find /etc/s6-overlay/s6-rc.d -type f -name run -o -name up -exec chmod +x {} \;

# App code last
COPY . /app

# collect static at build time using uv-run manage.py
RUN uv run manage.py collectstatic --noinput

EXPOSE 80
ENTRYPOINT ["/init"]
