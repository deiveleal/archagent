"""Briefing: resumo estruturado das entradas, com origem de cada item (spec §4.3, §7.3).

Correções não apagam: o item antigo fica `superado` (arXiv 2501.13956).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TipoItem = Literal[
    "ator", "processo", "servico", "sistema", "interface", "dado", "infraestrutura",
    "ligacao", "requisito", "decisao", "hipotese", "pendencia", "conflito",
]  # fmt: skip
TIPOS_ITEM: tuple[str, ...] = TipoItem.__args__  # type: ignore[attr-defined]
Confianca = Literal["alta", "media", "baixa"]
StatusItem = Literal["ativo", "superado", "descartado"]
_ORDEM_CONFIANCA = {"baixa": 0, "media": 1, "alta": 2}


def agora() -> datetime:
    return datetime.now().astimezone()


def normalizar_nome(nome: str) -> str:
    t = unicodedata.normalize("NFKD", nome)
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class Origem(BaseModel):
    entrada: str
    local: str = ""
    trecho: str = ""


class ItemBriefing(BaseModel):
    id: str = ""
    tipo: TipoItem
    nome: str
    descricao: str = ""
    origens: list[Origem] = Field(default_factory=list)
    confianca: Confianca = "media"
    status: StatusItem = "ativo"
    registrado_em: datetime = Field(default_factory=agora)
    superado_por: str | None = None
    relacionados: list[str] = Field(default_factory=list)
    # ligacao
    de: str | None = None
    para: str | None = None
    rotulo: str = ""
    # conflito
    itens: list[str] = Field(default_factory=list)

    def chave(self) -> tuple[str, str]:
        if self.tipo == "ligacao" and self.de and self.para:
            return (self.tipo, f"{self.de}->{self.para}")
        return (self.tipo, normalizar_nome(self.nome))


class Briefing(BaseModel):
    itens: list[ItemBriefing] = Field(default_factory=list)
    confirmado_em: datetime | None = None
    proximo: int = 1

    # ------------------------------------------------------------ consulta

    def item(self, iid: str) -> ItemBriefing | None:
        return next((i for i in self.itens if i.id == iid), None)

    def ativos(self, tipo: str | None = None) -> list[ItemBriefing]:
        return [i for i in self.itens if i.status == "ativo" and (tipo is None or i.tipo == tipo)]

    def filtrar(self, status: str | None = None, tipo: str | None = None,
                ids: list[str] | None = None) -> list[ItemBriefing]:  # fmt: skip
        """Ferramenta `consultar_briefing`."""
        return [i for i in self.itens
                if (status is None or i.status == status) and (tipo is None or i.tipo == tipo)
                and (ids is None or i.id in ids)]  # fmt: skip

    def procurar(self, tipo: str, nome: str) -> ItemBriefing | None:
        alvo = normalizar_nome(nome)
        return next((i for i in self.ativos(tipo) if normalizar_nome(i.nome) == alvo), None)

    def procurar_nome(self, nome: str) -> ItemBriefing | None:
        """Item ativo (que não seja ligação) com esse nome, de qualquer tipo."""
        alvo = normalizar_nome(nome)
        return next((i for i in self.ativos()
                     if i.tipo not in ("ligacao", "conflito") and normalizar_nome(i.nome) == alvo),
                    None)  # fmt: skip

    @property
    def confirmado(self) -> bool:
        return self.confirmado_em is not None

    # ------------------------------------------------------------ mudanças

    def _mudou(self) -> None:
        # RF-BRI-08: qualquer mudança desfaz a confirmação.
        self.confirmado_em = None

    def _novo_id(self) -> str:
        iid = f"B-{self.proximo:03d}"
        self.proximo += 1
        return iid

    def adicionar(self, novo: ItemBriefing) -> ItemBriefing:
        """Adiciona; se já existe item ativo igual, une as origens (RF-BRI-04)."""
        existente = next((i for i in self.ativos() if i.chave() == novo.chave()), None)
        if existente:
            for o in novo.origens:
                if o not in existente.origens:
                    existente.origens.append(o)
            if _ORDEM_CONFIANCA[novo.confianca] > _ORDEM_CONFIANCA[existente.confianca]:
                existente.confianca = novo.confianca
            if novo.descricao and novo.descricao not in existente.descricao:
                existente.descricao = f"{existente.descricao} {novo.descricao}".strip()
            for r in novo.relacionados:
                if r not in existente.relacionados and r != existente.id:
                    existente.relacionados.append(r)
            self._mudou()
            return existente
        novo.id = self._novo_id()
        novo.status = "ativo"
        self.itens.append(novo)
        self._mudou()
        return novo

    def registrar_conflito(self, ids: list[str], descricao: str,
                           origens: list[Origem] | None = None) -> ItemBriefing:  # fmt: skip
        """RF-BRI-05: o agente não escolhe um lado; liga os itens num `conflito`."""
        nomes = [self.item(i).nome for i in ids if self.item(i)]  # type: ignore[union-attr]
        conflito = ItemBriefing(tipo="conflito", nome=" × ".join(nomes) or descricao[:60],
                                descricao=descricao, itens=list(ids), confianca="baixa",
                                origens=origens or [])  # fmt: skip
        conflito = self.adicionar(conflito)
        for i in ids:
            item = self.item(i)
            if item and conflito.id not in item.relacionados:
                item.relacionados.append(conflito.id)
        return conflito

    def corrigir(self, antigo_id: str, novo: ItemBriefing) -> ItemBriefing:
        """RF-BRI-06: o item antigo fica `superado`, com referência ao novo."""
        antigo = self.item(antigo_id)
        if antigo is None:
            raise KeyError(f"Item {antigo_id} não existe no briefing")
        antigo.status = "superado"
        if antigo_id not in novo.relacionados:
            novo.relacionados.append(antigo_id)
        criado = self.adicionar(novo)
        antigo.superado_por = criado.id
        # Ligações e conflitos que apontavam para o antigo passam a apontar para o novo.
        for i in self.ativos():
            if i.de == antigo_id:
                i.de = criado.id
            if i.para == antigo_id:
                i.para = criado.id
        self._mudou()
        return criado

    def descartar(self, iid: str) -> None:
        item = self.item(iid)
        if item:
            item.status = "descartado"
            self._mudou()

    def confirmar(self) -> None:
        self.confirmado_em = agora()

    def para_esclarecer(self) -> list[ItemBriefing]:
        """RF-ESC-01: itens de confiança baixa, conflitos e pendências ativos."""
        return [i for i in self.ativos()
                if i.confianca == "baixa" or i.tipo in ("conflito", "pendencia")]  # fmt: skip

    def resumo(self) -> str:
        """Linhas curtas dos itens ativos, para o contexto do LLM."""
        linhas = []
        for i in self.ativos():
            extra = ""
            if i.tipo == "ligacao":
                extra = f" ({i.de} → {i.para}{', ' + i.rotulo if i.rotulo else ''})"
            elif i.tipo == "conflito":
                extra = f" (entre {', '.join(i.itens)})"
            desc = f": {i.descricao}" if i.descricao else ""
            linhas.append(f"{i.id} [{i.tipo}, {i.confianca}] {i.nome}{extra}{desc}")
        return "\n".join(linhas) or "(vazio)"


class Pergunta(BaseModel):
    id: str
    item: str
    texto: str
    impacto: Literal["alto", "medio", "baixo"] = "medio"
    status: Literal["pendente", "respondida", "pulada"] = "pendente"
    resposta: str | None = None
    rodada: int = 1
    criada_em: datetime = Field(default_factory=agora)
