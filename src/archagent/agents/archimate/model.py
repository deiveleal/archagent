"""Modelo interno ArchiMate, antes da exportação (spec §7.4 e §7.5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Severidade = Literal["erro", "aviso"]
Criterio = Literal["V1", "V2", "V3", "V4", "V5"]


def novo_id() -> str:
    """Ids no padrão do Exchange Format, para que o Archi os preserve."""
    return f"id-{uuid.uuid4().hex}"


class Elemento(BaseModel):
    id: str = Field(default_factory=novo_id)
    tipo: str
    nome: str
    documentacao: str = ""
    origens: list[str] = Field(default_factory=list)
    premissa: bool = False
    motivo_premissa: str = ""


class Relacao(BaseModel):
    id: str = Field(default_factory=novo_id)
    tipo: str
    origem: str
    destino: str
    nome: str = ""
    origens: list[str] = Field(default_factory=list)
    premissa: bool = False
    # Só para Access: Read, Write, ReadWrite ou Access.
    acesso: Literal["Access", "Read", "Write", "ReadWrite"] | None = None


class No(BaseModel):
    elemento: str
    x: int
    y: int
    w: int = 120
    h: int = 55


class Faixa(BaseModel):
    """Faixa de camada desenhada como container na visão."""

    rotulo: str
    camada: str
    x: int
    y: int
    w: int
    h: int


class Conexao(BaseModel):
    relacao: str


class Visao(BaseModel):
    id: str = Field(default_factory=novo_id)
    nome: str
    viewpoint: str
    nos: list[No] = Field(default_factory=list)
    conexoes: list[Conexao] = Field(default_factory=list)
    faixas: list[Faixa] = Field(default_factory=list)


class Achado(BaseModel):
    criterio: Criterio
    regra: str
    severidade: Severidade
    elemento: str | None = None
    mensagem: str


class Validacao(BaseModel):
    viavel: bool = False
    erros: list[Achado] = Field(default_factory=list)
    avisos: list[Achado] = Field(default_factory=list)
    criterios: dict[str, bool] = Field(default_factory=dict)

    @classmethod
    def de_achados(cls, achados: list[Achado], criterios: dict[str, bool]) -> Validacao:
        erros = [a for a in achados if a.severidade == "erro"]
        avisos = [a for a in achados if a.severidade == "aviso"]
        return cls(
            viavel=not erros and all(criterios.values()),
            erros=erros,
            avisos=avisos,
            criterios=criterios,
        )


class Modelo(BaseModel):
    id: str = "M-001"
    nome: str = "Modelo"
    gerado_em: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    elementos: list[Elemento] = Field(default_factory=list)
    relacoes: list[Relacao] = Field(default_factory=list)
    visoes: list[Visao] = Field(default_factory=list)
    validacao: Validacao = Field(default_factory=Validacao)
    exchange_id: str = Field(default_factory=novo_id)

    def elemento(self, eid: str) -> Elemento | None:
        return next((e for e in self.elementos if e.id == eid), None)

    def por_id(self) -> dict[str, Elemento]:
        return {e.id: e for e in self.elementos}
