"""Vault de notas Markdown (spec §10.3) e busca (RF-KB-02).

Busca por palavra (BM25) com normalização de acentos, seguindo os links
`[[...]]` até 1 nível. A busca por embeddings fica para quando houver modelo de
embeddings disponível (pendência P-04; arXiv 2506.05690 indica que busca simples
basta para uma base pequena).
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CAMPOS_OBRIGATORIOS = ("id", "tipo", "camada", "tags", "fontes", "status")
TIPOS_NOTA = ("elemento", "padrao", "antipadrao", "convencao")
LINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
STOPWORDS = frozenset(
    [
        "a",
        "o",
        "as",
        "os",
        "de",
        "da",
        "do",
        "das",
        "dos",
        "e",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "um",
        "uma",
        "uns",
        "umas",
        "por",
        "para",
        "com",
        "sem",
        "que",
        "se",
        "ao",
        "aos",
        "à",
        "às",
        "ou",
        "é",
        "ser",
        "como",
        "mais",
        "menos",
        "quando",
        "não",
        "sim",
        "seu",
        "sua",
        "seus",
        "suas",
        "the",
        "of",
    ]
)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.casefold()


def tokens(texto: str) -> list[str]:
    # Separa CamelCase (ApplicationComponent → application component).
    texto = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", texto)
    return [
        t for t in re.findall(r"[a-z0-9]+", normalizar(texto)) if len(t) > 1 and t not in STOPWORDS
    ]


@dataclass
class Nota:
    id: str
    meta: dict[str, Any]
    corpo: str
    arquivo: Path
    links: list[str] = field(default_factory=list)

    @property
    def tipo(self) -> str:
        return str(self.meta.get("tipo", ""))

    @property
    def status(self) -> str:
        return str(self.meta.get("status", ""))

    @property
    def archimate(self) -> str | None:
        valor = self.meta.get("archimate")
        return str(valor) if valor else None

    @property
    def titulo(self) -> str:
        m = re.search(r"^#\s+(.+)$", self.corpo, re.MULTILINE)
        return m.group(1).strip() if m else self.id

    def texto(self) -> str:
        return f"---\nid: {self.id}\n---\n{self.corpo.strip()}"


def ler_nota(arquivo: Path) -> Nota:
    bruto = arquivo.read_text(encoding="utf-8")
    if not bruto.startswith("---"):
        raise ValueError(f"{arquivo}: sem cabeçalho de metadados")
    _, cabecalho, corpo = bruto.split("---", 2)
    meta = yaml.safe_load(cabecalho) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"{arquivo}: cabeçalho inválido")
    return Nota(
        id=str(meta.get("id", arquivo.stem)),
        meta=meta,
        corpo=corpo,
        arquivo=arquivo,
        links=sorted(set(LINK.findall(corpo))),
    )


def validar_nota(nota: Nota, ids: set[str]) -> list[str]:
    erros = [
        f"{nota.arquivo.name}: falta o campo '{c}'"
        for c in CAMPOS_OBRIGATORIOS
        if c not in nota.meta
    ]
    if nota.tipo not in TIPOS_NOTA:
        erros.append(f"{nota.arquivo.name}: tipo '{nota.tipo}' inválido")
    if nota.status not in ("rascunho", "revisado"):
        erros.append(f"{nota.arquivo.name}: status '{nota.status}' inválido")
    if nota.status == "revisado" and not nota.meta.get("revisado_por"):
        erros.append(f"{nota.arquivo.name}: nota revisada sem 'revisado_por'")
    if nota.tipo == "elemento" and not nota.archimate:
        erros.append(f"{nota.arquivo.name}: ficha de elemento sem 'archimate'")
    if nota.id != nota.arquivo.stem:
        erros.append(f"{nota.arquivo.name}: id '{nota.id}' diferente do nome do arquivo")
    erros += [
        f"{nota.arquivo.name}: link para nota inexistente [[{alvo}]]"
        for alvo in nota.links
        if alvo not in ids
    ]
    return erros


class Vault:
    def __init__(self, notas: list[Nota], incluir_rascunhos: bool = False) -> None:
        self.todas = {n.id: n for n in notas}
        self.notas = {n.id: n for n in notas if incluir_rascunhos or n.status == "revisado"}
        self._docs = {
            nid: Counter(
                tokens(
                    f"{n.titulo} {n.titulo} {n.corpo} "
                    f"{' '.join(map(str, n.meta.get('tags', [])))} "
                    f"{n.archimate or ''}"
                )
            )
            for nid, n in self.notas.items()
        }
        n_docs = max(len(self._docs), 1)
        df: Counter[str] = Counter()
        for c in self._docs.values():
            df.update(c.keys())
        self._idf = {t: math.log(1 + (n_docs - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self._media = sum(sum(c.values()) for c in self._docs.values()) / n_docs

    @classmethod
    def carregar(cls, pasta: Path, incluir_rascunhos: bool = False) -> Vault:
        notas = [ler_nota(a) for a in sorted(pasta.rglob("*.md"))] if pasta.exists() else []
        return cls(notas, incluir_rascunhos)

    @property
    def rascunhos(self) -> list[str]:
        return sorted(n.id for n in self.todas.values() if n.status != "revisado")

    def _bm25(
        self, consulta: list[str], doc: Counter[str], k1: float = 1.5, b: float = 0.75
    ) -> float:
        tamanho = sum(doc.values())
        total = 0.0
        for t in consulta:
            f = doc.get(t, 0)
            if f:
                total += (
                    self._idf.get(t, 0)
                    * f
                    * (k1 + 1)
                    / (f + k1 * (1 - b + b * tamanho / (self._media or 1)))
                )
        return total

    def buscar(
        self, consulta: str, limite: int = 5, tipo: str | None = None, camada: str | None = None
    ) -> list[Nota]:
        """Ferramenta `buscar_vault`: notas mais relevantes + notas ligadas (1 nível)."""
        q = tokens(consulta)
        pontos = []
        for nid, doc in self._docs.items():
            n = self.notas[nid]
            if (tipo and n.tipo != tipo) or (camada and n.meta.get("camada") != camada):
                continue
            p = self._bm25(q, doc)
            if p > 0:
                pontos.append((p, nid))
        principais = [self.notas[nid] for _, nid in sorted(pontos, reverse=True)[:limite]]
        resultado = list(principais)
        for n in principais:
            for alvo in n.links:
                if alvo in self.notas and self.notas[alvo] not in resultado:
                    resultado.append(self.notas[alvo])
        return resultado

    def ficha(self, tipo_archimate: str) -> Nota | None:
        """Ferramenta `ficha_elemento`."""
        return next(
            (
                n
                for n in self.notas.values()
                if n.tipo == "elemento" and n.archimate == tipo_archimate
            ),
            None,
        )

    def resumo(self, tipos: tuple[str, ...] = ("padrao", "antipadrao", "convencao")) -> str:
        """Notas curtas que cabem inteiras no contexto (plano §2.4)."""
        return "\n\n".join(n.texto() for n in self.notas.values() if n.tipo in tipos)
