"""Serviço do agente ArchiMate: orquestra sessões, grafo e LLM (spec §9).

O estado da sessão fica no SessionStore (volume). Cada operação roda um grafo
curto do LangGraph; as "pausas" (perguntas, confirmação do briefing) são o
próprio estado da sessão, retomado na próxima chamada da API (decisão D-09).
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import PurePath
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from archagent.agents.archimate.archi import ArchiClient, ArchiIndisponivel
from archagent.agents.archimate.conversa import (
    Classificacao,
    RegistroCorrecoes,
    avaliar_alternativa,
    classificar,
    contexto,
    responder,
)
from archagent.agents.archimate.exchange import exportar, validar_v1
from archagent.agents.archimate.interpretacao import (
    Interpretacao,
    ResultadoInterpretacao,
    aplicar,
    gerar_perguntas,
    interpretar,
)
from archagent.agents.archimate.layout import gerar_visoes
from archagent.agents.archimate.model import Achado, Modelo, Validacao
from archagent.agents.archimate.modelagem import corrigir, modelar
from archagent.agents.archimate.relatorio import gerar_relatorio
from archagent.agents.archimate.rules import Regras
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.agents.archimate.validation import validar_modelo
from archagent.agents.archimate.vault import Vault
from archagent.core.briefing import Briefing, Pergunta
from archagent.core.inputs import EntradaInvalida, EntradaLida, ler_entrada, ler_mensagem
from archagent.core.llm import LLM, LLMResult
from archagent.core.logs import log_event, session_var
from archagent.core.sessions import Entrada, SessionStore

logger = logging.getLogger(__name__)


class ImagemIlegivel(EntradaInvalida):
    """RF-ENT-07: interpretação vazia de uma imagem é falha, não sucesso."""


class BriefingNaoConfirmado(RuntimeError):
    """RF-BRI-07: a modelagem só começa com o briefing confirmado."""


class EstadoModelo(TypedDict, total=False):
    sid: str
    mid: str
    job: str
    inicio: float
    modelo: Modelo
    achados: list[Achado]
    rodada: int
    xml: bytes
    archimate: bytes | None
    v1: list[Achado]
    v5: list[Achado]
    relatorio: str


class EstadoMensagem(TypedDict, total=False):
    sid: str
    texto: str
    classificacao: Classificacao
    resposta: str
    detalhes: dict[str, Any]


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
        self.grafo_modelo = self._montar_grafo_modelo()
        self.grafo_mensagem = self._montar_grafo_mensagem()
        self.correcoes = RegistroCorrecoes(settings.kb_dir / "archimate" / "propostas")
        self.jobs: dict[str, dict[str, Any]] = {}
        self.eventos: dict[str, list[dict[str, Any]]] = {}
        self._lock_jobs = threading.Lock()

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
        sid, entrada = st["sid"], st["entrada"]
        try:
            interp = interpretar(
                self.llm,
                entrada.id,
                st["lida"],
                self.store.briefing(sid),
                tokens_usados=self.tokens(sid),
                on_usage=self.hook(sid),
                contexto=st.get("contexto", ""),
            )
        except Exception as exc:
            # A entrada fica registrada como falha: não entra no briefing nem no relatório.
            entrada.status = "falhou"
            entrada.observacao = f"Interpretação falhou ({type(exc).__name__}); envie de novo."
            self.store.salvar_entrada(sid, entrada)
            raise
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

    # ------------------------------------------------------------ grafo da conversa

    def _montar_grafo_mensagem(self) -> Any:
        g: Any = StateGraph(EstadoMensagem)
        g.add_node("classificar", self._no_classificar)
        g.add_node("responder", self._no_responder)
        g.add_node("atualizar_briefing", self._no_mensagem_briefing)
        g.add_node("avaliar_alternativa", self._no_alternativa)
        g.add_node("comando", self._no_comando)
        g.add_edge(START, "classificar")
        g.add_conditional_edges(
            "classificar",
            lambda st: {
                "pergunta": "responder",
                "informacao": "atualizar_briefing",
                "correcao": "atualizar_briefing",
                "alternativa": "avaliar_alternativa",
                "comando": "comando",
            }[st["classificacao"].classe],
        )
        for no in ("responder", "atualizar_briefing", "avaliar_alternativa", "comando"):
            g.add_edge(no, END)
        return g.compile()

    def _ultimo_modelo(self, sid: str) -> Modelo | None:
        versoes = self.store.obter(sid).versoes_modelo
        return self.modelo(sid, versoes[-1]) if versoes else None

    def _no_classificar(self, st: EstadoMensagem) -> EstadoMensagem:
        sid = st["sid"]
        c = classificar(
            self.llm,
            st["texto"],
            self.store.briefing(sid),
            tokens_usados=self.tokens(sid),
            on_usage=self.hook(sid),
        )
        log_event(logger, "mensagem.classificada", classe=c.classe, acao=c.acao)
        return {"classificacao": c}

    def _no_responder(self, st: EstadoMensagem) -> EstadoMensagem:
        sid = st["sid"]
        ctx = contexto(self.store.briefing(sid), self._ultimo_modelo(sid), self.vault, st["texto"])
        r = responder(
            self.llm, st["texto"], ctx, tokens_usados=self.tokens(sid), on_usage=self.hook(sid)
        )
        return {"resposta": r.resposta, "detalhes": {"citados": r.citados, "sabe": r.sabe}}

    def _no_mensagem_briefing(self, st: EstadoMensagem) -> EstadoMensagem:
        sid, c = st["sid"], st["classificacao"]
        estado = self.enviar_entrada(sid, texto=st["texto"])
        res = estado["resultado"]
        partes = []
        if res.novos:
            partes.append(f"novos: {', '.join(res.novos)}")
        if res.unidos:
            partes.append(f"atualizados: {', '.join(res.unidos)}")
        if res.superados:
            partes.append(f"superados: {', '.join(res.superados)}")
        if res.conflitos:
            partes.append(f"conflitos: {', '.join(res.conflitos)}")
        texto = (
            "Registrei no briefing (" + "; ".join(partes) + ")."
            if partes
            else "Não encontrei nada novo para o briefing nessa mensagem."
        )
        if self.store.obter(sid).versoes_modelo:
            texto += (
                " O briefing mudou: confirme de novo e gere uma nova versão do modelo "
                "para incorporar a mudança."
            )
        perguntas = estado.get("perguntas", [])
        if perguntas:
            texto += f" Tenho {len(perguntas)} pergunta(s) nova(s)."
        detalhes: dict[str, Any] = {
            "entrada": estado["entrada"].id,
            "resultado": res.model_dump(),
            "perguntas": [p.model_dump(mode="json") for p in perguntas],
        }
        if c.classe == "correcao" and c.tema:
            proposta = self.correcoes.registrar(c.tema, sid, st["texto"])
            if proposta:
                detalhes["proposta"] = proposta.name
                log_event(logger, "proposta.criada", arquivo=proposta.name)
        return {"resposta": texto, "detalhes": detalhes}

    def _no_alternativa(self, st: EstadoMensagem) -> EstadoMensagem:
        sid = st["sid"]
        ctx = contexto(self.store.briefing(sid), self._ultimo_modelo(sid), self.vault, st["texto"])
        a = avaliar_alternativa(
            self.llm, st["texto"], ctx, tokens_usados=self.tokens(sid), on_usage=self.hook(sid)
        )
        return {"resposta": a.markdown(), "detalhes": {"avaliacao": a.model_dump()}}

    def _no_comando(self, st: EstadoMensagem) -> EstadoMensagem:
        sid, acao = st["sid"], st["classificacao"].acao
        if acao == "confirmar_briefing":
            self.confirmar_briefing(sid)
            return {
                "resposta": "Briefing confirmado. Já posso gerar o modelo.",
                "detalhes": {"acao": acao},
            }
        if acao == "gerar_modelo":
            try:
                info = self.iniciar_geracao(sid)
            except BriefingNaoConfirmado as exc:
                return {"resposta": str(exc), "detalhes": {"acao": acao, "erro": True}}
            return {
                "resposta": f"Gerando o modelo {info['modelo']}; acompanhe na aba Modelo.",
                "detalhes": {"acao": acao, **info},
            }
        return {
            "resposta": "Não entendi qual ação executar. Posso confirmar o briefing ou "
            "gerar o modelo.",
            "detalhes": {"acao": acao},
        }

    def mensagem(self, sid: str, texto: str) -> EstadoMensagem:
        """RF-CON-01..06: classifica a mensagem e responde conforme a classe."""
        self.store.obter(sid)
        self.store.registrar_mensagem(sid, "arquiteto", texto)
        token = session_var.set(sid)
        try:
            final: EstadoMensagem = self.grafo_mensagem.invoke({"sid": sid, "texto": texto})
        finally:
            session_var.reset(token)
        self.store.registrar_mensagem(
            sid, "agente", final.get("resposta", ""), classe=final["classificacao"].classe
        )
        return final

    # ------------------------------------------------------------ grafo do modelo

    def _evento(self, st: EstadoModelo, etapa: str, mensagem: str, **extra: Any) -> None:
        ev = {
            "job": st.get("job"),
            "modelo": st.get("mid"),
            "etapa": etapa,
            "mensagem": mensagem,
            "em": datetime.now().astimezone().isoformat(),
            **extra,
        }
        with self._lock_jobs:
            self.eventos.setdefault(st["sid"], []).append(ev)
        self.store.gravar_arquivo(
            st["sid"],
            f"modelos/{st['mid']}/eventos.jsonl",
            "\n".join(
                json.dumps(e, ensure_ascii=False)
                for e in self.eventos[st["sid"]]
                if e.get("modelo") == st["mid"]
            )
            + "\n",
        )
        log_event(logger, "modelo.progresso", etapa=etapa, modelo=st.get("mid"))

    def _montar_grafo_modelo(self) -> Any:
        g: Any = StateGraph(EstadoModelo)
        for nome, fn in (
            ("modelar", self._no_modelar),
            ("validar", self._no_validar),
            ("corrigir", self._no_corrigir),
            ("gerar_visoes", self._no_visoes),
            ("exportar_exchange", self._no_exportar),
            ("converter_archi", self._no_converter),
            ("relatorio", self._no_relatorio),
        ):
            g.add_node(nome, fn)
        g.add_edge(START, "modelar")
        g.add_edge("modelar", "validar")
        g.add_conditional_edges(
            "validar", self._depois_de_validar, {"corrigir": "corrigir", "seguir": "gerar_visoes"}
        )
        g.add_edge("corrigir", "validar")
        g.add_edge("gerar_visoes", "exportar_exchange")
        g.add_edge("exportar_exchange", "converter_archi")
        g.add_edge("converter_archi", "relatorio")
        g.add_edge("relatorio", END)
        return g.compile()

    def _no_modelar(self, st: EstadoModelo) -> EstadoModelo:
        sid = st["sid"]
        self._evento(st, "modelar", "Convertendo o briefing em elementos e relações ArchiMate…")
        sessao = self.store.obter(sid)
        m = modelar(
            self.llm,
            self.store.briefing(sid),
            self.regras,
            self.vault,
            nome=sessao.titulo,
            mid=st["mid"],
            tokens_usados=self.tokens(sid),
            on_usage=self.hook(sid),
        )
        return {"modelo": m, "rodada": 0}

    def _no_validar(self, st: EstadoModelo) -> EstadoModelo:
        b = self.store.briefing(st["sid"])
        achados = validar_modelo(st["modelo"], self.regras, b.ativos())
        erros = [a for a in achados if a.severidade == "erro"]
        self._evento(
            st,
            "validar",
            f"Validação V2–V4 (rodada {st.get('rodada', 0)}): "
            f"{len(erros)} erro(s), {len(achados) - len(erros)} aviso(s).",
            erros=len(erros),
        )
        log_event(
            logger,
            "validacao.resultado",
            rodada=st.get("rodada", 0),
            erros=len(erros),
            avisos=len(achados) - len(erros),
        )
        return {"achados": achados}

    def _depois_de_validar(self, st: EstadoModelo) -> str:
        erros = [a for a in st.get("achados", []) if a.severidade == "erro"]
        if erros and st.get("rodada", 0) < self.settings.max_rodadas_correcao:
            return "corrigir"
        return "seguir"

    def _no_corrigir(self, st: EstadoModelo) -> EstadoModelo:
        sid, rodada = st["sid"], st.get("rodada", 0) + 1
        erros = [a for a in st["achados"] if a.severidade == "erro"]
        self._evento(
            st,
            "corrigir",
            f"Corrigindo {len(erros)} erro(s) (rodada {rodada} de "
            f"{self.settings.max_rodadas_correcao})…",
        )
        m = corrigir(
            self.llm,
            st["modelo"],
            erros,
            self.store.briefing(sid),
            self.regras,
            self.vault,
            tokens_usados=self.tokens(sid),
            on_usage=self.hook(sid),
        )
        return {"modelo": m, "rodada": rodada}

    def _no_visoes(self, st: EstadoModelo) -> EstadoModelo:
        m = st["modelo"]
        m.visoes = gerar_visoes(m, self.regras)
        self._evento(st, "gerar_visoes", f"{len(m.visoes)} visão(ões) geradas.")
        return {"modelo": m}

    def _no_exportar(self, st: EstadoModelo) -> EstadoModelo:
        xml = exportar(st["modelo"])
        v1 = validar_v1(xml, self.regras.xsd_dir)
        self._evento(
            st,
            "exportar_exchange",
            "Exchange Format válido nos XSDs (V1)."
            if not v1
            else f"Exchange Format reprovado nos XSDs (V1): {len(v1)} erro(s).",
        )
        return {"xml": xml, "v1": v1}

    def _no_converter(self, st: EstadoModelo) -> EstadoModelo:
        if st["v1"]:
            v5 = [
                Achado(
                    criterio="V5",
                    regra="NAO-EXECUTADO",
                    severidade="erro",
                    mensagem="Conversão no Archi não executada porque o V1 falhou.",
                )
            ]
            return {"archimate": None, "v5": v5}
        self._evento(st, "converter_archi", "Abrindo o modelo no Archi 5 (tool-archi)…")
        try:
            arquivo, v5 = self.archi.converter(st["xml"])
        except ArchiIndisponivel as exc:
            arquivo, v5 = (
                None,
                [
                    Achado(
                        criterio="V5",
                        regra="ARCHI-INDISPONIVEL",
                        severidade="erro",
                        mensagem=str(exc),
                    )
                ],
            )
        self._evento(
            st,
            "converter_archi",
            "O Archi abriu e salvou o modelo (V5)."
            if not v5
            else "O Archi não conseguiu abrir o modelo (V5).",
        )
        return {"archimate": arquivo, "v5": v5}

    def _no_relatorio(self, st: EstadoModelo) -> EstadoModelo:
        sid, mid, m = st["sid"], st["mid"], st["modelo"]
        briefing = self.store.briefing(sid)
        achados = [*validar_modelo(m, self.regras, briefing.ativos()), *st["v1"], *st["v5"]]
        criterios = {
            c: not any(a.criterio == c and a.severidade == "erro" for a in achados)
            for c in ("V1", "V2", "V3", "V4", "V5")
        }
        m.validacao = Validacao.de_achados(achados, criterios)
        m.rodadas_correcao = st.get("rodada", 0)
        segundos = time.monotonic() - st["inicio"]
        texto = gerar_relatorio(
            m,
            self.regras,
            briefing,
            self.store.entradas(sid),
            self.store.perguntas(sid),
            self.store.uso(sid),
            segundos,
            st.get("rodada", 0),
        )
        base = f"modelos/{mid}"
        self.store.gravar_arquivo(sid, f"{base}/modelo.json", m.model_dump_json(indent=2))
        self.store.gravar_arquivo(sid, f"{base}/modelo.xml", st["xml"])
        if st.get("archimate"):
            self.store.gravar_arquivo(sid, f"{base}/modelo.archimate", st["archimate"] or b"")
        self.store.gravar_arquivo(sid, f"{base}/relatorio.md", texto)
        with self.store.lock(sid):
            sessao = self.store.obter(sid)
            if mid not in sessao.versoes_modelo:
                sessao.versoes_modelo.append(mid)
            sessao.status = "modelo_gerado"
            self.store.salvar(sessao)
        self._evento(
            st,
            "relatorio",
            f"Modelo {mid} {'viável' if m.validacao.viavel else 'não viável'}"
            f" ({len(m.validacao.erros)} erro(s), {len(m.validacao.avisos)} aviso(s)).",
            viavel=m.validacao.viavel,
        )
        log_event(
            logger,
            "modelo.gerado",
            modelo=mid,
            viavel=m.validacao.viavel,
            rodadas=st.get("rodada", 0),
            segundos=round(segundos, 1),
        )
        return {"modelo": m, "relatorio": texto}

    # ------------------------------------------------------------ geração de modelos

    def _preparar(self, sid: str) -> tuple[str, str]:
        if not self.store.briefing(sid).confirmado:
            raise BriefingNaoConfirmado(
                "Confirme o briefing antes de gerar o modelo (mudanças depois da confirmação "
                "exigem nova confirmação)."
            )
        with self.store.lock(sid):
            sessao = self.store.obter(sid)
            n = len(sessao.versoes_modelo) + 1
            pasta = self.store.pasta_sessao(sid) / "modelos"
            while (pasta / f"M-{n:03d}").exists():
                n += 1
            mid = f"M-{n:03d}"
            self.store.gravar_arquivo(sid, f"modelos/{mid}/.reservado", "")
        return mid, f"J-{uuid.uuid4().hex[:8]}"

    def gerar_modelo(self, sid: str, mid: str | None = None, job: str | None = None) -> Modelo:
        """Gera o modelo de forma síncrona (usado pela API em segundo plano e pela avaliação)."""
        if mid is None or job is None:
            mid, job = self._preparar(sid)
        token = session_var.set(sid)
        try:
            st: EstadoModelo = {"sid": sid, "mid": mid, "job": job, "inicio": time.monotonic()}
            final: EstadoModelo = self.grafo_modelo.invoke(st)
            return final["modelo"]
        finally:
            session_var.reset(token)

    def iniciar_geracao(self, sid: str) -> dict[str, Any]:
        mid, job = self._preparar(sid)
        info = {"job_id": job, "modelo": mid, "sessao": sid, "status": "em_andamento"}
        with self._lock_jobs:
            self.jobs[job] = info

        def rodar() -> None:
            try:
                self.gerar_modelo(sid, mid, job)
                info["status"] = "concluido"
            except Exception as exc:
                info["status"], info["erro"] = "falhou", f"{type(exc).__name__}: {exc}"[:500]
                st: EstadoModelo = {"sid": sid, "mid": mid, "job": job}
                self._evento(st, "erro", f"A geração falhou: {info['erro']}")
                logger.exception("modelo.falhou")

        threading.Thread(target=rodar, name=f"modelo-{job}", daemon=True).start()
        return dict(info)

    def modelo(self, sid: str, mid: str) -> Modelo:
        arq = self.store.pasta_sessao(sid) / "modelos" / mid / "modelo.json"
        if "/" in mid or ".." in mid or not arq.exists():
            raise KeyError(mid)
        return Modelo.model_validate_json(arq.read_text(encoding="utf-8"))

    def arquivo_modelo(self, sid: str, mid: str, tipo: str) -> tuple[bytes, str, str]:
        nomes = {
            "exchange": ("modelo.xml", "application/xml", "xml"),
            "archimate": ("modelo.archimate", "application/xml", "archimate"),
            "relatorio": ("relatorio.md", "text/markdown; charset=utf-8", "md"),
        }
        if tipo not in nomes or "/" in mid or ".." in mid:
            raise KeyError(tipo)
        nome, mime, ext = nomes[tipo]
        arq = self.store.pasta_sessao(sid) / "modelos" / mid / nome
        if not arq.exists():
            raise KeyError(tipo)
        return arq.read_bytes(), mime, f"{sid}-{mid}.{ext}"

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
