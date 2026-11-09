"""Validadores V2 (ArchiMate), V3 (coerência) e V4 (cobertura) — spec §8."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Protocol

from archagent.agents.archimate.model import Achado, Modelo, Severidade
from archagent.agents.archimate.rules import TIPOS_RELACAO, Regras

# Tipos de item do briefing que precisam aparecer no modelo (V4).
TIPOS_COBERTOS = frozenset(
    {"ator", "processo", "servico", "sistema", "interface", "dado", "infraestrutura", "ligacao"}
)


class ItemRef(Protocol):
    """O mínimo de um item do briefing que o V4 precisa."""

    @property
    def id(self) -> str: ...
    @property
    def tipo(self) -> str: ...
    @property
    def status(self) -> str: ...
    @property
    def nome(self) -> str: ...


def _rotulo(m: Modelo, eid: str) -> str:
    e = m.elemento(eid)
    return f"{e.tipo} '{e.nome}'" if e else f"'{eid}'"


# ---------------------------------------------------------------- V2


def validar_v2(m: Modelo, regras: Regras) -> list[Achado]:
    achados: list[Achado] = []
    for e in m.elementos:
        if e.tipo not in regras.elementos:
            achados.append(
                Achado(
                    criterio="V2",
                    regra="TIPO-ELEMENTO",
                    severidade="erro",
                    elemento=e.id,
                    mensagem=f"Tipo de elemento '{e.tipo}' de '{e.nome}' não existe no "
                    "ArchiMate 3.2 ou está fora do escopo do MVP (Negócio, Aplicação, "
                    "Tecnologia).",
                )
            )
    ids = m.por_id()
    for r in m.relacoes:
        if r.tipo not in TIPOS_RELACAO:
            achados.append(
                Achado(
                    criterio="V2",
                    regra="TIPO-RELACAO",
                    severidade="erro",
                    elemento=r.id,
                    mensagem=f"Tipo de relação '{r.tipo}' não existe no ArchiMate 3.2.",
                )
            )
            continue
        o, d = ids.get(r.origem), ids.get(r.destino)
        if not o or not d or o.tipo not in regras.elementos or d.tipo not in regras.elementos:
            continue  # COE-02 ou TIPO-ELEMENTO já acusam
        if regras.permitida(r.tipo, o.tipo, d.tipo):
            if r.acesso and r.tipo != "Access":
                achados.append(
                    Achado(
                        criterio="V2",
                        regra="ACESSO-SO-EM-ACCESS",
                        severidade="erro",
                        elemento=r.id,
                        mensagem=f"O tipo de acesso só vale para Access, não para {r.tipo}.",
                    )
                )
            continue
        msg = (
            f"Relação {r.tipo} de {o.tipo} '{o.nome}' para {d.tipo} '{d.nome}' não é "
            "permitida no ArchiMate 3.2."
        )
        if regras.permitida(r.tipo, d.tipo, o.tipo):
            msg += " A direção parece invertida: no sentido contrário ela é permitida."
        else:
            opcoes = regras.relacoes_permitidas(o.tipo, d.tipo)
            msg += f" Permitidas neste sentido: {', '.join(opcoes) or 'nenhuma'}."
        achados.append(
            Achado(
                criterio="V2", regra="REL-PERMITIDA", severidade="erro", elemento=r.id, mensagem=msg
            )
        )
    return achados


# ---------------------------------------------------------------- V3


def _sev(regras: Regras, rid: str, padrao: Severidade) -> Severidade:
    s = regras.regra(rid).get("severidade", padrao)
    return "erro" if s == "erro" else "aviso"


def validar_v3(m: Modelo, regras: Regras) -> list[Achado]:
    a: list[Achado] = []
    ids = m.por_id()

    def add(rid: str, padrao: Severidade, mensagem: str, elemento: str | None = None) -> None:
        a.append(
            Achado(
                criterio="V3",
                regra=rid,
                severidade=_sev(regras, rid, padrao),
                elemento=elemento,
                mensagem=mensagem,
            )
        )

    # COE-02: relações apontando para elementos inexistentes
    validas = []
    for r in m.relacoes:
        faltam = [x for x in (r.origem, r.destino) if x not in ids]
        if faltam:
            add(
                "COE-02",
                "erro",
                f"Relação {r.tipo} '{r.id}' aponta para elemento inexistente: {', '.join(faltam)}.",
                r.id,
            )
        else:
            validas.append(r)

    # COE-01: elementos sem relação
    ligados = {x for r in validas for x in (r.origem, r.destino)}
    for e in m.elementos:
        if e.id not in ligados:
            add("COE-01", "erro", f"{e.tipo} '{e.nome}' não tem nenhuma relação.", e.id)

    # COE-03: nomes únicos por tipo
    contagem = Counter((e.tipo, e.nome.strip().casefold()) for e in m.elementos)
    vistos: set[tuple[str, str]] = set()
    for e in m.elementos:
        chave = (e.tipo, e.nome.strip().casefold())
        if contagem[chave] > 1 and chave not in vistos:
            vistos.add(chave)
            add(
                "COE-03",
                "erro",
                f"Há {contagem[chave]} elementos {e.tipo} com o nome '{e.nome}'.",
                e.id,
            )

    def tipo(eid: str) -> str:
        return ids[eid].tipo

    # COE-04: ApplicationService realizado
    realizadores = set(regras.regra("COE-04").get("realizadores", []))
    for e in m.elementos:
        if e.tipo == "ApplicationService" and not any(
            r.tipo == "Realization" and r.destino == e.id and tipo(r.origem) in realizadores
            for r in validas
        ):
            add(
                "COE-04",
                "aviso",
                f"ApplicationService '{e.nome}' não é realizado por "
                "componente, função ou processo de aplicação.",
                e.id,
            )

    # COE-05: ApplicationComponent ligado à Tecnologia
    for e in m.elementos:
        if e.tipo == "ApplicationComponent" and not any(
            e.id in (r.origem, r.destino)
            and regras.camada(tipo(r.destino if r.origem == e.id else r.origem)) == "tecnologia"
            for r in validas
        ):
            add(
                "COE-05",
                "aviso",
                f"ApplicationComponent '{e.nome}' não está ligado à camada de Tecnologia.",
                e.id,
            )

    # COE-06: BusinessProcess com responsável
    responsaveis = set(regras.regra("COE-06").get("responsaveis", []))
    for e in m.elementos:
        if e.tipo == "BusinessProcess" and not any(
            r.tipo == "Assignment" and r.destino == e.id and tipo(r.origem) in responsaveis
            for r in validas
        ):
            add(
                "COE-06",
                "aviso",
                f"BusinessProcess '{e.nome}' não tem responsável (Assignment de ator ou papel).",
                e.id,
            )

    # COE-07 / COE-08: camadas ligadas
    camadas = {regras.camada(e.tipo) for e in m.elementos}
    pares = {
        frozenset((regras.camada(tipo(r.origem)), regras.camada(tipo(r.destino)))) for r in validas
    }
    for rid, c1, c2, nome in (
        ("COE-07", "negocio", "aplicacao", "Negócio e Aplicação"),
        ("COE-08", "aplicacao", "tecnologia", "Aplicação e Tecnologia"),
    ):
        if {c1, c2} <= camadas and frozenset((c1, c2)) not in pares:
            add(rid, "aviso", f"Há elementos de {nome}, mas nenhuma relação liga as duas camadas.")

    # COE-09: tamanho das visões
    limite = regras.limite("elementos_por_visao", 20)
    for v in m.visoes:
        if len(v.nos) > limite:
            add(
                "COE-09",
                "aviso",
                f"A visão '{v.nome}' tem {len(v.nos)} elementos (limite {limite}).",
                v.id,
            )

    # COE-10: convenções de nome
    conf = regras.regra("COE-10")
    inf = conf.get("infinitivo", {})
    padrao = re.compile(inf.get("padrao", r"^\S*(ar|er|ir)\b"), re.IGNORECASE)
    maximo = int(conf.get("tamanho_maximo_nome", 60))
    for e in m.elementos:
        if e.tipo in inf.get("tipos", []) and not padrao.match(e.nome.strip()):
            add(
                "COE-10",
                "aviso",
                f"{e.tipo} '{e.nome}' deveria começar com verbo no "
                "infinitivo (ex.: 'Registrar pedido').",
                e.id,
            )
        if len(e.nome) > maximo:
            add(
                "COE-10",
                "aviso",
                f"O nome de {e.tipo} '{e.nome[:30]}…' passa de {maximo} caracteres.",
                e.id,
            )
        if not e.nome.strip():
            add("COE-10", "aviso", f"Elemento {e.tipo} sem nome.", e.id)
    return a


# ---------------------------------------------------------------- V4


def validar_v4(m: Modelo, itens: Iterable[ItemRef]) -> list[Achado]:
    a: list[Achado] = []
    itens = list(itens)
    conhecidos = {i.id for i in itens}
    usados = {o for e in m.elementos for o in e.origens} | {
        o for r in m.relacoes for o in r.origens
    }
    for i in itens:
        if i.status == "ativo" and i.tipo in TIPOS_COBERTOS and i.id not in usados:
            a.append(
                Achado(
                    criterio="V4",
                    regra="ITEM-SEM-ELEMENTO",
                    severidade="erro",
                    elemento=i.id,
                    mensagem=f"O item {i.id} ({i.tipo} '{i.nome}') do briefing não aparece em "
                    "nenhum elemento ou relação do modelo.",
                )
            )
    for e in m.elementos:
        if not e.origens and not e.premissa:
            a.append(
                Achado(
                    criterio="V4",
                    regra="ELEMENTO-SEM-ORIGEM",
                    severidade="erro",
                    elemento=e.id,
                    mensagem=f"{e.tipo} '{e.nome}' não cita nenhum item do briefing e não está "
                    "marcado como premissa.",
                )
            )
        desconhecidas = [o for o in e.origens if o not in conhecidos]
        if desconhecidas and conhecidos:
            a.append(
                Achado(
                    criterio="V4",
                    regra="ORIGEM-INEXISTENTE",
                    severidade="erro",
                    elemento=e.id,
                    mensagem=f"{e.tipo} '{e.nome}' cita itens que não existem no briefing: "
                    f"{', '.join(desconhecidas)}.",
                )
            )
    return a


def validar_modelo(m: Modelo, regras: Regras, itens: Sequence[ItemRef] = ()) -> list[Achado]:
    """Ferramenta `validar_modelo` (spec §9.2): achados V2–V4."""
    return [*validar_v2(m, regras), *validar_v3(m, regras), *validar_v4(m, itens)]
