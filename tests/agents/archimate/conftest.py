from __future__ import annotations

from pathlib import Path

import pytest

from archagent.agents.archimate.model import Elemento, Modelo, Relacao
from archagent.agents.archimate.rules import Regras, carregar_regras

KB = Path(__file__).resolve().parents[3] / "kb"


@pytest.fixture(scope="session")
def regras() -> Regras:
    return carregar_regras(KB)


def modelo_portal() -> Modelo:
    """Modelo pequeno, montado à mão, com as três camadas."""
    ator = Elemento(id="id-ator", tipo="BusinessActor", nome="Cliente", origens=["B-001"])
    proc = Elemento(
        id="id-proc", tipo="BusinessProcess", nome="Registrar pedido", origens=["B-002"]
    )
    comp = Elemento(
        id="id-comp", tipo="ApplicationComponent", nome="API de Pedidos", origens=["B-003"]
    )
    serv = Elemento(
        id="id-serv", tipo="ApplicationService", nome="Serviço de pedidos", origens=["B-003"]
    )
    banco = Elemento(id="id-banco", tipo="SystemSoftware", nome="PostgreSQL", origens=["B-004"])
    dado = Elemento(id="id-dado", tipo="DataObject", nome="Pedido & <itens>", origens=["B-005"])
    rels = [
        Relacao(
            id="id-r1", tipo="Assignment", origem="id-ator", destino="id-proc", origens=["B-002"]
        ),
        Relacao(
            id="id-r2", tipo="Realization", origem="id-comp", destino="id-serv", origens=["B-003"]
        ),
        Relacao(id="id-r3", tipo="Serving", origem="id-serv", destino="id-proc", origens=["B-006"]),
        Relacao(
            id="id-r4", tipo="Serving", origem="id-banco", destino="id-comp", origens=["B-004"]
        ),
        Relacao(
            id="id-r5",
            tipo="Access",
            origem="id-comp",
            destino="id-dado",
            acesso="Write",
            origens=["B-005"],
        ),
    ]
    return Modelo(
        nome="Portal de pedidos", elementos=[ator, proc, comp, serv, banco, dado], relacoes=rels
    )
