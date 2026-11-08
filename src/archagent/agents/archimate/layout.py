"""Visões por viewpoint e layout automático em faixas por camada (spec §8.4).

Algoritmo (resolve a pendência P-02):

1. Cada viewpoint escolhe os seus elementos (`selecionar`).
2. Os elementos são ordenados seguindo as ligações: percurso em largura a partir
   dos elementos na ordem em que aparecem no modelo, para que elementos ligados
   fiquem perto.
3. Acima do limite de elementos por visão, a visão é dividida em partes.
4. Cada camada vira uma faixa (container), de cima para baixo: Negócio,
   Aplicação, Tecnologia. Dentro da faixa, os elementos vão em grade, com até
   N colunas, tamanho 120 × 55 e espaço de 40 entre eles.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable

from archagent.agents.archimate.model import Conexao, Elemento, Faixa, Modelo, No, Visao
from archagent.agents.archimate.rules import CAMADAS, Regras

LARGURA, ALTURA, ESPACO = 120, 55, 40
MARGEM, TOPO_FAIXA = 20, 30
ROTULOS = {"negocio": "Negócio", "aplicacao": "Aplicação", "tecnologia": "Tecnologia"}

NEGOCIO_BPC = {
    "BusinessProcess", "BusinessFunction", "BusinessInteraction", "BusinessEvent",
    "BusinessService", "BusinessObject", "BusinessActor", "BusinessRole",
    "BusinessCollaboration",
}  # fmt: skip
APLICACAO_AC = {
    "ApplicationComponent", "ApplicationInterface", "ApplicationService", "DataObject",
    "ApplicationCollaboration",
}  # fmt: skip


def _vizinhos(m: Modelo) -> dict[str, list[str]]:
    viz: dict[str, list[str]] = defaultdict(list)
    for r in m.relacoes:
        viz[r.origem].append(r.destino)
        viz[r.destino].append(r.origem)
    return viz


def ordenar(m: Modelo, ids: set[str]) -> list[str]:
    viz = _vizinhos(m)
    ordem: list[str] = []
    vistos: set[str] = set()
    for e in m.elementos:
        if e.id not in ids or e.id in vistos:
            continue
        fila = deque([e.id])
        vistos.add(e.id)
        while fila:
            atual = fila.popleft()
            ordem.append(atual)
            for v in viz.get(atual, []):
                if v in ids and v not in vistos:
                    vistos.add(v)
                    fila.append(v)
    return ordem


Seletor = Callable[[Modelo, Regras], set[str]]


def _layered(m: Modelo, _: Regras) -> set[str]:
    return {e.id for e in m.elementos}


def _bpc(m: Modelo, regras: Regras) -> set[str]:
    negocio = {e.id for e in m.elementos if e.tipo in NEGOCIO_BPC}
    if not negocio:
        return set()
    ids = m.por_id()
    componentes = {
        x
        for r in m.relacoes
        for x, outro in ((r.origem, r.destino), (r.destino, r.origem))
        if x in ids and ids[x].tipo == "ApplicationComponent" and outro in negocio
    }
    # Componentes que servem o negócio por meio de um serviço de aplicação também entram.
    servicos_negocio = {
        r.origem for r in m.relacoes
        if r.destino in negocio and r.origem in ids and regras.camada(ids[r.origem].tipo)
        == "aplicacao"
    }  # fmt: skip
    for r in m.relacoes:
        if (r.destino in servicos_negocio and r.origem in ids
                and ids[r.origem].tipo == "ApplicationComponent"):  # fmt: skip
            componentes.add(r.origem)
    return negocio | componentes


def _ac(m: Modelo, _: Regras) -> set[str]:
    return {e.id for e in m.elementos if e.tipo in APLICACAO_AC}


def _tu(m: Modelo, regras: Regras) -> set[str]:
    tecnologia = {e.id for e in m.elementos if regras.camada(e.tipo) == "tecnologia"}
    componentes = {e.id for e in m.elementos if e.tipo == "ApplicationComponent"}
    if not tecnologia or not componentes:
        return set()
    return tecnologia | componentes


VIEWPOINTS: list[tuple[str, str, Seletor]] = [
    ("Layered", "Visão geral em camadas", _layered),
    ("Business Process Cooperation", "Cooperação de processos de negócio", _bpc),
    ("Application Cooperation", "Cooperação de aplicações", _ac),
    ("Technology Usage", "Uso de tecnologia", _tu),
]


def desenhar(m: Modelo, regras: Regras, ids: list[str], nome: str, viewpoint: str) -> Visao:
    colunas = regras.limite("colunas_por_faixa", 6)
    por_camada: dict[str, list[Elemento]] = defaultdict(list)
    idx = m.por_id()
    for eid in ids:
        e = idx[eid]
        por_camada[regras.camada(e.tipo) or "aplicacao"].append(e)
    visao = Visao(nome=nome, viewpoint=viewpoint)
    largura_max = max(min(len(v), colunas) for v in por_camada.values()) if por_camada else 1
    largura_faixa = 2 * MARGEM + largura_max * LARGURA + (largura_max - 1) * ESPACO
    y = MARGEM
    for camada in CAMADAS:
        elems = por_camada.get(camada)
        if not elems:
            continue
        linhas = (len(elems) + colunas - 1) // colunas
        altura = TOPO_FAIXA + linhas * ALTURA + (linhas - 1) * ESPACO + MARGEM
        visao.faixas.append(Faixa(rotulo=ROTULOS[camada], camada=camada, x=MARGEM, y=y,
                                  w=largura_faixa, h=altura))  # fmt: skip
        for i, e in enumerate(elems):
            lin, col = divmod(i, colunas)
            visao.nos.append(No(
                elemento=e.id,
                x=2 * MARGEM + col * (LARGURA + ESPACO),
                y=y + TOPO_FAIXA + lin * (ALTURA + ESPACO),
            ))  # fmt: skip
        y += altura + ESPACO
    na_visao = set(ids)
    visao.conexoes = [Conexao(relacao=r.id) for r in m.relacoes
                      if r.origem in na_visao and r.destino in na_visao]  # fmt: skip
    return visao


def gerar_visoes(m: Modelo, regras: Regras) -> list[Visao]:
    """Gera as visões dos viewpoints que tiverem elementos (RF-MOD-07)."""
    limite = regras.limite("elementos_por_visao", 20)
    visoes: list[Visao] = []
    for viewpoint, nome, seletor in VIEWPOINTS:
        ids = ordenar(m, seletor(m, regras))
        if not ids:
            continue
        partes = [ids[i : i + limite] for i in range(0, len(ids), limite)]
        for n, parte in enumerate(partes, 1):
            rotulo = nome if len(partes) == 1 else f"{nome} ({n}/{len(partes)})"
            visoes.append(desenhar(m, regras, parte, rotulo, viewpoint))
    return visoes
