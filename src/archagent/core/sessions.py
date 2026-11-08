"""Sessões persistidas em arquivos, num volume (spec §4.1, §7.1, RF-SES-02).

<sessions_dir>/<S-id>/
    sessao.json, briefing.json, perguntas.json, uso.json, conversa.jsonl
    entradas/E-001.<ext> (como enviada) e E-001.json (metadados + texto normalizado)
    modelos/M-001/... (arquivos do agente)
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from archagent.core.briefing import Briefing, Pergunta, agora

StatusSessao = Literal["aberta", "briefing_confirmado", "modelo_gerado"]
MAX_ENTRADAS = 20


class SessaoNaoEncontrada(KeyError):
    pass


class LimiteDeEntradas(ValueError):
    pass


class Sessao(BaseModel):
    id: str
    titulo: str
    status: StatusSessao = "aberta"
    criada_em: datetime = Field(default_factory=agora)
    entradas: list[str] = Field(default_factory=list)
    briefing_confirmado_em: datetime | None = None
    versoes_modelo: list[str] = Field(default_factory=list)
    tokens_usados: int = 0
    rodada_perguntas: int = 0


class Entrada(BaseModel):
    id: str
    tipo: str
    formato: str
    nome_arquivo: str | None = None
    recebida_em: datetime = Field(default_factory=agora)
    tamanho_bytes: int = 0
    conteudo_normalizado: str = ""
    imagem_mime: str | None = None
    status: Literal["recebida", "interpretada", "falhou"] = "recebida"
    observacao: str = ""


class Uso(BaseModel):
    total: int = 0
    por_no: dict[str, int] = Field(default_factory=dict)
    chamadas: int = 0


def _gravar(arquivo: Path, conteudo: str | bytes) -> None:
    """Escrita atômica: grava num temporário e renomeia."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=arquivo.parent, prefix=".tmp-")
    with os.fdopen(fd, "wb") as f:
        f.write(conteudo.encode("utf-8") if isinstance(conteudo, str) else conteudo)
    os.replace(tmp, arquivo)


