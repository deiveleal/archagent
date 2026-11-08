# tool-archi: Archi 5 pela linha de comando, sem interface gráfica, atrás de uma API mínima.
# Contexto de build: raiz do repositório.
FROM python:3.13-slim-bookworm

ARG ARCHI_VERSION=5.10.0
ARG ARCHI_URL=https://github.com/archimatetool/archi.io/releases/download/5.10/Archi-Linux64-5.10.0.tgz
ARG ARCHI_SHA256=f9422455a00a22f5340dc28692ceafe0ad720c8cde839eaafb0fab1cea57287f
ARG VERSION=dev
LABEL org.opencontainers.image.title="archagent-tool-archi" \
      org.opencontainers.image.version="${VERSION}" \
      archi.version="${ARCHI_VERSION}"

# O Archi é uma aplicação SWT/GTK: precisa de GTK e de uma tela virtual (Xvfb).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl xvfb xauth libgtk-3-0 libxtst6 libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/archi.tgz "${ARCHI_URL}" \
    && echo "${ARCHI_SHA256}  /tmp/archi.tgz" | sha256sum -c - \
    && tar xzf /tmp/archi.tgz -C /opt \
    && rm /tmp/archi.tgz

RUN pip install --no-cache-dir fastapi==0.162.2 uvicorn==0.54.0

RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /home/app

ENV ARCHI_HOME=/opt/Archi ARCHI_VERSION=${ARCHI_VERSION} PYTHONUNBUFFERED=1
COPY --chown=app tools/archi/server.py /home/app/server.py

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
