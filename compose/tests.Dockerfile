# Container de testes (perfil `test`): mesmas dependências dos agentes + dev.
FROM ghcr.io/astral-sh/uv:0.9.11-python3.13-bookworm-slim
ENV UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 LLM_MODE=replay
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --all-extras --no-install-project
COPY . .
RUN uv sync --frozen --all-extras
CMD ["pytest", "--cov", "--cov-report=term-missing:skip-covered"]
