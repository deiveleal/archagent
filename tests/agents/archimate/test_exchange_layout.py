from __future__ import annotations

import json
from pathlib import Path

import pytest
from lxml import etree

from archagent.agents.archimate.exchange import NS, exportar, parse_seguro, validar_v1
from archagent.agents.archimate.layout import _atravessa, gerar_visoes
from archagent.agents.archimate.model import Elemento, Modelo, Relacao, Visao
from archagent.agents.archimate.rules import (
    Regras,
    RegrasInvalidas,
    carregar_regras,
    extrair_relacoes,
)

from .conftest import KB, modelo_portal


def _com_visoes(m: Modelo, regras: Regras) -> Modelo:
    m.visoes = gerar_visoes(m, regras)
    return m


# ----------------------------------------------------------------- regras


def test_regras_cobrem_os_35_elementos(regras: Regras) -> None:
    assert len(regras.elementos) == 35
    assert regras.permitida("Realization", "ApplicationComponent", "ApplicationService")
    assert not regras.permitida("Serving", "DataObject", "ApplicationComponent")


def test_relacoes_json_bate_com_a_fonte_do_archi() -> None:
    pasta = KB / "archimate" / "regras"
    gravado = json.loads((pasta / "relacoes.json").read_text())
    extraido = extrair_relacoes(pasta / "fonte" / "relationships.xml", gravado["fonte"])
    assert extraido == gravado


def test_regras_ausentes_impedem_subida(tmp_path: Path) -> None:
    with pytest.raises(RegrasInvalidas):
        carregar_regras(tmp_path)


# ----------------------------------------------------------------- layout


def test_layout_viewpoints(regras: Regras) -> None:
    visoes = gerar_visoes(modelo_portal(), regras)
    assert [v.viewpoint for v in visoes] == [
        "Layered", "Business Process Cooperation", "Application Cooperation", "Technology Usage",
    ]  # fmt: skip
    bpc = visoes[1]
    # componente que serve o negócio por meio do serviço entra na BPC
    assert "id-comp" in {n.elemento for n in bpc.nos}


def test_layout_so_negocio_gera_layered_e_bpc(regras: Regras) -> None:
    m = Modelo(
        elementos=[
            Elemento(id="id-a", tipo="BusinessActor", nome="A"),
            Elemento(id="id-p", tipo="BusinessProcess", nome="Fazer"),
        ],
        relacoes=[Relacao(tipo="Assignment", origem="id-a", destino="id-p")],
    )
    assert [v.viewpoint for v in gerar_visoes(m, regras)] == [
        "Layered",
        "Business Process Cooperation",
    ]


def test_layout_sem_sobreposicao_e_faixas_em_ordem(regras: Regras) -> None:
    v = gerar_visoes(modelo_portal(), regras)[0]
    caixas = [(n.x, n.y, n.x + n.w, n.y + n.h) for n in v.nos]
    for i, a in enumerate(caixas):
        for b in caixas[i + 1 :]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
    assert [f.camada for f in v.faixas] == ["negocio", "aplicacao", "tecnologia"]
    ys = [f.y for f in v.faixas]
    assert ys == sorted(ys)
    for n in v.nos:
        assert any(f.x <= n.x and n.x + n.w <= f.x + f.w and f.y <= n.y and
                   n.y + n.h <= f.y + f.h for f in v.faixas)  # fmt: skip


def test_layout_divide_acima_do_limite(regras: Regras) -> None:
    elems = [Elemento(id=f"id-{i}", tipo="Node", nome=f"N{i}") for i in range(45)]
    rels = [Relacao(tipo="Association", origem=f"id-{i}", destino=f"id-{i + 1}") for i in range(44)]
    visoes = gerar_visoes(Modelo(elementos=elems, relacoes=rels), regras)
    layered = [v for v in visoes if v.viewpoint == "Layered"]
    assert [len(v.nos) for v in layered] == [20, 20, 5]
    assert layered[0].nome.endswith("(1/3)")


def _linhas_atravessam_caixas(m: Modelo, v: Visao) -> list[str]:
    centro = {n.elemento: (n.x + n.w / 2, n.y + n.h / 2) for n in v.nos}
    caixa = {n.elemento: (n.x + 4, n.y + 4, n.x + n.w - 4, n.y + n.h - 4) for n in v.nos}
    rels = {r.id: r for r in m.relacoes}
    ruins = []
    for c in v.conexoes:
        r = rels[c.relacao]
        for e, cx in caixa.items():
            if e not in (r.origem, r.destino) and _atravessa(
                centro[r.origem], centro[r.destino], cx
            ):
                ruins.append(f"{r.origem}->{r.destino} atravessa {e}")
    return ruins


