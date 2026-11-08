"""N2: modelos dos exemplos ouro exportados e convertidos pelo tool-archi real (V5)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from archagent.agents.archimate.archi import ArchiClient
from archagent.agents.archimate.exchange import exportar
from archagent.agents.archimate.kb_tools import carregar_exemplo
from archagent.agents.archimate.layout import gerar_visoes
from archagent.agents.archimate.rules import Regras

from .conftest import KB

pytestmark = pytest.mark.integration

URL = os.environ.get("TOOL_ARCHI_URL", "http://tool-archi:8000")
EXEMPLOS = sorted(p for p in (KB / "archimate" / "exemplos").iterdir() if p.is_dir())


@pytest.mark.parametrize("pasta", EXEMPLOS, ids=lambda p: p.name)
def test_exemplo_ouro_abre_no_archi(pasta: Path, regras: Regras) -> None:
    _, modelo = carregar_exemplo(pasta)
    modelo.visoes = gerar_visoes(modelo, regras)
    arquivo, achados = ArchiClient(URL).converter(exportar(modelo))
    assert achados == []
    assert arquivo and b"archimate:model" in arquivo
