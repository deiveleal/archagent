"""Serviço do agente ArchiMate: orquestra sessões, grafo e LLM (spec §9).

O estado da sessão fica no SessionStore (volume). Cada operação roda um grafo
curto do LangGraph; as "pausas" (perguntas, confirmação do briefing) são o
próprio estado da sessão, retomado na próxima chamada da API (decisão D-09).
"""

from __future__ import annotations

import logging
from pathlib import PurePath
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from archagent.agents.archimate.archi import ArchiClient
from archagent.agents.archimate.interpretacao import (
    Interpretacao,
    ResultadoInterpretacao,
    aplicar,
    gerar_perguntas,
    interpretar,
)
from archagent.agents.archimate.rules import Regras
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.agents.archimate.vault import Vault
from archagent.core.briefing import Briefing, Pergunta
from archagent.core.inputs import EntradaInvalida, EntradaLida, ler_entrada, ler_mensagem
from archagent.core.llm import LLM, LLMResult
from archagent.core.logs import log_event, session_var
from archagent.core.sessions import Entrada, SessionStore

logger = logging.getLogger(__name__)


class ImagemIlegivel(EntradaInvalida):
    """RF-ENT-07: interpretação vazia de uma imagem é falha, não sucesso."""


class EstadoEntrada(TypedDict, total=False):
    sid: str
    nome_arquivo: str | None
    dados: bytes | None
    texto: str | None
    contexto: str
    entrada: Entrada
    lida: EntradaLida
    interp: Interpretacao
    resultado: ResultadoInterpretacao
    perguntas: list[Pergunta]


