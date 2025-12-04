FROM python:3.10-slim-bullseye AS builder

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
    pip install -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Healthcheck: check API port when running API mode
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD bash -lc '(exec </dev/tcp/127.0.0.1/8000) || exit 1'

CMD []