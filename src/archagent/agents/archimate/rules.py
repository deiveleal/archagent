"""Regras do ArchiMate carregadas como dados (spec §10.2, RF-KB-01).

As regras nunca ficam só no prompt: os validadores consultam estes dados.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from lxml import etree

# Letras usadas no relationships.xml do Archi.
LETRAS_RELACOES = {
    "a": "Access",
    "c": "Composition",
    "f": "Flow",
    "g": "Aggregation",
    "i": "Assignment",
    "n": "Influence",
    "o": "Association",
    "r": "Realization",
    "s": "Specialization",
    "t": "Triggering",
    "v": "Serving",
}
TIPOS_RELACAO = tuple(sorted(LETRAS_RELACOES.values()))
CAMADAS = ("negocio", "aplicacao", "tecnologia")


class RegrasInvalidas(RuntimeError):
    """Regras ausentes ou inválidas: o agente não sobe (RF-KB-01)."""


def extrair_relacoes(relationships_xml: Path, fonte: str) -> dict[str, Any]:
    """Converte o relationships.xml do Archi em relacoes.json (não editar à mão)."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    raiz = etree.parse(str(relationships_xml), parser).getroot()
    permitidas: dict[str, dict[str, list[str]]] = {}
    for origem in raiz.findall("source"):
        alvos: dict[str, list[str]] = {}
        for alvo in origem.findall("target"):
            letras = alvo.get("relations", "")
            alvos[alvo.get("concept", "")] = sorted(LETRAS_RELACOES[c] for c in letras)
        permitidas[origem.get("concept", "")] = dict(sorted(alvos.items()))
    return {
        "versao_archimate": raiz.get("version"),
        "fonte": fonte,
        "sha256_fonte": hashlib.sha256(relationships_xml.read_bytes()).hexdigest(),
        "permitidas": dict(sorted(permitidas.items())),
    }


@dataclass(frozen=True)
class TipoElemento:
    tipo: str
    camada: str
    aspecto: str
    nome_pt: str


@dataclass
class Regras:
    elementos: dict[str, TipoElemento]
    permitidas: dict[str, dict[str, list[str]]]
    coerencia: dict[str, Any]
    pasta: Path
    fonte_relacoes: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def xsd_dir(self) -> Path:
        return self.pasta / "xsd"

    def camada(self, tipo: str) -> str | None:
        t = self.elementos.get(tipo)
        return t.camada if t else None

    def relacoes_permitidas(self, origem: str, destino: str) -> list[str]:
        return list(self.permitidas.get(origem, {}).get(destino, []))

    def permitida(self, tipo_relacao: str, origem: str, destino: str) -> bool:
        return tipo_relacao in self.relacoes_permitidas(origem, destino)

    def regra(self, rid: str) -> dict[str, Any]:
        regras: dict[str, Any] = self.coerencia.get("regras", {})
        return dict(regras.get(rid, {}))

    def limite(self, nome: str, padrao: int) -> int:
        return int(self.coerencia.get("limites", {}).get(nome, padrao))


def carregar_regras(kb_dir: Path) -> Regras:
    pasta = kb_dir / "archimate" / "regras"
    try:
        elementos_raw = json.loads((pasta / "elementos.json").read_text(encoding="utf-8"))
        relacoes_raw = json.loads((pasta / "relacoes.json").read_text(encoding="utf-8"))
        coerencia = yaml.safe_load((pasta / "coerencia.yaml").read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise RegrasInvalidas(f"Não foi possível carregar as regras em {pasta}: {exc}") from exc
    elementos: dict[str, TipoElemento] = {}
    for item in elementos_raw:
        t = TipoElemento(item["tipo"], item["camada"], item["aspecto"], item["nome_pt"])
        if t.camada not in CAMADAS:
            raise RegrasInvalidas(f"Camada inválida para {t.tipo}: {t.camada}")
        elementos[t.tipo] = t
    permitidas = relacoes_raw.get("permitidas")
    if not elementos or not isinstance(permitidas, dict) or not permitidas:
        raise RegrasInvalidas("elementos.json ou relacoes.json vazios")
    faltando = [t for t in elementos if t not in permitidas]
    if faltando:
        raise RegrasInvalidas(f"Tipos sem relações em relacoes.json: {faltando}")
    for xsd in ("archimate3_Diagram.xsd", "archimate3_View.xsd", "archimate3_Model.xsd"):
        if not (pasta / "xsd" / xsd).exists():
            raise RegrasInvalidas(f"XSD ausente: {xsd}")
    if not isinstance(coerencia, dict) or "regras" not in coerencia:
        raise RegrasInvalidas("coerencia.yaml sem a chave 'regras'")
    return Regras(elementos, permitidas, coerencia, pasta, str(relacoes_raw.get("fonte", "")))