class SessionStore:
    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        self.pasta.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, threading.RLock] = {}
        self._lock_global = threading.Lock()

    # ------------------------------------------------------------ util

    def _dir(self, sid: str) -> Path:
        if "/" in sid or ".." in sid or not sid.startswith("S-"):
            raise SessaoNaoEncontrada(sid)
        d = self.pasta / sid
        if not (d / "sessao.json").exists():
            raise SessaoNaoEncontrada(sid)
        return d

    @contextmanager
    def lock(self, sid: str) -> Iterator[None]:
        with self._lock_global:
            trava = self._locks.setdefault(sid, threading.RLock())
        with trava:
            yield

    def _ler_json(self, arquivo: Path, padrao: Any) -> Any:
        if not arquivo.exists():
            return padrao
        return json.loads(arquivo.read_text(encoding="utf-8"))

    # ------------------------------------------------------------ sessões

    def criar(self, titulo: str) -> Sessao:
        with self._lock_global:
            dia = agora().strftime("%Y%m%d")
            existentes = sorted(p.name for p in self.pasta.glob(f"S-{dia}-*"))
            n = int(existentes[-1].rsplit("-", 1)[1]) + 1 if existentes else 1
            sessao = Sessao(id=f"S-{dia}-{n:04d}", titulo=titulo.strip() or "Sem título")
            d = self.pasta / sessao.id
            d.mkdir(parents=True)
            _gravar(d / "sessao.json", sessao.model_dump_json(indent=2))
        return sessao

    def listar(self) -> list[Sessao]:
        return [Sessao.model_validate_json((p / "sessao.json").read_text(encoding="utf-8"))
                for p in sorted(self.pasta.glob("S-*"), reverse=True)
                if (p / "sessao.json").exists()]  # fmt: skip

    def obter(self, sid: str) -> Sessao:
        return Sessao.model_validate_json((self._dir(sid) / "sessao.json").read_text("utf-8"))

    def salvar(self, sessao: Sessao) -> None:
        _gravar(self._dir(sessao.id) / "sessao.json", sessao.model_dump_json(indent=2))

    # ------------------------------------------------------------ entradas

    def adicionar_entrada(self, sid: str, entrada: Entrada, original: bytes,
                          extensao: str) -> Entrada:  # fmt: skip
        with self.lock(sid):
            sessao = self.obter(sid)
            if len(sessao.entradas) >= MAX_ENTRADAS:
                raise LimiteDeEntradas(f"A sessão já tem {MAX_ENTRADAS} entradas (limite).")
            entrada.id = f"E-{len(sessao.entradas) + 1:03d}"
            d = self._dir(sid) / "entradas"
            _gravar(d / f"{entrada.id}.{extensao}", original)
            _gravar(d / f"{entrada.id}.json", entrada.model_dump_json(indent=2))
            sessao.entradas.append(entrada.id)
            self.salvar(sessao)
        return entrada

    def salvar_entrada(self, sid: str, entrada: Entrada) -> None:
        _gravar(self._dir(sid) / "entradas" / f"{entrada.id}.json",
                entrada.model_dump_json(indent=2))  # fmt: skip

    def entradas(self, sid: str) -> list[Entrada]:
        d = self._dir(sid) / "entradas"
        return [Entrada.model_validate_json(p.read_text("utf-8"))
                for p in sorted(d.glob("E-*.json"))]  # fmt: skip

    def original(self, sid: str, eid: str) -> bytes:
        d = self._dir(sid) / "entradas"
        arq = next((p for p in d.glob(f"{eid}.*") if p.suffix != ".json"), None)
        if arq is None:
            raise KeyError(eid)
        return arq.read_bytes()

    # ------------------------------------------------------------ briefing e perguntas

    def briefing(self, sid: str) -> Briefing:
        return Briefing.model_validate(self._ler_json(self._dir(sid) / "briefing.json", {}))

    def salvar_briefing(self, sid: str, briefing: Briefing) -> None:
        with self.lock(sid):
            _gravar(self._dir(sid) / "briefing.json", briefing.model_dump_json(indent=2))
            sessao = self.obter(sid)
            sessao.briefing_confirmado_em = briefing.confirmado_em
            if briefing.confirmado:
                if sessao.status == "aberta":
                    sessao.status = "briefing_confirmado"
            elif sessao.status == "briefing_confirmado":
                sessao.status = "aberta"
            self.salvar(sessao)

    def perguntas(self, sid: str) -> list[Pergunta]:
        dados = self._ler_json(self._dir(sid) / "perguntas.json", [])
        return [Pergunta.model_validate(p) for p in dados]

    def salvar_perguntas(self, sid: str, perguntas: list[Pergunta]) -> None:
        _gravar(self._dir(sid) / "perguntas.json",
                json.dumps([p.model_dump(mode="json") for p in perguntas], ensure_ascii=False,
                           indent=2))  # fmt: skip

    # ------------------------------------------------------------ conversa e uso

    def registrar_mensagem(self, sid: str, papel: str, texto: str, **extra: Any) -> None:
        with self.lock(sid):
            arq = self._dir(sid) / "conversa.jsonl"
            linha = json.dumps({"papel": papel, "texto": texto, "em": agora().isoformat(),
                                **extra}, ensure_ascii=False, default=str)  # fmt: skip
            with arq.open("a", encoding="utf-8") as f:
                f.write(linha + "\n")

    def conversa(self, sid: str) -> list[dict[str, Any]]:
        arq = self._dir(sid) / "conversa.jsonl"
        if not arq.exists():
            return []
        return [json.loads(ln) for ln in arq.read_text("utf-8").splitlines() if ln.strip()]

    def uso(self, sid: str) -> Uso:
        return Uso.model_validate(self._ler_json(self._dir(sid) / "uso.json", {}))

    def registrar_uso(self, sid: str, no: str, tokens: int) -> Uso:
        with self.lock(sid):
            uso = self.uso(sid)
            uso.total += tokens
            uso.chamadas += 1
            uso.por_no[no] = uso.por_no.get(no, 0) + tokens
            _gravar(self._dir(sid) / "uso.json", uso.model_dump_json(indent=2))
            sessao = self.obter(sid)
            sessao.tokens_usados = uso.total
            self.salvar(sessao)
        return uso

    # ------------------------------------------------------------ arquivos livres

    def pasta_sessao(self, sid: str) -> Path:
        return self._dir(sid)

    def gravar_arquivo(self, sid: str, relativo: str, conteudo: str | bytes) -> Path:
        destino = (self._dir(sid) / relativo).resolve()
        if not destino.is_relative_to(self._dir(sid).resolve()):
            raise ValueError("Caminho fora da sessão")
        _gravar(destino, conteudo)
        return destino
