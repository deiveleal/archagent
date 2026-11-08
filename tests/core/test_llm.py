from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from archagent.core.config import Settings
from archagent.core.llm import (
    LLM,
    LLMError,
    MissingFixture,
    ReplayBackend,
    ScriptedBackend,
    TokenBudgetExceeded,
    extract_json,
    fixture_key,
    image_message,
)


class Resposta(BaseModel):
    nome: str
    total: int


def settings(**kw: object) -> Settings:
    return Settings(_env_file=None, **kw)  # type: ignore[call-arg]


def test_structured_valida_esquema() -> None:
    b = ScriptedBackend()
    b.add("no1", {"nome": "API", "total": 2})
    r = LLM(b, settings()).structured([{"role": "user", "content": "x"}], Resposta, no="no1")
    assert r == Resposta(nome="API", total=2)


def test_structured_repara_resposta_fora_do_esquema() -> None:
    b = ScriptedBackend()
    b.add("no1", '{"nome": "API"}')
    b.add("no1", '```json\n{"nome": "API", "total": 3}\n```')
    usos: list[int] = []
    r = LLM(b, settings()).structured(
        [{"role": "user", "content": "x"}],
        Resposta,
        no="no1",
        on_usage=lambda _no, res: usos.append(res.tokens),
    )
    assert r.total == 3
    assert len(b.chamadas) == 2
    assert "não segue o esquema" in b.chamadas[1][1][-1]["content"]
    assert usos == [150, 150]


def test_structured_desiste_depois_do_reparo() -> None:
    b = ScriptedBackend()
    b.add("no1", "sem json")
    with pytest.raises(LLMError):
        LLM(b, settings()).structured([], Resposta, no="no1")


def test_orcamento_de_tokens_bloqueia() -> None:
    b = ScriptedBackend()
    b.add("no1", "oi")
    llm = LLM(b, settings(llm_max_tokens_per_session=1000))
    assert llm.chat([], no="no1", tokens_usados=999).texto == "oi"
    with pytest.raises(TokenBudgetExceeded):
        llm.chat([], no="no1", tokens_usados=1000)


def test_replay_sem_gravacao_falha(tmp_path: Path) -> None:
    with pytest.raises(MissingFixture):
        ReplayBackend(tmp_path).chat([], modelo="m", json_mode=False, no="x")


def test_replay_le_e_grava(tmp_path: Path) -> None:
    real = ScriptedBackend()
    real.add("x", "resposta")
    gravador = ReplayBackend(tmp_path, real, gravar=True)
    msgs = [{"role": "user", "content": "olá"}]
    assert gravador.chat(msgs, modelo="m", json_mode=False, no="x").texto == "resposta"
    arquivo = tmp_path / f"{fixture_key('x', 'm', msgs, False)}.json"
    assert json.loads(arquivo.read_text())["texto"] == "resposta"
    leitor = ReplayBackend(tmp_path)
    assert leitor.chat(msgs, modelo="m", json_mode=False, no="x").texto == "resposta"


def test_extract_json() -> None:
    assert extract_json('texto {"a": 1} fim') == '{"a": 1}'
    with pytest.raises(ValueError, match="Nenhum"):
        extract_json("nada")


def test_image_message() -> None:
    m = image_message("descreva", "QUJD", "image/jpeg")
    assert m["content"][1]["image_url"]["url"] == "data:image/jpeg;base64,QUJD"
