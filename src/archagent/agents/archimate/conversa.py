"""Conversa com o arquiteto (spec §4.8) e propostas de aprendizado (RF-KB-04)."""

from __future__ import annotations

import json
import re
import threading
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from archagent.agents.archimate import prompts
from archagent.agents.archimate.model import Modelo
from archagent.agents.archimate.vault import Vault
from archagent.core.briefing import Briefing
from archagent.core.llm import LLM, Message, UsageHook

Classe = Literal["pergunta", "informacao", "correcao", "alternativa", "comando"]
Acao = Literal["confirmar_briefing", "gerar_modelo", "nenhuma"]


class Classificacao(BaseModel):
    classe: Classe
    acao: Acao = "nenhuma"
    tema: str = ""


class RespostaPergunta(BaseModel):
    resposta: str
    citados: list[str] = Field(default_factory=list)
    sabe: bool = True


class AvaliacaoAlternativa(BaseModel):
    pros: list[str] = Field(default_factory=list)
    contras: list[str] = Field(default_factory=list)
    impacto_no_modelo: str = ""
    conflitos: list[str] = Field(default_factory=list)
    recomendacao: str = ""

    def markdown(self) -> str:
        def lista(xs: list[str]) -> str:
            return "\n".join(f"- {x}" for x in xs) or "- Nenhum identificado."

        return (
            f"**Prós**\n{lista(self.pros)}\n\n**Contras**\n{lista(self.contras)}\n\n"
            f"**Impacto no modelo**\n{self.impacto_no_modelo or 'Não identificado.'}\n\n"
            f"**Conflitos com o que já foi decidido**\n{lista(self.conflitos)}\n\n"
            f"**Recomendação**\n{self.recomendacao}\n\n"
            "_A alternativa não muda o briefing: para adotá-la, envie a correção._"
        )


def contexto(briefing: Briefing, modelo: Modelo | None, vault: Vault, consulta: str) -> str:
    partes = [f"# Briefing (itens ativos)\n{briefing.resumo()}"]
    superados = [i for i in briefing.itens if i.status == "superado"]
    if superados:
        partes.append(
            "# Itens superados\n"
            + "\n".join(f"{i.id} {i.nome} → {i.superado_por}" for i in superados)
        )
    if modelo is not None:
        nomes = {e.id: e.nome for e in modelo.elementos}
        els = "\n".join(
            f"- {e.tipo} '{e.nome}' (origens {', '.join(e.origens) or '—'})"
            for e in modelo.elementos
        )
        rels = "\n".join(
            f"- {nomes.get(r.origem, '?')} —{r.tipo}→ {nomes.get(r.destino, '?')}"
            for r in modelo.relacoes
        )
        partes.append(
            f"# Modelo {modelo.id} ({'viável' if modelo.validacao.viavel else 'não viável'})"
            f"\nElementos:\n{els}\nRelações:\n{rels}"
        )
    notas = vault.buscar(consulta, limite=3)
    if notas:
        partes.append("# Notas do vault\n" + "\n\n".join(n.texto()[:1500] for n in notas[:4]))
    return "\n\n".join(partes)


def _msgs(sistema: str, ctx: str, texto: str) -> list[Message]:
    return [
        {"role": "system", "content": sistema},
        {
            "role": "user",
            "content": f"{ctx}\n\nMensagem do arquiteto:\n{prompts.entrada_tag(texto)}",
        },
    ]


def classificar(
    llm: LLM,
    texto: str,
    briefing: Briefing,
    *,
    tokens_usados: int = 0,
    on_usage: UsageHook | None = None,
) -> Classificacao:
    return llm.structured(
        _msgs(prompts.CLASSIFICAR, f"# Briefing\n{briefing.resumo()}", texto),
        Classificacao,
        no="classificar",
        tokens_usados=tokens_usados,
        on_usage=on_usage,
    )


def responder(
    llm: LLM, texto: str, ctx: str, *, tokens_usados: int = 0, on_usage: UsageHook | None = None
) -> RespostaPergunta:
    return llm.structured(
        _msgs(prompts.RESPONDER, ctx, texto),
        RespostaPergunta,
        no="responder",
        tokens_usados=tokens_usados,
        on_usage=on_usage,
    )


def avaliar_alternativa(
    llm: LLM, texto: str, ctx: str, *, tokens_usados: int = 0, on_usage: UsageHook | None = None
) -> AvaliacaoAlternativa:
    return llm.structured(
        _msgs(prompts.AVALIAR_ALTERNATIVA, ctx, texto),
        AvaliacaoAlternativa,
        no="avaliar_alternativa",
        tokens_usados=tokens_usados,
        on_usage=on_usage,
    )


# ------------------------------------------------------------------ propostas (RF-KB-04)

SESSOES_PARA_PROPOR = 3
_lock = threading.Lock()


def slug(tema: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "-", tema.lower()).strip("-")
    return t[:60]


class RegistroCorrecoes:
    """Correções por tema, guardadas na pasta de propostas (volume gravável).

    Quando o mesmo tema aparece em 3 sessões diferentes, grava um rascunho de nota em
    `kb/archimate/propostas/`. O agente nunca altera o vault: uma pessoa aprova por PR.
    """

    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        self.arquivo = pasta / "registro-correcoes.json"

    def _ler(self) -> dict[str, list[dict[str, str]]]:
        if not self.arquivo.exists():
            return {}
        dados: dict[str, list[dict[str, str]]] = json.loads(self.arquivo.read_text("utf-8"))
        return dados

    def registrar(self, tema: str, sessao: str, texto: str) -> Path | None:
        chave = slug(tema)
        if not chave:
            return None
        with _lock:
            dados = self._ler()
            lista = dados.setdefault(chave, [])
            lista.append({"sessao": sessao, "texto": texto[:500], "data": date.today().isoformat()})
            self.pasta.mkdir(parents=True, exist_ok=True)
            self.arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2), "utf-8")
            sessoes = sorted({x["sessao"] for x in lista})
            destino = self.pasta / f"{date.today().isoformat()}-{chave}.md"
            ja_existe = any(self.pasta.glob(f"*-{chave}.md"))
            if len(sessoes) < SESSOES_PARA_PROPOR or ja_existe:
                return None
            destino.write_text(self._proposta(chave, lista, sessoes), "utf-8")
            return destino

    @staticmethod
    def _proposta(chave: str, lista: list[dict[str, str]], sessoes: list[str]) -> str:
        exemplos = "\n".join(f'- {x["sessao"]} ({x["data"]}): "{x["texto"]}"' for x in lista)
        return f"""# Proposta de nota: {chave}

## Correção observada

O arquiteto fez correções do tema `{chave}` em {len(sessoes)} sessões diferentes:

{exemplos}

## Sessões

{", ".join(sessoes)}

## Nota proposta

```markdown
---
id: convencao-{chave}
tipo: convencao
camada: todas
tags: [aprendizado]
fontes:
  - "Correções do arquiteto nas sessões {", ".join(sessoes)}"
status: rascunho
revisado_por: null
revisado_em: null
---

# {chave.replace("-", " ").capitalize()}

(Descrever a regra que as correções mostram e quando ela vale.)
```

## Justificativa

A mesma correção se repetiu em {len(sessoes)} sessões (regra RF-KB-04). Uma pessoa
revisa, completa a nota e a aprova por PR para a branch `agent/archimate`.
"""
