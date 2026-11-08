# Agente ArchiMate (container `agent-archimate`). Contexto de build: raiz do repositório.
FROM ghcr.io/astral-sh/uv:0.9.11-python3.13-bookworm-slim

ARG VERSION=dev
LABEL org.opencontainers.image.title="archagent-agent-archimate" \
      org.opencontainers.image.version="${VERSION}"

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 \
    KB_DIR=/app/kb SESSIONS_DIR=/data/sessions

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --extra agent
COPY src ./src
RUN uv sync --frozen --no-dev --extra agent

RUN useradd --create-home --uid 10001 app && mkdir -p /data/sessions && chown -R app /data
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "archagent.agents.archimate.api:app_factory", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
