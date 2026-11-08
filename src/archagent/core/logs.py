"""Logs em JSON com request_id e sessão (spec RNF-10/RNF-11, harness §8.1).

Nunca registrar chaves, conteúdo das entradas ou respostas do LLM.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
session_var: ContextVar[str | None] = ContextVar("sessao", default=None)

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|authorization|bearer)\s*[:=]?\s*[A-Za-z0-9_\-\.]{8,}"),
]


def redact(texto: str) -> str:
    for padrao in _SECRET_PATTERNS:
        texto = padrao.sub("[removido]", texto)
    return texto


def new_request_id() -> str:
    return f"r-{uuid.uuid4().hex[:12]}"


class JsonFormatter(logging.Formatter):
    def __init__(self, servico: str) -> None:
        super().__init__()
        self.servico = servico

    def format(self, record: logging.LogRecord) -> str:
        dados: dict[str, Any] = {
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "nivel": record.levelname.lower(),
            "servico": self.servico,
            "request_id": request_id_var.get(),
            "sessao": session_var.get(),
            "evento": getattr(record, "evento", None) or record.getMessage(),
        }
        extras = getattr(record, "campos", None)
        if isinstance(extras, dict):
            dados.update(extras)
        if record.exc_info:
            dados["erro"] = redact(self.formatException(record.exc_info))
        return redact(json.dumps(dados, ensure_ascii=False, default=str))


def setup_logging(servico: str, nivel: str = "INFO") -> None:
    raiz = logging.getLogger()
    raiz.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(servico))
    raiz.addHandler(handler)
    raiz.setLevel(nivel.upper())
    for ruidoso in ("httpx", "httpx2", "httpcore", "openai"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


def log_event(
    logger: logging.Logger, evento: str, nivel: int = logging.INFO, **campos: Any
) -> None:
    logger.log(nivel, evento, extra={"evento": evento, "campos": campos})
