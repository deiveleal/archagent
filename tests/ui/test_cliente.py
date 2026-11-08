from __future__ import annotations

import httpx
import pytest
import respx

from archagent.ui.cliente import AgenteCliente, ErroApi

URL = "http://agente:8000"


@respx.mock
def test_erro_da_api_vira_erroapi() -> None:
    respx.get(f"{URL}/sessions/S-1").mock(
        return_value=httpx.Response(
            404, json={"erro": {"codigo": "sessao_inexistente", "mensagem": "Sessão S-1 não"}}
        )
    )
    with pytest.raises(ErroApi) as e:
        AgenteCliente(URL).sessao("S-1")
    assert e.value.status == 404 and e.value.codigo == "sessao_inexistente"


@respx.mock
def test_sem_conexao() -> None:
    respx.get(f"{URL}/health").mock(side_effect=httpx.ConnectError("x"))
    with pytest.raises(ErroApi) as e:
        AgenteCliente(URL).saude()
    assert e.value.codigo == "sem_conexao"


@respx.mock
def test_mensagem_cai_para_entrada_quando_nao_ha_conversa() -> None:
    respx.post(f"{URL}/sessions/S-1/messages").mock(
        return_value=httpx.Response(404, json={"erro": {"codigo": "http", "mensagem": "Not Found"}})
    )
    rota = respx.post(f"{URL}/sessions/S-1/inputs").mock(
        return_value=httpx.Response(201, json={"entrada": {"id": "E-001"}})
    )
    r = AgenteCliente(URL).enviar_mensagem("S-1", "olá")
    assert r["entrada"]["id"] == "E-001"
    assert b"texto=ol" in rota.calls[0].request.content


@respx.mock
def test_mensagem_usa_conversa_quando_existe() -> None:
    respx.post(f"{URL}/sessions/S-1/messages").mock(
        return_value=httpx.Response(200, json={"resposta": "oi", "classe": "pergunta"})
    )
    assert AgenteCliente(URL).enviar_mensagem("S-1", "?")["resposta"] == "oi"


@respx.mock
def test_eventos_sse_ate_o_fim() -> None:
    corpo = (
        'id: 0\ndata: {"etapa": "modelar", "mensagem": "a"}\n\n'
        'id: 1\ndata: {"etapa": "relatorio", "mensagem": "b"}\n\n'
        "event: fim\ndata: {}\n\n"
    )
    respx.get(f"{URL}/sessions/S-1/events").mock(
        return_value=httpx.Response(200, text=corpo, headers={"content-type": "text/event-stream"})
    )
    assert [e["etapa"] for e in AgenteCliente(URL).eventos("S-1")] == ["modelar", "relatorio"]


@respx.mock
def test_download_binario_e_json() -> None:
    respx.get(f"{URL}/sessions/S-1/models/M-001/files/relatorio").mock(
        return_value=httpx.Response(200, content=b"# R", headers={"content-type": "text/markdown"})
    )
    respx.get(f"{URL}/sessions").mock(return_value=httpx.Response(200, json={"sessoes": []}))
    c = AgenteCliente(URL)
    assert c.arquivo("S-1", "M-001", "relatorio") == b"# R"
    assert c.sessoes() == []
