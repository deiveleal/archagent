"""API HTTP do agente ArchiMate (spec §13)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from archagent.agents.archimate.archi import ArchiClient, ArchiIndisponivel
from archagent.agents.archimate.rules import carregar_regras
from archagent.agents.archimate.service import ArchimateService, BriefingNaoConfirmado
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.agents.archimate.vault import Vault
from archagent.core.inputs import EntradaInvalida
from archagent.core.llm import LLM, LLMError, TokenBudgetExceeded, build_llm
from archagent.core.logs import log_event, new_request_id, request_id_var, setup_logging
from archagent.core.sessions import LimiteDeEntradas, SessaoNaoEncontrada, SessionStore

VERSION = "0.2.0"
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


def ok(**dados: Any) -> dict[str, Any]:
    return {**dados, "request_id": request_id_var.get()}


class NovaSessao(BaseModel):
    titulo: str = "Sem título"


class Resposta(BaseModel):
    resposta: str | None = None
    pular: bool = False


def create_app(
    settings: ArchimateSettings | None = None,
    llm: LLM | None = None,
    archi: ArchiClient | None = None,
) -> FastAPI:
    settings = settings or ArchimateSettings()
    setup_logging("agent-archimate", settings.log_level)
    # RF-KB-01: sem regras válidas, o agente não sobe.
    regras = carregar_regras(settings.kb_dir)
    vault = Vault.carregar(
        settings.kb_dir / "archimate" / "vault", settings.vault_incluir_rascunhos
    )
    archi = archi or ArchiClient(settings.tool_archi_url, settings.tool_archi_timeout_seconds)
    store = SessionStore(settings.sessions_dir)
    svc = ArchimateService(settings, llm or build_llm(settings), store, regras, vault, archi)

    app = FastAPI(title="ArchAgent — agente ArchiMate", version=VERSION)
    app.state.svc = svc

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

    @app.exception_handler(SessaoNaoEncontrada)
    async def sessao_404(_: Request, exc: SessaoNaoEncontrada) -> JSONResponse:
        return erro(404, "sessao_inexistente", f"Sessão {exc.args[0]} não encontrada.")

    @app.exception_handler(EntradaInvalida)
    async def entrada_400(_: Request, exc: EntradaInvalida) -> JSONResponse:
        return erro(400, "entrada_invalida", str(exc))

    @app.exception_handler(BriefingNaoConfirmado)
    async def briefing_409(_: Request, exc: BriefingNaoConfirmado) -> JSONResponse:
        return erro(409, "briefing_nao_confirmado", str(exc))

    @app.exception_handler(LimiteDeEntradas)
    async def limite_409(_: Request, exc: LimiteDeEntradas) -> JSONResponse:
        return erro(409, "limite_entradas", str(exc))

    @app.exception_handler(TokenBudgetExceeded)
    async def tokens_429(_: Request, exc: TokenBudgetExceeded) -> JSONResponse:
        return erro(429, "limite_tokens", str(exc))

    @app.exception_handler(LLMError)
    async def llm_502(_: Request, exc: LLMError) -> JSONResponse:
        log_event(logger, "llm.falha", logging.WARNING, tipo=type(exc).__name__)
        return erro(502, "llm_falhou", f"O modelo de linguagem não respondeu como esperado: {exc}")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return erro(exc.status_code, "http", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return erro(422, "entrada_invalida", str(exc.errors()[:3]))

    # ------------------------------------------------------------ saúde

    @app.get("/health")
    def health() -> dict[str, Any]:
        try:
            archi_info: dict[str, Any] = dict(svc.archi.health())
        except ArchiIndisponivel:
            archi_info = {"status": "indisponivel"}
        return ok(
            status="ok",
            versao=VERSION,
            regras={"elementos": len(regras.elementos), "fonte": regras.fonte_relacoes},
            vault={"notas_em_uso": len(vault.notas), "rascunhos": len(vault.rascunhos)},
            tool_archi=archi_info,
        )

    @app.get("/health/llm")
    def health_llm() -> dict[str, Any]:
        """Confirma que o provedor LLM responde (critério de saída da F0)."""
        try:
            res = svc.llm.chat([{"role": "user", "content": "Responda apenas: ok"}], no="health")
        except LLMError as exc:
            log_event(logger, "health.llm", logging.WARNING, resultado="erro")
            raise ApiError(503, "llm_indisponivel", str(exc)) from exc
        return ok(
            status="ok", modelo=res.modelo, resposta=res.texto[:20], latencia_ms=res.latencia_ms
        )

    # ------------------------------------------------------------ sessões

    @app.post("/sessions", status_code=201)
    def criar_sessao(corpo: NovaSessao) -> dict[str, Any]:
        return ok(sessao=store.criar(corpo.titulo).model_dump(mode="json"))

    @app.get("/sessions")
    def listar_sessoes() -> dict[str, Any]:
        return ok(sessoes=[s.model_dump(mode="json") for s in store.listar()])

    @app.get("/sessions/{sid}")
    def obter_sessao(sid: str) -> dict[str, Any]:
        sessao = store.obter(sid)
        entradas = [
            e.model_dump(mode="json", exclude={"conteudo_normalizado"}) for e in store.entradas(sid)
        ]
        return ok(
            sessao=sessao.model_dump(mode="json"),
            entradas=entradas,
            conversa=store.conversa(sid)[-50:],
        )

    # ------------------------------------------------------------ entradas e briefing

    @app.post("/sessions/{sid}/inputs", status_code=201)
    def enviar_entrada(
        sid: str,
        arquivo: Annotated[UploadFile | None, File()] = None,
        texto: Annotated[str | None, Form()] = None,
    ) -> dict[str, Any]:
        store.obter(sid)
        if arquivo is not None:
            dados = arquivo.file.read()
            st = svc.enviar_entrada(sid, nome_arquivo=arquivo.filename or "arquivo", dados=dados)
        elif texto and texto.strip():
            store.registrar_mensagem(sid, "arquiteto", texto)
            st = svc.enviar_entrada(sid, texto=texto)
        else:
            raise ApiError(400, "entrada_invalida", "Envie um arquivo ou o campo 'texto'.")
        return ok(
            entrada=st["entrada"].model_dump(mode="json", exclude={"conteudo_normalizado"}),
            resultado=st["resultado"].model_dump(),
            perguntas=[p.model_dump(mode="json") for p in st.get("perguntas", [])],
        )

    @app.get("/sessions/{sid}/briefing")
    def obter_briefing(
        sid: str, status: str | None = None, tipo: str | None = None
    ) -> dict[str, Any]:
        b = store.briefing(sid)
        return ok(
            confirmado_em=b.confirmado_em,
            itens=[i.model_dump(mode="json") for i in b.filtrar(status, tipo)],
        )

    @app.post("/sessions/{sid}/briefing/confirm")
    def confirmar(sid: str) -> dict[str, Any]:
        b = svc.confirmar_briefing(sid)
        return ok(confirmado_em=b.confirmado_em, status=store.obter(sid).status)

    @app.get("/sessions/{sid}/questions")
    def perguntas(sid: str, todas: bool = False) -> dict[str, Any]:
        lista = store.perguntas(sid)
        if not todas:
            lista = [p for p in lista if p.status == "pendente"]
        return ok(perguntas=[p.model_dump(mode="json") for p in lista])

    @app.post("/sessions/{sid}/questions/{qid}/answer")
    def responder(sid: str, qid: str, corpo: Resposta) -> dict[str, Any]:
        store.obter(sid)
        try:
            p = svc.responder(sid, qid, corpo.resposta, corpo.pular)
        except KeyError as exc:
            raise ApiError(404, "pergunta_inexistente", f"Pergunta {qid} não existe.") from exc
        except ValueError as exc:
            raise ApiError(409, "pergunta_fechada", str(exc)) from exc
        pendentes = [
            x.model_dump(mode="json") for x in store.perguntas(sid) if x.status == "pendente"
        ]
        return ok(pergunta=p.model_dump(mode="json"), perguntas_pendentes=pendentes)

    @app.get("/sessions/{sid}/usage")
    def uso(sid: str) -> dict[str, Any]:
        u = store.uso(sid)
        limite = settings.llm_max_tokens_per_session
        return ok(
            total=u.total,
            limite=limite,
            por_no=u.por_no,
            chamadas=u.chamadas,
            aviso=bool(limite and u.total >= 0.8 * limite),
            bloqueado=bool(limite and u.total >= limite),
        )

    # ------------------------------------------------------------ modelos

    @app.post("/sessions/{sid}/models", status_code=202)
    def gerar(sid: str) -> dict[str, Any]:
        store.obter(sid)
        return ok(**svc.iniciar_geracao(sid))

    @app.get("/sessions/{sid}/models")
    def listar_modelos(sid: str) -> dict[str, Any]:
        sessao = store.obter(sid)
        modelos = []
        for mid in sessao.versoes_modelo:
            m = svc.modelo(sid, mid)
            modelos.append(
                {
                    "id": mid,
                    "gerado_em": m.gerado_em,
                    "viavel": m.validacao.viavel,
                    "elementos": len(m.elementos),
                    "relacoes": len(m.relacoes),
                }
            )
        return ok(modelos=modelos)

    @app.get("/sessions/{sid}/models/{mid}")
    def obter_modelo(sid: str, mid: str) -> dict[str, Any]:
        store.obter(sid)
        try:
            m = svc.modelo(sid, mid)
        except KeyError as exc:
            raise ApiError(404, "modelo_inexistente", f"Modelo {mid} não existe.") from exc
        return ok(modelo=m.model_dump(mode="json"))

    @app.get("/sessions/{sid}/models/{mid}/files/{tipo}")
    def baixar(sid: str, mid: str, tipo: str) -> Response:
        store.obter(sid)
        try:
            conteudo, mime, nome = svc.arquivo_modelo(sid, mid, tipo)
        except KeyError as exc:
            raise ApiError(
                404, "arquivo_inexistente", f"Arquivo '{tipo}' do modelo {mid} não existe."
            ) from exc
        return Response(
            conteudo,
            media_type=mime,
            headers={"content-disposition": f'attachment; filename="{nome}"'},
        )

    @app.get("/sessions/{sid}/events")
    async def eventos(sid: str, desde: int = 0, aguardar: float = 300) -> StreamingResponse:
        """Progresso em tempo real (Server-Sent Events) até o fim dos jobs da sessão."""
        store.obter(sid)

        async def fluxo() -> AsyncIterator[str]:
            i, limite = desde, asyncio.get_running_loop().time() + aguardar
            while True:
                lista = svc.eventos.get(sid, [])
                while i < len(lista):
                    yield f"id: {i}\ndata: {json.dumps(lista[i], ensure_ascii=False)}\n\n"
                    i += 1
                ativos = [
                    j
                    for j in svc.jobs.values()
                    if j["sessao"] == sid and j["status"] == "em_andamento"
                ]
                if not ativos or asyncio.get_running_loop().time() > limite:
                    yield "event: fim\ndata: {}\n\n"
                    return
                await asyncio.sleep(0.5)

        return StreamingResponse(fluxo(), media_type="text/event-stream")

    @app.get("/sessions/{sid}/jobs/{job}")
    def job(sid: str, job: str) -> dict[str, Any]:
        info = svc.jobs.get(job)
        if not info or info["sessao"] != sid:
            raise ApiError(404, "job_inexistente", f"Job {job} não existe.")
        return ok(**info)

    return app


def app_factory() -> FastAPI:
    return create_app()