class ArchimateService:
    def __init__(
        self,
        settings: ArchimateSettings,
        llm: LLM,
        store: SessionStore,
        regras: Regras,
        vault: Vault,
        archi: ArchiClient,
    ) -> None:
        self.settings = settings
        self.llm = llm
        self.store = store
        self.regras = regras
        self.vault = vault
        self.archi = archi
        self.grafo_entrada = self._montar_grafo_entrada()

    # ------------------------------------------------------------ uso de tokens

    def tokens(self, sid: str) -> int:
        return self.store.uso(sid).total

    def hook(self, sid: str) -> Any:
        def registrar(no: str, res: LLMResult) -> None:
            self.store.registrar_uso(sid, no, res.tokens)

        return registrar

    # ------------------------------------------------------------ grafo de entrada

    def _montar_grafo_entrada(self) -> Any:
        g: Any = StateGraph(EstadoEntrada)
        g.add_node("ler_entrada", self._no_ler_entrada)
        g.add_node("interpretar", self._no_interpretar)
        g.add_node("atualizar_briefing", self._no_atualizar_briefing)
        g.add_node("esclarecer", self._no_esclarecer)
        g.add_edge(START, "ler_entrada")
        g.add_edge("ler_entrada", "interpretar")
        g.add_edge("interpretar", "atualizar_briefing")
        g.add_edge("atualizar_briefing", "esclarecer")
        g.add_edge("esclarecer", END)
        return g.compile()

    def _no_ler_entrada(self, st: EstadoEntrada) -> EstadoEntrada:
        """Sem LLM para texto, transcrições e .drawio (spec §9.1)."""
        if st.get("dados") is not None:
            nome = st.get("nome_arquivo") or "entrada.txt"
            lida = ler_entrada(nome, st["dados"] or b"")
            original, ext = st["dados"] or b"", PurePath(nome).suffix.lstrip(".").lower()
        else:
            lida = ler_mensagem(st.get("texto") or "")
            nome, original, ext = None, (st.get("texto") or "").encode("utf-8"), "txt"
        entrada = Entrada(
            id="",
            tipo=lida.tipo,
            formato=lida.formato,
            nome_arquivo=nome,
            tamanho_bytes=len(original),
            conteudo_normalizado=lida.texto_normalizado(),
            imagem_mime=lida.imagem_mime,
        )
        entrada = self.store.adicionar_entrada(st["sid"], entrada, original, ext or "bin")
        log_event(
            logger,
            "entrada.recebida",
            entrada=entrada.id,
            tipo=entrada.tipo,
            formato=entrada.formato,
            tamanho_bytes=entrada.tamanho_bytes,
        )
        return {"entrada": entrada, "lida": lida}

    def _no_interpretar(self, st: EstadoEntrada) -> EstadoEntrada:
        sid = st["sid"]
        interp = interpretar(
            self.llm,
            st["entrada"].id,
            st["lida"],
            self.store.briefing(sid),
            tokens_usados=self.tokens(sid),
            on_usage=self.hook(sid),
            contexto=st.get("contexto", ""),
        )
        return {"interp": interp}

    def _no_atualizar_briefing(self, st: EstadoEntrada) -> EstadoEntrada:
        sid, entrada, lida, interp = st["sid"], st["entrada"], st["lida"], st["interp"]
        if lida.imagem_b64 and (interp.ilegivel or not interp.itens):
            entrada.status = "falhou"
            entrada.observacao = "Imagem ilegível ou sem conteúdo reconhecido."
            self.store.salvar_entrada(sid, entrada)
            raise ImagemIlegivel(
                f"Não consegui ler a imagem {entrada.id}. Envie uma foto mais nítida, um "
                "arquivo .drawio ou descreva o desenho em texto."
            )
        with self.store.lock(sid):
            briefing = self.store.briefing(sid)
            res = aplicar(briefing, interp, entrada.id, lida)
            self.store.salvar_briefing(sid, briefing)
        entrada.status = "interpretada"
        self.store.salvar_entrada(sid, entrada)
        log_event(
            logger,
            "briefing.atualizado",
            entrada=entrada.id,
            novos=len(res.novos),
            unidos=len(res.unidos),
            superados=len(res.superados),
            conflitos=len(res.conflitos),
            origens_ajustadas=res.origens_ajustadas,
        )
        return {"resultado": res}

    def _no_esclarecer(self, st: EstadoEntrada) -> EstadoEntrada:
        return {"perguntas": self.esclarecer(st["sid"])}

    # ------------------------------------------------------------ operações

    def enviar_entrada(
        self,
        sid: str,
        *,
        nome_arquivo: str | None = None,
        dados: bytes | None = None,
        texto: str | None = None,
        contexto: str = "",
    ) -> EstadoEntrada:
        self.store.obter(sid)
        token = session_var.set(sid)
        try:
            estado: EstadoEntrada = {
                "sid": sid,
                "nome_arquivo": nome_arquivo,
                "dados": dados,
                "texto": texto,
                "contexto": contexto,
            }
            resultado: EstadoEntrada = self.grafo_entrada.invoke(estado)
            return resultado
        finally:
            session_var.reset(token)

    def esclarecer(self, sid: str) -> list[Pergunta]:
        with self.store.lock(sid):
            existentes = self.store.perguntas(sid)
            sessao = self.store.obter(sid)
            novas = gerar_perguntas(
                self.llm,
                self.store.briefing(sid),
                existentes,
                max_perguntas=self.settings.max_perguntas_por_rodada,
                rodada=sessao.rodada_perguntas + 1,
                tokens_usados=self.tokens(sid),
                on_usage=self.hook(sid),
            )
            if novas:
                sessao = self.store.obter(sid)
                sessao.rodada_perguntas += 1
                self.store.salvar(sessao)
                self.store.salvar_perguntas(sid, [*existentes, *novas])
        return novas

    def responder(self, sid: str, qid: str, resposta: str | None, pular: bool) -> Pergunta:
        perguntas = self.store.perguntas(sid)
        p = next((x for x in perguntas if x.id == qid), None)
        if p is None:
            raise KeyError(qid)
        if p.status != "pendente":
            raise ValueError(f"A pergunta {qid} já foi {p.status}.")
        if pular or not (resposta or "").strip():
            p.status = "pulada"  # RF-ESC-04: o item fica em aberto e vai para o relatório
            self.store.salvar_perguntas(sid, perguntas)
            return p
        p.status, p.resposta = "respondida", resposta
        self.store.salvar_perguntas(sid, perguntas)
        item = self.store.briefing(sid).item(p.item)
        contexto = (
            f"Esta entrada é a resposta do arquiteto à pergunta {p.id} sobre o item "
            f"{p.item} ({item.tipo if item else '?'}: {item.nome if item else '?'}): "
            f'"{p.texto}". Se ela resolve o item, use substitui="{p.item}".'
        )
        self.store.registrar_mensagem(sid, "arquiteto", resposta or "", pergunta=p.id)
        self.enviar_entrada(sid, texto=resposta, contexto=contexto)
        return p

    def confirmar_briefing(self, sid: str) -> Briefing:
        with self.store.lock(sid):
            b = self.store.briefing(sid)
            b.confirmar()
            self.store.salvar_briefing(sid, b)
        return b
