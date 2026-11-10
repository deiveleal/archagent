"""Visões por viewpoint e layout automático em faixas por camada (spec §8.4).

Algoritmo (resolve a pendência P-02; refeito na P-13 para as visões ficarem legíveis):

1. Cada viewpoint escolhe os seus elementos (`selecionar`).
2. Os elementos são ordenados seguindo as ligações: percurso em largura a partir
   dos elementos na ordem em que aparecem no modelo, para que elementos ligados
   fiquem perto.
3. Acima do limite de elementos por visão, a visão é dividida em partes.
4. Cada camada vira uma faixa (container), de cima para baixo: Negócio,
   Aplicação, Tecnologia. Dentro da faixa, os elementos vão numa grade de até
   N colunas, com caixas de 150 × 60.
5. Busca local: troca elementos de célula dentro da mesma faixa (inclusive com
   células vazias) enquanto o custo cair. O custo soma o comprimento das linhas,
   uma penalidade alta para cada caixa que uma linha atravessa e uma menor para
   cada cruzamento de linhas. O resultado é determinístico.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable

from archagent.agents.archimate.model import (
    Conexao,
    Elemento,
    Faixa,
    Modelo,
    No,
    Relacao,
    Visao,
)
from archagent.agents.archimate.rules import CAMADAS, Regras

LARGURA, ALTURA = 150, 60
ESPACO_X, ESPACO_Y = 60, 70
PESO_ATRAVESSA, PESO_CRUZA, PESO_ROTULO = 6.0, 1.5, 6.0
PX_POR_LETRA, ROTULO_A = 6.5, 18  # tamanho aproximado do nome de uma relação
DESVIO_PARALELA = 28
MAX_PASSADAS = 12
MARGEM, TOPO_FAIXA = 20, 30
ROTULOS = {"negocio": "Negócio", "aplicacao": "Aplicação", "tecnologia": "Tecnologia"}

NEGOCIO_BPC = {
    "BusinessProcess",
    "BusinessFunction",
    "BusinessInteraction",
    "BusinessEvent",
    "BusinessService",
    "BusinessObject",
    "BusinessActor",
    "BusinessRole",
    "BusinessCollaboration",
}
APLICACAO_AC = {
    "ApplicationComponent",
    "ApplicationInterface",
    "ApplicationService",
    "DataObject",
    "ApplicationCollaboration",
}


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
        r.origem
        for r in m.relacoes
        if r.destino in negocio
        and r.origem in ids
        and regras.camada(ids[r.origem].tipo) == "aplicacao"
    }
    for r in m.relacoes:
        if (
            r.destino in servicos_negocio
            and r.origem in ids
            and ids[r.origem].tipo == "ApplicationComponent"
        ):
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


Celula = tuple[int, int]  # (linha global, coluna)
Retangulo = tuple[float, float, float, float]


def _cruzam(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]
) -> bool:
    def lado(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    d1, d2 = lado(c, d, a), lado(c, d, b)
    d3, d4 = lado(a, b, c), lado(a, b, d)
    return d1 * d2 < 0 and d3 * d4 < 0


def _atravessa(a: tuple[float, float], b: tuple[float, float], r: Retangulo) -> bool:
    """Se o segmento a–b passa pelo retângulo r (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = r
    # Recorte de Liang–Barsky.
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


class _Grade:
    """Posições dos elementos numa grade e o custo de legibilidade (passo 5)."""

    def __init__(self, ligacoes: list[tuple[str, str, str]], pos: dict[str, Celula]) -> None:
        # (origem, destino, nome); ligações repetidas entre o mesmo par contam uma vez.
        unicas: dict[frozenset[str], tuple[str, str, str]] = {}
        for a, b, nome in ligacoes:
            if a == b:
                continue
            k = frozenset((a, b))
            if k not in unicas or len(nome) > len(unicas[k][2]):
                unicas[k] = (a, b, nome)
        self.ligacoes = list(unicas.values())
        self.pos = pos

    def centro(self, eid: str) -> tuple[float, float]:
        lin, col = self.pos[eid]
        return (col * (LARGURA + ESPACO_X) + LARGURA / 2, lin * (ALTURA + ESPACO_Y) + ALTURA / 2)

    def caixa(self, eid: str) -> Retangulo:
        cx, cy = self.centro(eid)
        return (
            cx - LARGURA / 2 + 4,
            cy - ALTURA / 2 + 4,
            cx + LARGURA / 2 - 4,
            cy + ALTURA / 2 - 4,
        )

    def custo(self) -> float:
        centros = {e: self.centro(e) for e in self.pos}
        caixas = {e: self.caixa(e) for e in self.pos}
        passo = LARGURA + ESPACO_X
        total = 0.0
        segs = [(a, b, centros[a], centros[b]) for a, b, _ in self.ligacoes]
        # Nomes das relações ficam no meio da linha: não devem cair sobre caixas nem entre si.
        rotulos = [
            ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, len(nome) * PX_POR_LETRA)
            for (_, _, nome), (_, _, pa, pb) in zip(self.ligacoes, segs, strict=True)
            if nome
        ]
        for i, (mx, my, lg) in enumerate(rotulos):
            area = (mx - lg / 2, my - ROTULO_A / 2, mx + lg / 2, my + ROTULO_A / 2)
            for r in caixas.values():
                if area[0] < r[2] and r[0] < area[2] and area[1] < r[3] and r[1] < area[3]:
                    total += PESO_ROTULO
            for nx, ny, ng in rotulos[i + 1 :]:
                if abs(mx - nx) < (lg + ng) / 2 and abs(my - ny) < ROTULO_A:
                    total += PESO_ROTULO
        for i, (a, b, pa, pb) in enumerate(segs):
            total += ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5 / passo
            for e, r in caixas.items():
                if e not in (a, b) and _atravessa(pa, pb, r):
                    total += PESO_ATRAVESSA
            for c, d, pc, pd in segs[i + 1 :]:
                if {a, b} & {c, d}:
                    continue
                if _cruzam(pa, pb, pc, pd):
                    total += PESO_CRUZA
        return total

    def otimizar(self, celulas_por_faixa: list[list[Celula]]) -> None:
        melhor = self.custo()
        for _ in range(MAX_PASSADAS):
            melhorou = False
            for celulas in celulas_por_faixa:
                for i, ci in enumerate(celulas):
                    for cj in celulas[i + 1 :]:
                        ocupante = {c: e for e, c in self.pos.items()}
                        ei, ej = ocupante.get(ci), ocupante.get(cj)
                        if ei is None and ej is None:
                            continue
                        if ei:
                            self.pos[ei] = cj
                        if ej:
                            self.pos[ej] = ci
                        novo = self.custo()
                        if novo < melhor - 1e-9:
                            melhor, melhorou = novo, True
                        else:
                            if ei:
                                self.pos[ei] = ci
                            if ej:
                                self.pos[ej] = cj
            if not melhorou:
                break


