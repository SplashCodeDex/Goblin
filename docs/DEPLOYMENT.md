# Deployment Guide

This guide covers production-ready deployment for Robin (API + optional Next.js UI), including environment configuration, Docker, and Kubernetes notes.

## 1) Environment and secrets
- Use a .env file for local development only. In production, inject environment variables via your orchestrator (Docker Compose/Swarm/Kubernetes) or a secret manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault).
- Do not bake secrets into the image.
- Set CORS_ALLOW_ORIGINS to explicit origins (avoid `*` in prod). Example: `https://your-ui.example.com`.
- Configure model providers according to your usage:
  - OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, OLLAMA_BASE_URL
- Tor:
  - TOR_SOCKS_HOST (default 127.0.0.1), TOR_SOCKS_PORT (default 9050)
  - Optional control port for circuit renewals: TOR_CONTROL_PORT, TOR_PASSWORD

## 2) Docker image and runtime
- The Dockerfile runs as a non-root user (robin) and disables pip cache.
- Environment variables:
  - PYTHONPATH=/app/src
  - UVICORN_WORKERS (default 2; adjust based on CPU cores)
  - CORS_ALLOW_ORIGINS (comma-separated)
- Keep the base image updated. Consider Python 3.11 for better performance.

## 3) Tor lifecycle options
- Default: entrypoint.sh starts Tor inside the container and waits for SOCKS at 9050.
- Sidecar option (recommended for prod hardening): run Tor as a separate container and point ROBIN to that SOCKS host/port.

Example sidecar in docker-compose.yml:
```
services:
  tor:
    image: dperson/torproxy
    ports:
      - "9050:9050"
  api:
    build:
      context: .
    environment:
      - PYTHONPATH=/app/src
      - TOR_SOCKS_HOST=tor
      - TOR_SOCKS_PORT=9050
    depends_on:
      - tor
```

## 4) Volumes and persistence
- docker-compose mounts:
  - ./data:/app/data (SQLite DB/history)
  - ./.cache:/app/.cache (engine health cache, search cache)
- Ensure these directories exist on the host with appropriate permissions.
- For Kubernetes, use PersistentVolumeClaims.

## 5) Networking and security
- Avoid exposing the API publicly without auth.
- Add optional API key middleware or place FastAPI behind an authenticating reverse proxy (Traefik/Nginx + OAuth2 proxy) and rate limiting.
- Restrict CORS to your UI origin(s).
- Use HTTPS termination at reverse proxy; enable HSTS and modern TLS settings.

## 6) Health checks and monitoring
- Dockerfile has a HEALTHCHECK probing port 8000.
- Use /api/health in readiness/liveness checks.
- Consider structured logging (JSON) and request IDs.
- Add metrics if needed (e.g., Prometheus FastAPI instrumentation).

## 7) Frontend (Next.js)
- Set NEXT_PUBLIC_API_BASE_URL to your API URL (e.g., https://api.example.com).
- Build and serve via a node server or export static (if applicable) behind the same reverse proxy.

### docker-compose quick start
```
cp .env.example .env
# Edit .env (set API keys, CORS_ALLOW_ORIGINS, UVICORN_WORKERS)
docker compose up --build -d
curl http://localhost:8000/api/health
```

### Example docker-compose (API + UI)
```
version: "3.9"
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["bash", "-lc", "python -m uvicorn robin.api.server:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}"]
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app/src
      - UVICORN_WORKERS=2
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./.cache:/app/.cache
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
    ports:
      - "3000:3000"
    volumes:
      - ./web:/app
    depends_on:
      - api
```

## 8) Kubernetes (outline)
- ConfigMap for non-secrets (CORS_ALLOW_ORIGINS, UVICORN_WORKERS, TOR_SOCKS_* if needed).
- Secret for API keys (OPENAI_API_KEY, etc.).
- Deployment with:
  - robin API container
  - Optional tor sidecar or use a shared tor service
  - ReadinessProbe: HTTP GET /api/health
  - LivenessProbe: HTTP GET /api/health
- Service (ClusterIP) for API.
- Ingress with TLS terminating at the proxy; configure CORS and auth at the ingress/controller as needed.

Example Deployment snippet (API container):
```
containers:
- name: robin-api
  image: your-registry/robin:latest
  env:
  - name: PYTHONPATH
    value: /app/src
  - name: CORS_ALLOW_ORIGINS
    value: https://your-ui.example.com
  - name: UVICORN_WORKERS
    value: "2"
  ports:
  - containerPort: 8000
  readinessProbe:
    httpGet:
      path: /api/health
      port: 8000
    initialDelaySeconds: 5
    periodSeconds: 10
  livenessProbe:
    httpGet:
      path: /api/health
      port: 8000
    initialDelaySeconds: 10
    periodSeconds: 20
  volumeMounts:
  - name: data
    mountPath: /app/data
  - name: cache
    mountPath: /app/.cache
```

Example volumes:
```
volumes:
- name: data
  persistentVolumeClaim:
    claimName: robin-data-pvc
- name: cache
  persistentVolumeClaim:
    claimName: robin-cache-pvc
```

## 9) Production checklist
- [ ] CORS_ALLOW_ORIGINS set to trusted origins only
- [ ] Secrets injected via orchestrator (no secrets in image)
- [ ] Volumes/PVCs configured for data and cache
- [ ] Health checks enabled
- [ ] HTTPS termination and authentication in place
- [ ] Logs centralized and monitored
