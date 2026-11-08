from __future__ import annotations

import json
import logging

import pytest

from archagent.core.logs import (
    JsonFormatter,
    log_event,
    new_request_id,
    redact,
    request_id_var,
    session_var,
)


def test_redact_remove_chaves() -> None:
    assert "sk-abc" not in redact("chave sk-abcdefghijkl123 aqui")
    assert "segredo123456" not in redact("Authorization: Bearer segredo123456")


def test_log_em_json_com_contexto(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("teste")
    token_r = request_id_var.set("r-1")
    token_s = session_var.set("S-1")
    try:
        with caplog.at_level(logging.INFO):
            log_event(logger, "llm.chamada", no="interpretar", tokens_entrada=10)
        linha = JsonFormatter("agent-archimate").format(caplog.records[0])
    finally:
        request_id_var.reset(token_r)
        session_var.reset(token_s)
    dados = json.loads(linha)
    assert dados["evento"] == "llm.chamada"
    assert dados["servico"] == "agent-archimate"
    assert dados["request_id"] == "r-1"
    assert dados["sessao"] == "S-1"
    assert dados["no"] == "interpretar"


def test_request_id() -> None:
    assert new_request_id().startswith("r-")