def desenhar(m: Modelo, regras: Regras, ids: list[str], nome: str, viewpoint: str) -> Visao:
    colunas_max = regras.limite("colunas_por_faixa", 6)
    por_camada: dict[str, list[Elemento]] = defaultdict(list)
    idx = m.por_id()
    for eid in ids:
        e = idx[eid]
        por_camada[regras.camada(e.tipo) or "aplicacao"].append(e)
    camadas = [c for c in CAMADAS if por_camada.get(c)]
    colunas = min(colunas_max, max((len(por_camada[c]) for c in camadas), default=1))

    # Grade: cada faixa ocupa linhas próprias, com uma linha a mais para a busca
    # local ter espaço de manobra; as linhas que sobrarem vazias saem no fim.
    pos: dict[str, Celula] = {}
    celulas_por_faixa: list[list[Celula]] = []
    linha = 0
    for camada in camadas:
        elems = por_camada[camada]
        linhas = (len(elems) + colunas - 1) // colunas + 1
        celulas = [(linha + li, co) for li in range(linhas) for co in range(colunas)]
        for e, c in zip(elems, celulas, strict=False):
            pos[e.id] = c
        celulas_por_faixa.append(celulas)
        linha += linhas

    na_visao = set(ids)
    rels = [r for r in m.relacoes if r.origem in na_visao and r.destino in na_visao]
    grade = _Grade([(r.origem, r.destino, r.nome or "") for r in rels], pos)
    grade.otimizar(celulas_por_faixa)

    # Tira as linhas vazias e renumera.
    usadas = sorted({lin for lin, _ in grade.pos.values()})
    nova = {lin: i for i, lin in enumerate(usadas)}
    grade.pos = {e: (nova[lin], col) for e, (lin, col) in grade.pos.items()}
    linhas_por_camada: dict[str, tuple[int, int]] = {}
    for camada in camadas:
        lins = [grade.pos[e.id][0] for e in por_camada[camada]]
        linhas_por_camada[camada] = (min(lins), max(lins) - min(lins) + 1)

    # Coordenadas: as faixas ficam separadas por um espaço extra.
    visao = Visao(nome=nome, viewpoint=viewpoint)
    largura_faixa = 2 * MARGEM + colunas * LARGURA + (colunas - 1) * ESPACO_X
    y = MARGEM
    for camada in camadas:
        primeira, linhas = linhas_por_camada[camada]
        altura = TOPO_FAIXA + linhas * ALTURA + (linhas - 1) * ESPACO_Y + MARGEM
        visao.faixas.append(
            Faixa(rotulo=ROTULOS[camada], camada=camada, x=MARGEM, y=y, w=largura_faixa, h=altura)
        )
        for e in por_camada[camada]:
            lin, col = grade.pos[e.id]
            visao.nos.append(
                No(
                    elemento=e.id,
                    x=2 * MARGEM + col * (LARGURA + ESPACO_X),
                    y=y + TOPO_FAIXA + (lin - primeira) * (ALTURA + ESPACO_Y),
                    w=LARGURA,
                    h=ALTURA,
                )
            )
        y += altura + ESPACO_Y
    visao.conexoes = _conexoes(rels, visao.nos)
    return visao


def _conexoes(rels: list[Relacao], nos: list[No]) -> list[Conexao]:
    """Liga as relações; a partir da 2ª entre o mesmo par, a linha ganha uma dobra ao lado."""
    centro = {n.elemento: (n.x + n.w / 2, n.y + n.h / 2) for n in nos}
    vistas: dict[frozenset[str], int] = defaultdict(int)
    conexoes: list[Conexao] = []
    for r in rels:
        k = frozenset((r.origem, r.destino))
        n = vistas[k]
        vistas[k] += 1
        dobras: list[tuple[int, int]] = []
        if n and r.origem != r.destino:
            (ax, ay), (bx, by) = centro[r.origem], centro[r.destino]
            dx, dy = bx - ax, by - ay
            norma = (dx * dx + dy * dy) ** 0.5 or 1.0
            lado = DESVIO_PARALELA * ((n + 1) // 2) * (1 if n % 2 else -1)
            dobras.append(
                (round((ax + bx) / 2 - dy / norma * lado), round((ay + by) / 2 + dx / norma * lado))
            )
        conexoes.append(Conexao(relacao=r.id, dobras=dobras))
    return conexoes


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
