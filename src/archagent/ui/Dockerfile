# Interface Streamlit (container `ui`). Contexto de build: raiz do repositório.
FROM ghcr.io/astral-sh/uv:0.9.11-python3.13-bookworm-slim

ARG VERSION=dev
LABEL org.opencontainers.image.title="archagent-ui" \
      org.opencontainers.image.version="${VERSION}"

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --extra ui
COPY src ./src
RUN uv sync --frozen --no-dev --extra ui

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "src/archagent/ui/app.py", "--server.port=8501", \
     "--server.address=0.0.0.0", "--browser.gatherUsageStats=false"]
