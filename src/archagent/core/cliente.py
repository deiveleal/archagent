"""Cliente HTTP da API do agente (spec §13), usado pela interface e pelo servidor MCP.

Nenhum dos dois tem lógica de agente: tudo passa por aqui.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx


class ErroApi(RuntimeError):
    def __init__(self, status: int, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem


class AgenteCliente:
    def __init__(self, url: str, timeout: float = 300.0) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _req(self, metodo: str, caminho: str, **kw: Any) -> Any:
        try:
            r = httpx.request(metodo, f"{self.url}{caminho}", timeout=self.timeout, **kw)
        except httpx.HTTPError as exc:
            raise ErroApi(0, "sem_conexao", f"Agente indisponível: {exc}") from exc
        if r.status_code >= 400:
            try:
                e = r.json().get("erro", {})
            except ValueError:
                e = {}
            raise ErroApi(r.status_code, e.get("codigo", "erro"), e.get("mensagem", r.text[:300]))
        ctype = r.headers.get("content-type", "")
        return r.json() if ctype.startswith("application/json") else r.content

    # ------------------------------------------------------------ sessões

    def saude(self) -> dict[str, Any]:
        dados: dict[str, Any] = self._req("GET", "/health")
        return dados

    def sessoes(self) -> list[dict[str, Any]]:
        return list(self._req("GET", "/sessions")["sessoes"])

    def criar_sessao(self, titulo: str) -> dict[str, Any]:
        return dict(self._req("POST", "/sessions", json={"titulo": titulo})["sessao"])

    def sessao(self, sid: str) -> dict[str, Any]:
        return dict(self._req("GET", f"/sessions/{sid}"))

    def uso(self, sid: str) -> dict[str, Any]:
        return dict(self._req("GET", f"/sessions/{sid}/usage"))

    # ------------------------------------------------------------ entradas e conversa

    def enviar_arquivo(self, sid: str, nome: str, dados: bytes) -> dict[str, Any]:
        return dict(self._req("POST", f"/sessions/{sid}/inputs", files={"arquivo": (nome, dados)}))

    def enviar_mensagem(self, sid: str, texto: str) -> dict[str, Any]:
        """Usa /messages (conversa); se o agente ainda não tiver, envia como entrada de texto."""
        try:
            return dict(self._req("POST", f"/sessions/{sid}/messages", json={"texto": texto}))
        except ErroApi as exc:
            if exc.status not in (404, 405):
                raise
        return dict(self._req("POST", f"/sessions/{sid}/inputs", data={"texto": texto}))

    # ------------------------------------------------------------ briefing e perguntas

    def briefing(self, sid: str) -> dict[str, Any]:
        return dict(self._req("GET", f"/sessions/{sid}/briefing"))

    def confirmar(self, sid: str) -> dict[str, Any]:
        return dict(self._req("POST", f"/sessions/{sid}/briefing/confirm"))

    def perguntas(self, sid: str) -> list[dict[str, Any]]:
        return list(self._req("GET", f"/sessions/{sid}/questions")["perguntas"])

    def responder(self, sid: str, qid: str, resposta: str | None, pular: bool) -> dict[str, Any]:
        return dict(
            self._req(
                "POST",
                f"/sessions/{sid}/questions/{qid}/answer",
                json={"resposta": resposta, "pular": pular},
            )
        )

    # ------------------------------------------------------------ modelos

    def gerar_modelo(self, sid: str) -> dict[str, Any]:
        return dict(self._req("POST", f"/sessions/{sid}/models"))

    def modelos(self, sid: str) -> list[dict[str, Any]]:
        return list(self._req("GET", f"/sessions/{sid}/models")["modelos"])

    def modelo(self, sid: str, mid: str) -> dict[str, Any]:
        return dict(self._req("GET", f"/sessions/{sid}/models/{mid}")["modelo"])

    def job(self, sid: str, job: str) -> dict[str, Any]:
        return dict(self._req("GET", f"/sessions/{sid}/jobs/{job}"))

    def enviar_texto(self, sid: str, texto: str) -> dict[str, Any]:
        """Envia texto como entrada (material a interpretar), sem passar pela conversa."""
        return dict(self._req("POST", f"/sessions/{sid}/inputs", data={"texto": texto}))

    def arquivo(self, sid: str, mid: str, tipo: str) -> bytes:
        dados: bytes = self._req("GET", f"/sessions/{sid}/models/{mid}/files/{tipo}")
        return dados

    def eventos(self, sid: str, desde: int = 0) -> Iterator[dict[str, Any]]:
        """Lê o fluxo SSE de progresso até `event: fim`."""
        with httpx.stream(
            "GET",
            f"{self.url}/sessions/{sid}/events",
            params={"desde": desde},
            timeout=httpx.Timeout(self.timeout, read=None),
        ) as r:
            evento = ""
            for linha in r.iter_lines():
                if linha.startswith("event:"):
                    evento = linha.split(":", 1)[1].strip()
                elif linha.startswith("data:"):
                    if evento == "fim":
                        return
                    yield json.loads(linha.split(":", 1)[1])
                elif not linha:
                    evento = ""
