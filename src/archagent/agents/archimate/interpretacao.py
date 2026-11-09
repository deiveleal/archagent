"""Interpretação das entradas em itens do briefing e perguntas de esclarecimento.

O LLM só propõe itens; o código aplica as regras do briefing (união, conflito,
correção) e confere se cada origem aponta para um trecho que existe.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from archagent.agents.archimate import prompts
from archagent.core.briefing import Briefing, ItemBriefing, Origem, Pergunta, normalizar_nome
from archagent.core.inputs import EntradaLida
from archagent.core.llm import LLM, Message, UsageHook, image_message

TipoExtraido = Literal[
    "ator",
    "processo",
    "servico",
    "sistema",
    "interface",
    "dado",
    "infraestrutura",
    "ligacao",
    "requisito",
    "decisao",
    "hipotese",
    "pendencia",
]


class ItemExtraido(BaseModel):
    tipo: TipoExtraido
    nome: str
    descricao: str = ""
    local: str = ""
    trecho: str = ""
    confianca: Literal["alta", "media", "baixa"] = "media"
    de: str | None = None
    para: str | None = None
    rotulo: str | None = ""
    substitui: str | None = None


class ConflitoExtraido(BaseModel):
    descricao: str
    itens: list[str] = Field(default_factory=list)
    local: str = ""
    trecho: str = ""


class Interpretacao(BaseModel):
    itens: list[ItemExtraido] = Field(default_factory=list)
    conflitos: list[ConflitoExtraido] = Field(default_factory=list)
    descartar: list[str] = Field(default_factory=list)
    ilegivel: bool = False


class PerguntaLLM(BaseModel):
    item: str
    pergunta: str
    impacto: Literal["alto", "medio", "baixo"] = "medio"


class Perguntas(BaseModel):
    perguntas: list[PerguntaLLM] = Field(default_factory=list)


class ResultadoInterpretacao(BaseModel):
    novos: list[str] = Field(default_factory=list)
    unidos: list[str] = Field(default_factory=list)
    superados: list[str] = Field(default_factory=list)
    conflitos: list[str] = Field(default_factory=list)
    origens_ajustadas: int = 0
    ilegivel: bool = False


# ------------------------------------------------------------------ chamada ao LLM


def mensagens_interpretacao(
    entrada_id: str, lida: EntradaLida, briefing: Briefing, contexto: str = ""
) -> list[Message]:
    sistema = prompts.INTERPRETAR
    if lida.imagem_b64:
        sistema += "\n\n" + prompts.INTERPRETAR_IMAGEM
    cabecalho = (
        f"Briefing atual (itens ativos):\n{briefing.resumo()}\n\n"
        f"Entrada {entrada_id} ({lida.tipo}, {lida.formato})."
    )
    if contexto:
        cabecalho += f"\nContexto: {contexto}"
    msgs: list[Message] = [{"role": "system", "content": sistema}]
    if lida.imagem_b64:
        msgs.append(
            image_message(
                f"{cabecalho}\n{prompts.entrada_tag('(imagem anexa)')}",
                lida.imagem_b64,
                lida.imagem_mime or "image/png",
            )
        )
    else:
        msgs.append(
            {
                "role": "user",
                "content": f"{cabecalho}\n{prompts.entrada_tag(lida.texto_normalizado())}",
            }
        )
    return msgs


def interpretar(
    llm: LLM,
    entrada_id: str,
    lida: EntradaLida,
    briefing: Briefing,
    *,
    tokens_usados: int = 0,
    on_usage: UsageHook | None = None,
    contexto: str = "",
) -> Interpretacao:
    msgs = mensagens_interpretacao(entrada_id, lida, briefing, contexto)
    modelo = llm.settings.llm_model_vision if lida.imagem_b64 else None
    return llm.structured(
        msgs,
        Interpretacao,
        no="interpretar",
        modelo=modelo,
        tokens_usados=tokens_usados,
        on_usage=on_usage,
    )


# ------------------------------------------------------------------ aplicação


def _ajustar_origem(it: ItemExtraido, entrada_id: str, lida: EntradaLida) -> tuple[Origem, bool]:
    """Garante que o local exista na entrada; procura pelo trecho se precisar."""
    if lida.imagem_b64:
        return Origem(entrada=entrada_id, local=it.local or "imagem", trecho=it.trecho), False
    locais = {ln.local: ln.texto for ln in lida.linhas}
    local = it.local.strip().strip("[]")
    trecho_norm = normalizar_nome(it.trecho)
    if local in locais and (not trecho_norm or trecho_norm in normalizar_nome(locais[local])):
        return Origem(entrada=entrada_id, local=local, trecho=it.trecho), False
    if trecho_norm:
        for ln in lida.linhas:
            if trecho_norm in normalizar_nome(ln.texto):
                return Origem(entrada=entrada_id, local=ln.local, trecho=it.trecho), True
        # Trecho que atravessa a quebra de linha: cita a linha onde ele começa.
        for atual, seguinte in zip(lida.linhas, lida.linhas[1:], strict=False):
            if trecho_norm in normalizar_nome(f"{atual.texto} {seguinte.texto}"):
                mesmo = atual.local == local
                return Origem(entrada=entrada_id, local=atual.local, trecho=it.trecho), not mesmo
    nome_norm = normalizar_nome(it.nome)
    for ln in lida.linhas:
        if nome_norm and nome_norm in normalizar_nome(ln.texto):
            return Origem(entrada=entrada_id, local=ln.local, trecho=ln.texto[:120]), True
    if local in locais:
        return Origem(entrada=entrada_id, local=local, trecho=locais[local][:120]), True
    return Origem(entrada=entrada_id, local="", trecho=it.trecho), True


def aplicar(
    briefing: Briefing, interp: Interpretacao, entrada_id: str, lida: EntradaLida
) -> ResultadoInterpretacao:
    res = ResultadoInterpretacao(ilegivel=interp.ilegivel)
    nomes: dict[str, str] = {}  # nome normalizado → id, só deste lote
    antes = {i.id for i in briefing.itens}

    def resolver(ref: str | None) -> str | None:
        if not ref:
            return None
        ref = ref.strip()
        if briefing.item(ref):
            return ref
        if normalizar_nome(ref) in nomes:
            return nomes[normalizar_nome(ref)]
        achado = briefing.procurar_nome(ref)
        return achado.id if achado else None

    def registrar(item: ItemBriefing, substitui: str | None) -> ItemBriefing:
        alvo = briefing.item(substitui) if substitui else None
        if alvo and alvo.status == "ativo":
            criado = briefing.corrigir(alvo.id, item)
            res.superados.append(alvo.id)
        else:
            criado = briefing.adicionar(item)
        (res.novos if criado.id not in antes else res.unidos).append(criado.id)
        return criado

    # 1) itens que não são ligações
    for it in interp.itens:
        if it.tipo == "ligacao" or not it.nome.strip():
            continue
        origem, ajustada = _ajustar_origem(it, entrada_id, lida)
        res.origens_ajustadas += ajustada
        confianca = "baixa" if not origem.local and not lida.imagem_b64 else it.confianca
        criado = registrar(
            ItemBriefing(
                tipo=it.tipo,
                nome=it.nome.strip(),
                descricao=it.descricao,
                origens=[origem],
                confianca=confianca,
            ),
            it.substitui,
        )
        nomes[normalizar_nome(it.nome)] = criado.id

    # 2) ligações, resolvendo os nomes de origem e destino
    for it in interp.itens:
        if it.tipo != "ligacao":
            continue
        origem, ajustada = _ajustar_origem(it, entrada_id, lida)
        res.origens_ajustadas += ajustada
        de, para = resolver(it.de), resolver(it.para)
        nome_de = briefing.item(de).nome if de and briefing.item(de) else (it.de or "?")  # type: ignore[union-attr]
        nome_para = briefing.item(para).nome if para and briefing.item(para) else (it.para or "?")  # type: ignore[union-attr]
        confianca = it.confianca if de and para else "baixa"
        criado = registrar(
            ItemBriefing(
                tipo="ligacao",
                nome=f"{nome_de} → {nome_para}",
                descricao=it.descricao,
                origens=[origem],
                confianca=confianca,
                de=de,
                para=para,
                rotulo=it.rotulo or "",
                relacionados=[x for x in (de, para) if x],
            ),
            it.substitui,
        )
        nomes[normalizar_nome(it.nome)] = criado.id

    # 3) conflitos
    for c in interp.conflitos:
        ids = [x for x in (resolver(r) for r in c.itens) if x]
        if not ids:
            continue
        # Um conflito costuma citar várias linhas: cada trecho vira uma origem.
        partes = [
            t.strip() for t in re.split(r"\s+/\s+|\s*\.\.\.\s*|\s*…\s*", c.trecho) if t.strip()
        ] or [""]
        origens: list[Origem] = []
        for parte in partes:
            o, ajustada = _ajustar_origem(
                ItemExtraido(tipo="pendencia", nome=c.descricao, local=c.local, trecho=parte),
                entrada_id,
                lida,
            )
            res.origens_ajustadas += ajustada
            if o not in origens:
                origens.append(o)
        criado = briefing.registrar_conflito(sorted(set(ids)), c.descricao, origens)
        res.conflitos.append(criado.id)

    # 4) descartes
    for iid in interp.descartar:
        item = briefing.item(iid)
        if item and item.status == "ativo":
            briefing.descartar(iid)
    return res


# ------------------------------------------------------------------ esclarecimento


def gerar_perguntas(
    llm: LLM,
    briefing: Briefing,
    existentes: list[Pergunta],
    *,
    max_perguntas: int = 5,
    rodada: int = 1,
    tokens_usados: int = 0,
    on_usage: UsageHook | None = None,
) -> list[Pergunta]:
    """RF-ESC-01..03: perguntas para itens de baixa confiança, conflitos e pendências."""
    ja = {p.item for p in existentes}
    candidatos = [i for i in briefing.para_esclarecer() if i.id not in ja]
    if not candidatos:
        return []
    lista = "\n".join(
        f"{i.id} [{i.tipo}, confiança {i.confianca}] {i.nome}"
        + (f": {i.descricao}" if i.descricao else "")
        + (f" (entre {', '.join(i.itens)})" if i.itens else "")
        for i in candidatos
    )
    msgs: list[Message] = [
        {"role": "system", "content": prompts.ESCLARECER.format(max_perguntas=max_perguntas)},
        {
            "role": "user",
            "content": f"Briefing atual:\n{briefing.resumo()}\n\nCandidatos a pergunta:\n{lista}",
        },
    ]
    resp = llm.structured(
        msgs, Perguntas, no="esclarecer", tokens_usados=tokens_usados, on_usage=on_usage
    )
    validos = {i.id for i in candidatos}
    ordem = {"alto": 0, "medio": 1, "baixo": 2}
    escolhidas: list[PerguntaLLM] = []
    for p in sorted(resp.perguntas, key=lambda p: ordem[p.impacto]):
        if p.item in validos and p.item not in {e.item for e in escolhidas}:
            escolhidas.append(p)
    n0 = len(existentes)
    return [
        Pergunta(
            id=f"Q-{n0 + k:03d}", item=p.item, texto=p.pergunta, impacto=p.impacto, rodada=rodada
        )
        for k, p in enumerate(escolhidas[:max_perguntas], 1)
    ]
