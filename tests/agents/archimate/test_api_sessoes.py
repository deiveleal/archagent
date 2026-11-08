"""N2: endpoints da spec §13 com LLM simulado: sucesso, entrada inválida, sessão
inexistente e request_id presente."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from archagent.agents.archimate.api import create_app
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.core.llm import LLM, ScriptedBackend

from .conftest import KB
from .test_api_health import ArchiFalso

INTERP = {
    "itens": [
        {
            "tipo": "ator",
            "nome": "Cliente",
            "local": "linha 1",
            "trecho": "O cliente",
            "confianca": "alta",
        },
        {
            "tipo": "sistema",
            "nome": "Portal Web",
            "local": "linha 1",
            "trecho": "Portal Web",
            "confianca": "alta",
        },
        {
            "tipo": "pendencia",
            "nome": "Onde o portal roda?",
            "local": "linha 1",
            "trecho": "Portal",
            "confianca": "baixa",
        },
    ]
}
PERG = {"perguntas": [{"item": "B-003", "pergunta": "Onde o Portal Web roda?", "impacto": "alto"}]}
RESP = {
    "itens": [
        {
            "tipo": "infraestrutura",
            "nome": "Cluster Kubernetes",
            "local": "linha 1",
            "trecho": "Kubernetes",
            "confianca": "alta",
            "substitui": "B-003",
        }
    ]
}


@pytest.fixture
def ctx(tmp_path: Path) -> tuple[TestClient, ScriptedBackend, ArchimateSettings]:
    s = ArchimateSettings(
        _env_file=None,
        kb_dir=KB,
        sessions_dir=tmp_path,  # type: ignore[call-arg]
        llm_max_tokens_per_session=1000,
    )
    b = ScriptedBackend()
    return TestClient(create_app(s, LLM(b, s), ArchiFalso())), b, s  # type: ignore[arg-type]


def criar(c: TestClient) -> str:
    r = c.post("/sessions", json={"titulo": "Portal"})
    assert r.status_code == 201
    sid: str = r.json()["sessao"]["id"]
    return sid


def test_fluxo_de_briefing_completo(
    ctx: tuple[TestClient, ScriptedBackend, ArchimateSettings],
) -> None:
    c, b, _ = ctx
    sid = criar(c)
    b.add("interpretar", INTERP)
    b.add("esclarecer", PERG)
    r = c.post(f"/sessions/{sid}/inputs", data={"texto": "O cliente usa o Portal Web."})
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["entrada"]["id"] == "E-001"
    assert corpo["resultado"]["novos"] == ["B-001", "B-002", "B-003"]
    assert corpo["perguntas"][0]["id"] == "Q-001"
    assert corpo["request_id"].startswith("r-")

    assert len(c.get(f"/sessions/{sid}/questions").json()["perguntas"]) == 1
    # resposta do arquiteto resolve a pendência
    b.respostas["interpretar"] = []
    b.add("interpretar", RESP)
    b.respostas["esclarecer"] = []
    b.add("esclarecer", {"perguntas": []})
    r = c.post(
        f"/sessions/{sid}/questions/Q-001/answer", json={"resposta": "Roda num cluster Kubernetes."}
    )
    assert r.status_code == 200, r.text
    assert r.json()["pergunta"]["status"] == "respondida"
    itens = {i["id"]: i for i in c.get(f"/sessions/{sid}/briefing").json()["itens"]}
    assert itens["B-003"]["status"] == "superado"
    assert itens["B-003"]["superado_por"] == "B-004"
    # responder de novo dá 409
    assert (
        c.post(f"/sessions/{sid}/questions/Q-001/answer", json={"pular": True}).status_code == 409
    )

    assert c.post(f"/sessions/{sid}/briefing/confirm").json()["status"] == "briefing_confirmado"
    detalhe = c.get(f"/sessions/{sid}").json()
    assert [e["id"] for e in detalhe["entradas"]] == ["E-001", "E-002"]
    assert c.get("/sessions").json()["sessoes"][0]["id"] == sid
    filtrado = c.get(f"/sessions/{sid}/briefing", params={"status": "ativo", "tipo": "ator"})
    assert [i["nome"] for i in filtrado.json()["itens"]] == ["Cliente"]


def test_upload_de_arquivo_e_invalido(
    ctx: tuple[TestClient, ScriptedBackend, ArchimateSettings],
) -> None:
    c, b, _ = ctx
    sid = criar(c)
    b.add("interpretar", {"itens": []})
    vtt = b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Ana>Oi\n"
    r = c.post(f"/sessions/{sid}/inputs", files={"arquivo": ("reuniao.vtt", vtt)})
    assert r.status_code == 201, r.text
    r = c.post(f"/sessions/{sid}/inputs", files={"arquivo": ("x.png", b"nao e png")})
    assert r.status_code == 400
    assert r.json()["erro"]["codigo"] == "entrada_invalida"
    assert c.post(f"/sessions/{sid}/inputs", data={}).status_code == 400


def test_sessao_inexistente(ctx: tuple[TestClient, ScriptedBackend, ArchimateSettings]) -> None:
    c, _, _ = ctx
    for metodo, caminho in [
        ("get", "/sessions/S-20990101-0001"),
        ("get", "/sessions/S-x/briefing"),
        ("get", "/sessions/S-x/questions"),
        ("get", "/sessions/S-x/usage"),
        ("post", "/sessions/S-x/briefing/confirm"),
    ]:
        r = getattr(c, metodo)(caminho)
        assert r.status_code == 404, caminho
        assert r.json()["erro"]["codigo"] == "sessao_inexistente"
        assert r.json()["request_id"]
    r = c.post("/sessions/S-x/inputs", data={"texto": "oi"})
    assert r.status_code == 404


def test_pergunta_inexistente(ctx: tuple[TestClient, ScriptedBackend, ArchimateSettings]) -> None:
    c, _, _ = ctx
    sid = criar(c)
    r = c.post(f"/sessions/{sid}/questions/Q-999/answer", json={"pular": True})
    assert r.status_code == 404


def test_limite_de_tokens(ctx: tuple[TestClient, ScriptedBackend, ArchimateSettings]) -> None:
    c, b, _ = ctx
    sid = criar(c)
    b.add("interpretar", {"itens": []})
    for _ in range(7):  # 150 tokens por chamada; limite 1000 → 1050 depois da 7ª
        c.post(f"/sessions/{sid}/inputs", data={"texto": "x"})
    u = c.get(f"/sessions/{sid}/usage").json()
    assert u["aviso"] is True
    r = c.post(f"/sessions/{sid}/inputs", data={"texto": "x"})
    assert r.status_code == 429
    assert r.json()["erro"]["codigo"] == "limite_tokens"
    assert c.get(f"/sessions/{sid}/usage").json()["bloqueado"] is True


def test_imagem_ilegivel_e_falha(
    ctx: tuple[TestClient, ScriptedBackend, ArchimateSettings],
) -> None:
    import io

    from PIL import Image

    c, b, _ = ctx
    sid = criar(c)
    b.add("interpretar", {"itens": [], "ilegivel": True})
    buf = io.BytesIO()
    Image.new("RGB", (20, 20)).save(buf, "PNG")
    r = c.post(f"/sessions/{sid}/inputs", files={"arquivo": ("q.png", buf.getvalue())})
    assert r.status_code == 400
    assert "Não consegui ler a imagem" in r.json()["erro"]["mensagem"]
    entradas = c.get(f"/sessions/{sid}").json()["entradas"]
    assert entradas[0]["status"] == "falhou"


def test_llm_fora_do_esquema_vira_502(
    ctx: tuple[TestClient, ScriptedBackend, ArchimateSettings],
) -> None:
    c, b, _ = ctx
    sid = criar(c)
    b.add("interpretar", "isto não é json")
    r = c.post(f"/sessions/{sid}/inputs", data={"texto": "x"})
    assert r.status_code == 502
