# Servidor MCP (container `mcp`). Contexto de build: raiz do repositório.
FROM ghcr.io/astral-sh/uv:0.9.11-python3.13-bookworm-slim

ARG VERSION=dev
LABEL org.opencontainers.image.title="archagent-mcp" \
      org.opencontainers.image.version="${VERSION}"

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=8000

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --extra mcp
COPY src ./src
RUN uv sync --frozen --no-dev --extra mcp

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["archagent-mcp"]
