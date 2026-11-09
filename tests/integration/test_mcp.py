"""N2: servidor MCP por HTTP (streamable-http) falando com o agente real."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
import pytest

from mcp import Client

pytestmark = pytest.mark.integration

URL = os.environ.get("MCP_URL", "http://mcp:8000/mcp")


def test_health() -> None:
    r = httpx.get(URL.removesuffix("/mcp") + "/health", timeout=10)
    assert r.json()["status"] == "ok"


def test_sessao_pelo_mcp() -> None:
    async def rodar() -> tuple[Any, Any, Any]:
        async with Client(URL) as c:
            criada = await c.call_tool("criar_sessao", {"titulo": "Teste MCP"})
            sid = json.loads(criada.content[0].text)["sessao"]["id"]
            briefing = await c.call_tool("ver_briefing", {"sessao": sid})
            inexistente = await c.call_tool("ver_briefing", {"sessao": "S-nao-existe"})
            return criada, briefing, inexistente

    criada, briefing, inexistente = asyncio.run(rodar())
    assert not criada.is_error
    assert json.loads(briefing.content[0].text)["itens"] == []
    # O erro da API chega ao cliente como erro da ferramenta.
    assert inexistente.is_error
    assert "sessao_inexistente" in inexistente.content[0].text
