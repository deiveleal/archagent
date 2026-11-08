"""API HTTP do agente ArchiMate (spec §13)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from archagent.core.config import Settings, get_settings
from archagent.core.llm import LLM, LLMError, build_llm
from archagent.core.logs import log_event, new_request_id, request_id_var, setup_logging

VERSION = "0.1.0"
logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem


def erro(status: int, codigo: str, mensagem: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "erro": {"codigo": codigo, "mensagem": mensagem},
            "request_id": request_id_var.get(),
        },
    )


def create_app(settings: Settings | None = None, llm: LLM | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging("agent-archimate", settings.log_level)
    app = FastAPI(title="ArchAgent — agente ArchiMate", version=VERSION)
    app.state.settings = settings
    app.state.llm = llm or build_llm(settings)

    @app.middleware("http")
    async def request_id_mw(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or new_request_id()
        token = request_id_var.set(rid)
        try:
            resposta = await call_next(request)
        finally:
            request_id_var.reset(token)
        resposta.headers["x-request-id"] = rid
        return resposta

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return erro(exc.status, exc.codigo, exc.mensagem)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return erro(exc.status_code, "http", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return erro(422, "entrada_invalida", str(exc.errors()[:3]))

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "versao": VERSION, "request_id": request_id_var.get()}

    @app.get("/health/llm")
    def health_llm() -> dict[str, Any]:
        """Confirma que o provedor LLM responde (critério de saída da F0)."""
        llm_: LLM = app.state.llm
        try:
            res = llm_.chat([{"role": "user", "content": "Responda apenas: ok"}], no="health")
        except LLMError as exc:
            log_event(logger, "health.llm", logging.WARNING, resultado="erro")
            raise ApiError(503, "llm_indisponivel", str(exc)) from exc
        return {
            "status": "ok",
            "modelo": res.modelo,
            "resposta": res.texto[:20],
            "latencia_ms": res.latencia_ms,
            "request_id": request_id_var.get(),
        }

    return app


def app_factory() -> FastAPI:
    return create_app()
