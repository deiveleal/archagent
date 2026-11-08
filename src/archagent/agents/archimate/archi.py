"""Cliente do tool-archi: converte o Exchange Format em .archimate (V5)."""

from __future__ import annotations

import httpx

from archagent.agents.archimate.model import Achado


class ArchiIndisponivel(RuntimeError):
    """O tool-archi não respondeu."""


class ArchiClient:
    def __init__(self, url: str, timeout: float = 180.0) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, object]:
        try:
            r = httpx.get(f"{self.url}/health", timeout=5)
            r.raise_for_status()
            dados: dict[str, object] = r.json()
            return dados
        except (httpx.HTTPError, ValueError) as exc:
            raise ArchiIndisponivel(str(exc)) from exc

    def converter(self, exchange: bytes) -> tuple[bytes | None, list[Achado]]:
        """Devolve o .archimate, ou os achados V5 quando o Archi falha."""
        try:
            r = httpx.post(f"{self.url}/convert", content=exchange, timeout=self.timeout,
                           headers={"content-type": "application/xml"})  # fmt: skip
        except httpx.HTTPError as exc:
            raise ArchiIndisponivel(f"tool-archi indisponível: {exc}") from exc
        if r.status_code == 200:
            return r.content, []
        try:
            erro = r.json().get("erro", {})
        except ValueError:
            erro = {"mensagem": r.text[:500]}
        mensagem = erro.get("mensagem", "Falha no Archi")
        log = erro.get("log", "")
        return None, [Achado(criterio="V5", regra=erro.get("codigo", "ARCHI"), severidade="erro",
                             mensagem=f"{mensagem} {log}".strip())]  # fmt: skip
