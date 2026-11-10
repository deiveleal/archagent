"""Testes N1 do servidor MCP: protocolo em memória e API do agente simulada (respx)."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

import httpx
import respx
from starlette.testclient import TestClient

from archagent.mcp.server import McpSettings, criar_servidor
from mcp import Client

URL = "http://agente:8000"


def cfg(**kw: Any) -> McpSettings:
    return McpSettings(agent_archimate_url=URL, mcp_intervalo_consulta_segundos=0.0, **kw)


def chamar(nome: str, args: dict[str, Any], **kw: Any) -> tuple[bool, Any]:
    """Chama a ferramenta pelo protocolo MCP; devolve (é_erro, dados ou texto)."""

    async def rodar() -> Any:
        async with Client(criar_servidor(cfg(**kw))) as c:
            return await c.call_tool(nome, args)

    r = asyncio.run(rodar())
    texto = r.content[0].text if r.content else ""
    if r.is_error:
        return True, texto
    return False, r.structured_content if r.structured_content is not None else json.loads(texto)


MODELO = {
    "id": "M-001",
    "validacao": {
        "viavel": True,
        "criterios": {"V1": True, "V2": True, "V3": True, "V4": True, "V5": True},
        "erros": [],
        "avisos": [{"criterio": "V3", "regra": "COE-04", "mensagem": "Ator sem processo"}],
    },
    "rodadas_correcao": 1,
    "elementos": [
        {"id": "e1", "tipo": "BusinessActor", "nome": "Cliente", "premissa": False},
        {"id": "e2", "tipo": "ApplicationComponent", "nome": "Portal", "premissa": True},
    ],
    "relacoes": [{"tipo": "Serving", "origem": "e2", "destino": "e1"}],
    "visoes": [{"id": "v1", "nome": "Visão geral"}],
}


def test_lista_as_ferramentas() -> None:
    async def rodar() -> list[str]:
        async with Client(criar_servidor(cfg())) as c:
            return [t.name for t in (await c.list_tools()).tools]

    nomes = asyncio.run(rodar())
    assert {
        "criar_sessao",
        "enviar_texto",
        "enviar_arquivo",
        "ver_briefing",
        "responder_pergunta",
        "confirmar_briefing",
        "gerar_modelo",
        "baixar_arquivo",
        "enviar_mensagem",
    } <= set(nomes)


@respx.mock
def test_enviar_texto_resume_a_entrada() -> None:
    rota = respx.post(f"{URL}/sessions/S-1/inputs").mock(
        return_value=httpx.Response(
            201,
            json={
                "entrada": {"id": "E-001", "tipo": "texto", "formato": "txt", "status": "ok"},
                "resultado": {"novos": ["B-001"]},
                "perguntas": [
                    {"id": "Q-001", "item": "B-001", "texto": "Qual?", "impacto": "alto"}
                ],
            },
        )
    )
    erro, dados = chamar("enviar_texto", {"sessao": "S-1", "texto": "O cliente usa o portal."})
    assert not erro
    assert dados["entrada"]["id"] == "E-001"
    assert dados["perguntas"][0]["id"] == "Q-001"
    assert b"texto=" in rota.calls[0].request.content


@respx.mock
def test_erro_da_api_vira_erro_da_ferramenta() -> None:
    respx.get(f"{URL}/sessions/S-9/briefing").mock(
        return_value=httpx.Response(
            404,
            json={"erro": {"codigo": "sessao_inexistente", "mensagem": "Sessão S-9 não existe."}},
        )
    )
    erro, texto = chamar("ver_briefing", {"sessao": "S-9"})
    assert erro and "sessao_inexistente" in texto


@respx.mock
def test_ver_briefing_filtra_inativos() -> None:
    item = {"tipo": "ator", "nome": "Cliente", "confianca": "alta", "origens": []}
    respx.get(f"{URL}/sessions/S-1/briefing").mock(
        return_value=httpx.Response(
            200,
            json={
                "confirmado_em": None,
                "itens": [
                    {**item, "id": "B-001", "status": "ativo"},
                    {**item, "id": "B-002", "status": "superado", "superado_por": "B-001"},
                ],
            },
        )
    )
    _, dados = chamar("ver_briefing", {"sessao": "S-1"})
    assert [i["id"] for i in dados["itens"]] == ["B-001"]
    _, todos = chamar("ver_briefing", {"sessao": "S-1", "incluir_inativos": True})
    assert todos["itens"][1]["superado_por"] == "B-001"


def test_enviar_arquivo_exige_uma_fonte() -> None:
    erro, texto = chamar("enviar_arquivo", {"sessao": "S-1", "nome": "a.txt"})
    assert erro and "exatamente um" in texto
    erro, texto = chamar(
        "enviar_arquivo", {"sessao": "S-1", "nome": "a.txt", "conteudo": "x", "caminho": "a.txt"}
    )
    assert erro


@respx.mock
def test_enviar_arquivo_base64() -> None:
    rota = respx.post(f"{URL}/sessions/S-1/inputs").mock(
        return_value=httpx.Response(201, json={"entrada": {"id": "E-002"}, "resultado": {}})
    )
    b64 = base64.b64encode(b"\x89PNG-dados").decode()
    erro, _ = chamar(
        "enviar_arquivo", {"sessao": "S-1", "nome": "quadro.png", "conteudo_base64": b64}
    )
    assert not erro
    assert b"\x89PNG-dados" in rota.calls[0].request.content


def test_caminho_desligado_e_fora_da_pasta(tmp_path: Path) -> None:
    erro, texto = chamar("enviar_arquivo", {"sessao": "S-1", "nome": "a.txt", "caminho": "a.txt"})
    assert erro and "MCP_PASTA_ARQUIVOS" in texto
    erro, texto = chamar(
        "enviar_arquivo",
        {"sessao": "S-1", "nome": "a.txt", "caminho": "../segredo.txt"},
        mcp_pasta_arquivos=str(tmp_path),
    )
    assert erro and "dentro de" in texto


@respx.mock
def test_caminho_dentro_da_pasta(tmp_path: Path) -> None:
    (tmp_path / "ata.md").write_text("# Ata", encoding="utf-8")
    rota = respx.post(f"{URL}/sessions/S-1/inputs").mock(
        return_value=httpx.Response(201, json={"entrada": {"id": "E-003"}, "resultado": {}})
    )
    erro, _ = chamar(
        "enviar_arquivo",
        {"sessao": "S-1", "nome": "ata.md", "caminho": "ata.md"},
        mcp_pasta_arquivos=str(tmp_path),
    )
    assert not erro and b"# Ata" in rota.calls[0].request.content


def test_responder_sem_resposta_nem_pular() -> None:
    erro, _ = chamar("responder_pergunta", {"sessao": "S-1", "pergunta": "Q-001"})
    assert erro


@respx.mock
def test_gerar_modelo_aguarda_o_job() -> None:
    respx.post(f"{URL}/sessions/S-1/models").mock(
        return_value=httpx.Response(
            202, json={"job_id": "J-1", "modelo": "M-001", "status": "em_andamento"}
        )
    )
    respx.get(f"{URL}/sessions/S-1/jobs/J-1").mock(
        side_effect=[
            httpx.Response(200, json={"job_id": "J-1", "status": "em_andamento"}),
            httpx.Response(200, json={"job_id": "J-1", "status": "concluido"}),
        ]
    )
    respx.get(f"{URL}/sessions/S-1/models/M-001").mock(
        return_value=httpx.Response(200, json={"modelo": MODELO})
    )
    erro, dados = chamar("gerar_modelo", {"sessao": "S-1"})
    assert not erro
    assert dados["viavel"] and dados["rodadas_correcao"] == 1
    assert dados["relacoes"] == ["Portal —Serving→ Cliente"]
    assert dados["elementos"][1]["premissa"] is True
    assert dados["avisos"] == ["V3 COE-04: Ator sem processo"]


@respx.mock
def test_gerar_modelo_falhou() -> None:
    respx.post(f"{URL}/sessions/S-1/models").mock(
        return_value=httpx.Response(
            202, json={"job_id": "J-2", "modelo": "M-002", "status": "em_andamento"}
        )
    )
    respx.get(f"{URL}/sessions/S-1/jobs/J-2").mock(
        return_value=httpx.Response(200, json={"status": "falhou", "erro": "LLMError: tempo"})
    )
    erro, texto = chamar("gerar_modelo", {"sessao": "S-1"})
    assert erro and "LLMError" in texto


@respx.mock
def test_gerar_modelo_estoura_o_tempo() -> None:
    respx.post(f"{URL}/sessions/S-1/models").mock(
        return_value=httpx.Response(
            202, json={"job_id": "J-3", "modelo": "M-003", "status": "em_andamento"}
        )
    )
    respx.get(f"{URL}/sessions/S-1/jobs/J-3").mock(
        return_value=httpx.Response(200, json={"status": "em_andamento"})
    )
    erro, dados = chamar("gerar_modelo", {"sessao": "S-1"}, mcp_timeout_modelo_segundos=0.0)
    assert not erro and dados["status"] == "em_andamento"


@respx.mock
def test_ver_modelo_usa_a_versao_mais_recente() -> None:
    respx.get(f"{URL}/sessions/S-1/models").mock(
        return_value=httpx.Response(
            200,
            json={"modelos": [{"id": "M-001", "viavel": False}, {"id": "M-002", "viavel": True}]},
        )
    )
    rota = respx.get(f"{URL}/sessions/S-1/models/M-002").mock(
        return_value=httpx.Response(200, json={"modelo": {**MODELO, "id": "M-002"}})
    )
    erro, dados = chamar("ver_modelo", {"sessao": "S-1"})
    assert not erro and rota.called and dados["modelo"]["id"] == "M-002"


@respx.mock
def test_baixar_arquivo_conteudo_ou_pasta(tmp_path: Path) -> None:
    respx.get(f"{URL}/sessions/S-1/models/M-001/files/archimate").mock(
        return_value=httpx.Response(
            200, content=b"<archimate:model/>", headers={"content-type": "application/xml"}
        )
    )
    erro, dados = chamar(
        "baixar_arquivo", {"sessao": "S-1", "modelo": "M-001", "tipo": "archimate"}
    )
    assert not erro and dados["conteudo"] == "<archimate:model/>"
    erro, dados = chamar(
        "baixar_arquivo",
        {"sessao": "S-1", "modelo": "M-001", "tipo": "archimate"},
        mcp_pasta_saida=str(tmp_path),
    )
    assert not erro and dados["arquivo"] == "S-1-M-001.archimate"
    assert (tmp_path / "S-1-M-001.archimate").read_bytes() == b"<archimate:model/>"


def test_baixar_tipo_invalido() -> None:
    erro, _ = chamar("baixar_arquivo", {"sessao": "S-1", "modelo": "M-001", "tipo": "pdf"})
    assert erro


def test_health_http() -> None:
    app = criar_servidor(cfg()).streamable_http_app()
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
