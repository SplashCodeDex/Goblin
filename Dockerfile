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

# Simple healthcheck: check Streamlit port when running UI mode
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD bash -lc 'command -v nc >/dev/null 2>&1 && nc -z localhost 8501 || (command -v bash >/dev/null 2>&1 && (exec </dev/tcp/127.0.0.1/8501) || exit 1)'

CMD []