def test_layout_linha_nao_atravessa_caixa(regras: Regras) -> None:
    # Três componentes ligados ao mesmo: numa só linha da grade, uma linha passaria por dentro.
    comps = ["api", "portal", "registro", "backoffice"]
    m = Modelo(
        elementos=[Elemento(id=f"id-{c}", tipo="ApplicationComponent", nome=c) for c in comps],
        relacoes=[
            Relacao(tipo="Serving", origem="id-api", destino="id-portal"),
            Relacao(tipo="Serving", origem="id-api", destino="id-registro"),
            Relacao(tipo="Serving", origem="id-api", destino="id-backoffice"),
            Relacao(tipo="Serving", origem="id-registro", destino="id-backoffice"),
        ],
    )
    for v in gerar_visoes(m, regras):
        assert _linhas_atravessam_caixas(m, v) == []
    for v in gerar_visoes(modelo_portal(), regras):
        assert _linhas_atravessam_caixas(modelo_portal(), v) == []


def test_layout_deterministico(regras: Regras) -> None:
    def posicoes() -> list[tuple[str, int, int]]:
        return [
            (n.elemento, n.x, n.y) for v in gerar_visoes(modelo_portal(), regras) for n in v.nos
        ]

    assert posicoes() == posicoes()


def test_relacoes_paralelas_ganham_dobra_e_exportam(regras: Regras) -> None:
    m = Modelo(
        elementos=[
            Elemento(id="id-a", tipo="ApplicationComponent", nome="A"),
            Elemento(id="id-b", tipo="ApplicationComponent", nome="B"),
        ],
        relacoes=[
            Relacao(id="id-r1", tipo="Serving", origem="id-a", destino="id-b"),
            Relacao(id="id-r2", tipo="Flow", origem="id-b", destino="id-a", nome="Dados"),
        ],
    )
    m.visoes = gerar_visoes(m, regras)
    dobras = {c.relacao: c.dobras for c in m.visoes[0].conexoes}
    assert dobras["id-r1"] == [] and len(dobras["id-r2"]) == 1
    xml = exportar(m)
    assert validar_v1(xml, regras.xsd_dir) == []
    assert len(parse_seguro(xml).findall(f".//{{{NS}}}bendpoint")) == len(m.visoes)


# ----------------------------------------------------------------- exportação (V1)


def test_exportacao_minima_valida(regras: Regras) -> None:
    m = Modelo(elementos=[Elemento(id="id-a", tipo="Node", nome="A", origens=["B-1"])])
    assert validar_v1(exportar(m), regras.xsd_dir) == []


def test_exportacao_completa_valida_e_com_propriedades(regras: Regras) -> None:
    m = _com_visoes(modelo_portal(), regras)
    m.elementos[0].premissa = True
    m.elementos[0].motivo_premissa = "Ator suposto"
    xml = exportar(m)
    assert validar_v1(xml, regras.xsd_dir) == []
    raiz = parse_seguro(xml)
    ns = {"a": NS}
    assert len(raiz.findall(".//a:views/a:diagrams/a:view", ns)) == 4
    props = raiz.findall(".//a:element[@identifier='id-ator']/a:properties/a:property", ns)
    assert [p.find("a:value", ns).text for p in props] == ["B-001", "sim"]  # type: ignore[union-attr]
    assert raiz.find(".//a:relationship[@identifier='id-r5']", ns).get("accessType") == "Write"  # type: ignore[union-attr]


def test_caracteres_especiais(regras: Regras) -> None:
    m = _com_visoes(modelo_portal(), regras)
    xml = exportar(m)
    assert b"Pedido &amp; &lt;itens&gt;" in xml
    assert validar_v1(xml, regras.xsd_dir) == []


def test_v1_reprova_xml_invalido(regras: Regras) -> None:
    m = modelo_portal()
    m.relacoes[0].destino = "id-nada"
    achados = validar_v1(exportar(m), regras.xsd_dir)
    assert achados and achados[0].criterio == "V1"


def test_v1_reprova_xml_quebrado(regras: Regras) -> None:
    assert validar_v1(b"<model", regras.xsd_dir)[0].regra == "XML"


def test_parse_seguro_recusa_entidade_externa(tmp_path: Path) -> None:
    segredo = tmp_path / "segredo.txt"
    segredo.write_text("CONFIDENCIAL")
    xml = (f'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file://{segredo}">]>'
           "<r>&x;</r>").encode()  # fmt: skip
    try:
        el = parse_seguro(xml)
    except etree.XMLSyntaxError:
        return
    assert "CONFIDENCIAL" not in (etree.tostring(el).decode())
