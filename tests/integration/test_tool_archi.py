"""N2: conversão real pelo container tool-archi (V5)."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

URL = os.environ.get("TOOL_ARCHI_URL", "http://tool-archi:8000")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exchange"


def test_health() -> None:
    r = httpx.get(f"{URL}/health", timeout=10)
    assert r.json()["status"] == "ok"


def test_converte_modelo_valido() -> None:
    r = httpx.post(f"{URL}/convert", content=(FIXTURES / "minimo.xml").read_bytes(), timeout=200)
    assert r.status_code == 200, r.text
    assert b"archimate:model" in r.content
    assert b'name="API de Pedidos"' in r.content


def test_erro_do_archi_legivel() -> None:
    ruim = (FIXTURES / "minimo.xml").read_text().replace('target="id-b"', 'target="id-zzz"')
    r = httpx.post(f"{URL}/convert", content=ruim.encode(), timeout=200)
    assert r.status_code == 422
    erro = r.json()["erro"]
    assert erro["codigo"] == "archi_falhou"
    assert "id-zzz" in erro["log"]
    assert "\tat " not in erro["log"]
