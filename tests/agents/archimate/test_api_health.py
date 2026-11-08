from __future__ import annotations

from fastapi.testclient import TestClient

from archagent.agents.archimate.api import create_app
from archagent.core.config import Settings
from archagent.core.llm import LLM, ScriptedBackend


def cliente(backend: ScriptedBackend) -> TestClient:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    return TestClient(create_app(s, LLM(backend, s)))


def test_health_tem_request_id() -> None:
    r = cliente(ScriptedBackend()).get("/health", headers={"x-request-id": "r-teste"})
    assert r.status_code == 200
    assert r.json()["request_id"] == "r-teste"
    assert r.headers["x-request-id"] == "r-teste"


def test_health_llm_ok() -> None:
    b = ScriptedBackend()
    b.add("health", "ok")
    r = cliente(b).get("/health/llm")
    assert r.status_code == 200
    assert r.json()["resposta"] == "ok"


def test_health_llm_indisponivel_formato_de_erro() -> None:
    r = cliente(ScriptedBackend()).get("/health/llm")
    assert r.status_code == 503
    corpo = r.json()
    assert corpo["erro"]["codigo"] == "llm_indisponivel"
    assert corpo["request_id"].startswith("r-")


def test_rota_inexistente_no_formato_de_erro() -> None:
    r = cliente(ScriptedBackend()).get("/nada")
    assert r.status_code == 404
    assert "erro" in r.json()
