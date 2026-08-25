# Multi-stage production build for nlsqlc enterprise service
FROM python:3.12-slim AS builder

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

RUN make all || true

FROM python:3.12-slim

WORKDIR /app

RUN useradd -m -u 1000 nlsqlc
COPY --from=builder /app /app
RUN chown -R nlsqlc:nlsqlc /app

USER nlsqlc

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1

ENTRYPOINT ["python3", "tools/server.py", "--host", "0.0.0.0", "--port", "8080"]
