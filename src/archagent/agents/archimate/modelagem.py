"""Conversão do briefing confirmado em modelo ArchiMate e ciclo validar → corrigir.

O LLM gera o modelo com saída estruturada (RF-MOD-02); as regras do ArchiMate
ficam nos validadores (V2–V4), que devolvem a mensagem exata para correção
(RF-VAL-02), no máximo N rodadas (RF-VAL-03).
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from archagent.agents.archimate import prompts
from archagent.agents.archimate.model import Achado, Elemento, Modelo, Relacao, novo_id
from archagent.agents.archimate.rules import Regras
from archagent.agents.archimate.vault import Vault
from archagent.core.briefing import Briefing
from archagent.core.llm import LLM, Message, UsageHook


class ElementoLLM(BaseModel):
    ref: str
    tipo: str
    nome: str
    documentacao: str = ""
    origens: list[str] = Field(default_factory=list)
    premissa: bool = False
    motivo_premissa: str = ""


class RelacaoLLM(BaseModel):
    tipo: str
    origem: str
    destino: str
    nome: str | None = ""
    origens: list[str] = Field(default_factory=list)
    acesso: Literal["Access", "Read", "Write", "ReadWrite"] | None = None


class ModeloLLM(BaseModel):
    elementos: list[ElementoLLM] = Field(default_factory=list)
    relacoes: list[RelacaoLLM] = Field(default_factory=list)


# ------------------------------------------------------------------ guia a partir do vault


def _campo(corpo: str, rotulo: str) -> str:
    m = re.search(rf"\*\*{re.escape(rotulo)}:?\*\*:?\s*(.+)", corpo)
    if not m:
        return ""
    texto = re.sub(r"\[\[elemento-([a-z-]+)\]\]", lambda x: _camel(x.group(1)), m.group(1))
    return re.sub(r"\[\[([^\]]+)\]\]", r"\1", texto).strip()


def _camel(slug: str) -> str:
    return "".join(p.capitalize() for p in slug.split("-"))


def guia_de_tipos(regras: Regras, vault: Vault) -> str:
    """Resumo das fichas: quando usar e quando não usar cada tipo (RF-MOD-04)."""
    linhas = []
    for camada, titulo in (
        ("negocio", "Negócio"),
        ("aplicacao", "Aplicação"),
        ("tecnologia", "Tecnologia"),
    ):
        linhas.append(f"## {titulo}")
        for t in regras.elementos.values():
            if t.camada != camada:
                continue
            ficha = vault.ficha(t.tipo)
            if ficha is None:
                linhas.append(f"- {t.tipo} ({t.nome_pt})")
                continue
            use = _campo(ficha.corpo, "Use quando")
            nao = _campo(ficha.corpo, "Não use quando")
            linhas.append(f"- {t.tipo} ({t.nome_pt}): use quando {use} Não use quando {nao}")
    return "\n".join(linhas)


def mensagens_modelagem(briefing: Briefing, regras: Regras, vault: Vault) -> list[Message]:
    sistema = (
        f"{prompts.MODELAR}\n\n# Guia de tipos (fichas do vault)\n{guia_de_tipos(regras, vault)}"
    )
    padroes = vault.resumo()
    if padroes:
        sistema += f"\n\n# Padrões, anti-padrões e convenções\n{padroes}"
    usuario = (
        "Briefing confirmado (itens ativos; formato: id [tipo, confiança] nome):\n"
        f"{prompts.entrada_tag(briefing.resumo())}"
    )
    return [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]


# ------------------------------------------------------------------ conversão


def para_modelo(llm_modelo: ModeloLLM, briefing: Briefing, nome: str, mid: str = "M-001") -> Modelo:
    """Troca os "ref" do LLM por ids do Exchange Format e aplica RF-MOD-06."""
    ids: dict[str, str] = {}
    elementos: list[Elemento] = []
    for e in llm_modelo.elementos:
        eid = ids.setdefault(e.ref, novo_id())
        origens = [o for o in e.origens if briefing.item(o)]
        premissa = e.premissa or not origens
        # Elementos que só vêm de pendências ou hipóteses entram como premissa.
        tipos = {briefing.item(o).tipo for o in origens if briefing.item(o)}  # type: ignore[union-attr]
        if origens and tipos <= {"pendencia", "hipotese"}:
            premissa = True
        motivo = e.motivo_premissa
        if premissa and not motivo:
            motivo = (
                "Baseado em pendência ou hipótese do briefing."
                if origens
                else "Criado pelo agente para completar o modelo."
            )
        elementos.append(
            Elemento(
                id=eid,
                tipo=e.tipo,
                nome=e.nome.strip(),
                documentacao=e.documentacao,
                origens=e.origens,
                premissa=premissa,
                motivo_premissa=motivo,
            )
        )
    relacoes = [
        Relacao(
            tipo=r.tipo,
            origem=ids.get(r.origem, r.origem),
            destino=ids.get(r.destino, r.destino),
            nome=r.nome or "",
            origens=r.origens,
            premissa=not r.origens,
            acesso=r.acesso if r.tipo == "Access" else None,
        )
        for r in llm_modelo.relacoes
    ]
    return Modelo(id=mid, nome=nome, elementos=elementos, relacoes=relacoes)


def para_llm(m: Modelo) -> ModeloLLM:
    """Volta o modelo interno ao formato do LLM, para o pedido de correção."""
    refs = {e.id: f"e{i}" for i, e in enumerate(m.elementos, 1)}
    return ModeloLLM(
        elementos=[
            ElementoLLM(
                ref=refs[e.id],
                tipo=e.tipo,
                nome=e.nome,
                documentacao=e.documentacao,
                origens=e.origens,
                premissa=e.premissa,
                motivo_premissa=e.motivo_premissa,
            )
            for e in m.elementos
        ],
        relacoes=[
            RelacaoLLM(
                tipo=r.tipo,
                origem=refs.get(r.origem, r.origem),
                destino=refs.get(r.destino, r.destino),
                nome=r.nome,
                origens=r.origens,
                acesso=r.acesso,
            )
            for r in m.relacoes
        ],
    )


def _descrever(a: Achado, m: Modelo, refs: dict[str, str]) -> str:
    alvo = refs.get(a.elemento or "", a.elemento or "")
    return f"- [{a.criterio} {a.regra}] {alvo}: {a.mensagem}"


# ------------------------------------------------------------------ chamadas


def modelar(
    llm: LLM,
    briefing: Briefing,
    regras: Regras,
    vault: Vault,
    *,
    nome: str,
    mid: str = "M-001",
    tokens_usados: int = 0,
    on_usage: UsageHook | None = None,
) -> Modelo:
    msgs = mensagens_modelagem(briefing, regras, vault)
    resp = llm.structured(
        msgs, ModeloLLM, no="modelar", tokens_usados=tokens_usados, on_usage=on_usage
    )
    return para_modelo(resp, briefing, nome, mid)


def corrigir(
    llm: LLM,
    m: Modelo,
    achados: list[Achado],
    briefing: Briefing,
    regras: Regras,
    vault: Vault,
    *,
    tokens_usados: int = 0,
    on_usage: UsageHook | None = None,
) -> Modelo:
    atual = para_llm(m)
    refs = {e.id: f"e{i}" for i, e in enumerate(m.elementos, 1)}
    refs |= {
        r.id: f"relação {r.tipo} {refs.get(r.origem, '?')}→{refs.get(r.destino, '?')}"
        for r in m.relacoes
    }
    erros = "\n".join(_descrever(a, m, refs) for a in achados)
    msgs = [
        *mensagens_modelagem(briefing, regras, vault),
        {"role": "assistant", "content": json.dumps(atual.model_dump(), ensure_ascii=False)},
        {"role": "user", "content": f"{prompts.CORRIGIR}\n\nErros:\n{erros}"},
    ]
    resp = llm.structured(
        msgs, ModeloLLM, no="corrigir", tokens_usados=tokens_usados, on_usage=on_usage
    )
    novo = para_modelo(resp, briefing, m.nome, m.id)
    novo.exchange_id = m.exchange_id
    return novo
