FROM python:3.10-slim-bullseye AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN DEBIAN_FRONTEND="noninteractive" apt-get update && \
    apt-get install -y --no-install-recommends \
      tor \
      build-essential \
      curl \
      libssl-dev \
      libffi-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN groupadd -r robin && useradd -r -g robin robin && \
    chown -R robin:robin /app

RUN chmod +x /app/entrypoint.sh

USER robin

ENTRYPOINT ["/app/entrypoint.sh"]

# Healthcheck: check API port when running API mode
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD bash -lc '(exec </dev/tcp/127.0.0.1/8000) || exit 1'

CMD []