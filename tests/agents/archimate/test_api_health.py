from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from archagent.agents.archimate.api import create_app
from archagent.agents.archimate.archi import ArchiIndisponivel
from archagent.agents.archimate.rules import RegrasInvalidas
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.core.llm import LLM, ScriptedBackend

from .conftest import KB


class ArchiFalso:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok

    def health(self) -> dict[str, object]:
        if not self.ok:
            raise ArchiIndisponivel("fora")
        return {"status": "ok", "archi_versao": "5.10.0"}

    def converter(self, exchange: bytes) -> tuple[bytes | None, list[object]]:
        if not self.ok:
            raise ArchiIndisponivel("fora")
        return b"<archimate:model/>", []


def settings(tmp: Path, **kw: object) -> ArchimateSettings:
    return ArchimateSettings(_env_file=None, kb_dir=KB, sessions_dir=tmp, **kw)  # type: ignore[call-arg]


@pytest.fixture(autouse=True)
def _tmp(tmp_path: Path) -> None:
    global TMP
    TMP = tmp_path


TMP = Path()


def cliente(backend: ScriptedBackend, archi: ArchiFalso | None = None) -> TestClient:
    s = settings(TMP)
    return TestClient(create_app(s, LLM(backend, s), archi or ArchiFalso()))  # type: ignore[arg-type]


def test_health_tem_request_id_regras_e_archi() -> None:
    r = cliente(ScriptedBackend()).get("/health", headers={"x-request-id": "r-teste"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["request_id"] == "r-teste"
    assert r.headers["x-request-id"] == "r-teste"
    assert corpo["regras"]["elementos"] == 35
    assert corpo["tool_archi"]["archi_versao"] == "5.10.0"


def test_health_com_archi_fora() -> None:
    r = cliente(ScriptedBackend(), ArchiFalso(ok=False)).get("/health")
    assert r.json()["tool_archi"]["status"] == "indisponivel"


def test_sem_regras_nao_sobe(tmp_path: Path) -> None:
    s = ArchimateSettings(_env_file=None, kb_dir=tmp_path, sessions_dir=tmp_path)  # type: ignore[call-arg]
    with pytest.raises(RegrasInvalidas):
        create_app(s, LLM(ScriptedBackend(), s))


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
