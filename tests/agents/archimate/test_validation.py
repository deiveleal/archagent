from __future__ import annotations

from dataclasses import dataclass

import pytest

from archagent.agents.archimate.model import Elemento, Modelo, No, Relacao, Visao
from archagent.agents.archimate.rules import Regras
from archagent.agents.archimate.validation import (
    validar_modelo,
    validar_v2,
    validar_v3,
    validar_v4,
)

from .conftest import modelo_portal


def regras_de(achados: list) -> set[str]:  # type: ignore[type-arg]
    return {a.regra for a in achados}


def test_modelo_portal_sem_achados(regras: Regras) -> None:
    assert validar_modelo(modelo_portal(), regras) == []


# ----------------------------------------------------------------- V2


def test_v2_tipo_inexistente(regras: Regras) -> None:
    m = modelo_portal()
    m.elementos[0].tipo = "BusinessActorX"
    achados = validar_v2(m, regras)
    assert "TIPO-ELEMENTO" in regras_de(achados)


def test_v2_tipo_fora_do_mvp(regras: Regras) -> None:
    m = modelo_portal()
    m.elementos[0].tipo = "Goal"
    assert "TIPO-ELEMENTO" in regras_de(validar_v2(m, regras))


def test_v2_relacao_permitida(regras: Regras) -> None:
    assert validar_v2(modelo_portal(), regras) == []


def test_v2_relacao_proibida(regras: Regras) -> None:
    m = modelo_portal()
    # DataObject não serve ApplicationComponent
    m.relacoes.append(Relacao(tipo="Serving", origem="id-dado", destino="id-comp"))
    achados = validar_v2(m, regras)
    assert [a.regra for a in achados] == ["REL-PERMITIDA"]
    assert "Permitidas neste sentido: Association" in achados[0].mensagem


def test_v2_direcao_invertida(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes[0] = Relacao(id="id-r1", tipo="Assignment", origem="id-proc", destino="id-ator")
    achados = validar_v2(m, regras)
    assert achados and "invertida" in achados[0].mensagem


def test_v2_tipo_de_relacao_inexistente(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes[0].tipo = "UsedBy"
    assert "TIPO-RELACAO" in regras_de(validar_v2(m, regras))


def test_v2_acesso_so_em_access(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes[1].acesso = "Read"
    assert "ACESSO-SO-EM-ACCESS" in regras_de(validar_v2(m, regras))


# ----------------------------------------------------------------- V3


def test_coe01_elemento_solto(regras: Regras) -> None:
    m = modelo_portal()
    m.elementos.append(Elemento(tipo="Node", nome="Servidor", origens=["B-009"]))
    assert "COE-01" in regras_de(validar_v3(m, regras))


def test_coe02_relacao_quebrada(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes.append(Relacao(tipo="Serving", origem="id-banco", destino="id-nada"))
    assert "COE-02" in regras_de(validar_v3(m, regras))


def test_coe03_nome_repetido(regras: Regras) -> None:
    m = modelo_portal()
    m.elementos.append(Elemento(tipo="BusinessActor", nome="cliente "))
    m.relacoes.append(Relacao(tipo="Assignment", origem=m.elementos[-1].id, destino="id-proc"))
    assert "COE-03" in regras_de(validar_v3(m, regras))


def test_coe04_servico_sem_realizacao(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes = [r for r in m.relacoes if r.id != "id-r2"]
    m.relacoes.append(Relacao(tipo="Serving", origem="id-serv", destino="id-comp"))
    assert "COE-04" in regras_de(validar_v3(m, regras))


def test_coe05_componente_sem_tecnologia(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes = [r for r in m.relacoes if r.id != "id-r4"]
    m.relacoes.append(Relacao(tipo="Association", origem="id-banco", destino="id-dado"))
    assert "COE-05" in regras_de(validar_v3(m, regras))


def test_coe06_processo_sem_responsavel(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes[0] = Relacao(id="id-r1", tipo="Association", origem="id-ator", destino="id-proc")
    assert "COE-06" in regras_de(validar_v3(m, regras))


def test_coe07_camadas_negocio_aplicacao(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes = [r for r in m.relacoes if r.id != "id-r3"]
    m.relacoes.append(Relacao(tipo="Serving", origem="id-banco", destino="id-serv"))
    assert "COE-07" in regras_de(validar_v3(m, regras))


def test_coe08_camadas_aplicacao_tecnologia(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes = [r for r in m.relacoes if r.id != "id-r4"]
    m.relacoes.append(Relacao(tipo="Association", origem="id-banco", destino="id-ator"))
    assert "COE-08" in regras_de(validar_v3(m, regras))


def test_coe09_visao_grande(regras: Regras) -> None:
    m = modelo_portal()
    m.visoes = [
        Visao(
            nome="v", viewpoint="Layered", nos=[No(elemento="id-ator", x=0, y=i) for i in range(21)]
        )
    ]
    assert "COE-09" in regras_de(validar_v3(m, regras))


@pytest.mark.parametrize(
    ("nome", "falha"), [("Registrar pedido", False), ("Pedido", True), ("Emitir nota", False)]
)
def test_coe10_processo_no_infinitivo(regras: Regras, nome: str, falha: bool) -> None:
    m = modelo_portal()
    m.elementos[1].nome = nome
    assert ("COE-10" in regras_de(validar_v3(m, regras))) is falha


def test_coe10_nome_longo(regras: Regras) -> None:
    m = modelo_portal()
    m.elementos[0].nome = "x" * 80
    assert "COE-10" in regras_de(validar_v3(m, regras))


def test_severidades(regras: Regras) -> None:
    m = modelo_portal()
    m.elementos.append(Elemento(tipo="Node", nome="Solto", origens=["B-1"]))
    m.relacoes[0] = Relacao(id="id-r1", tipo="Association", origem="id-ator", destino="id-proc")
    sev = {a.regra: a.severidade for a in validar_v3(m, regras)}
    assert sev["COE-01"] == "erro"
    assert sev["COE-06"] == "aviso"


# ----------------------------------------------------------------- V4


@dataclass
class Item:
    id: str
    tipo: str
    nome: str
    status: str = "ativo"


def test_v4_item_sem_elemento() -> None:
    m = modelo_portal()
    itens = [Item("B-001", "ator", "Cliente"), Item("B-099", "sistema", "ERP")]
    achados = validar_v4(m, itens)
    assert [a.elemento for a in achados if a.regra == "ITEM-SEM-ELEMENTO"] == ["B-099"]


def test_v4_ignora_superados_e_tipos_nao_cobertos() -> None:
    itens = [
        Item("B-098", "sistema", "ERP", status="superado"),
        Item("B-097", "requisito", "Rápido"),
    ]
    achados = validar_v4(modelo_portal(), itens)
    assert not [a for a in achados if a.regra == "ITEM-SEM-ELEMENTO"]


def test_v4_elemento_sem_origem_e_premissa() -> None:
    m = Modelo(
        elementos=[Elemento(tipo="Node", nome="A"), Elemento(tipo="Node", nome="B", premissa=True)]
    )
    achados = validar_v4(m, [])
    assert [a.regra for a in achados] == ["ELEMENTO-SEM-ORIGEM"]


def test_v4_origem_inexistente() -> None:
    m = Modelo(elementos=[Elemento(tipo="Node", nome="A", origens=["B-500"])])
    achados = validar_v4(m, [Item("B-001", "requisito", "x")])
    assert "ORIGEM-INEXISTENTE" in regras_de(achados)
