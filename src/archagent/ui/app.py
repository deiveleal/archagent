"""Interface Streamlit do ArchAgent (spec §15).

Não contém lógica de agente: tudo passa pela API do agente (spec §13).
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from typing import Any

import streamlit as st

from archagent.core.cliente import AgenteCliente, ErroApi

AGENT_URL = os.environ.get("AGENT_ARCHIMATE_URL", "http://agent-archimate:8000")
TIPOS_ARQUIVO = ["txt", "md", "vtt", "srt", "docx", "drawio", "xml", "png", "jpg", "jpeg"]
ROTULOS_TIPO = {
    "ator": "Atores",
    "processo": "Processos",
    "servico": "Serviços",
    "sistema": "Sistemas",
    "interface": "Interfaces",
    "dado": "Dados",
    "infraestrutura": "Infraestrutura",
    "ligacao": "Ligações",
    "requisito": "Requisitos",
    "decisao": "Decisões",
    "hipotese": "Hipóteses",
    "pendencia": "Pendências",
    "conflito": "Conflitos",
}
CAMADA = {
    "Business": "Negócio",
    "Contract": "Negócio",
    "Representation": "Negócio",
    "Product": "Negócio",
    "Application": "Aplicação",
    "DataObject": "Aplicação",
}

st.set_page_config(page_title="ArchAgent", page_icon="🏛️", layout="wide")
api = AgenteCliente(AGENT_URL)


def camada(tipo: str) -> str:
    for prefixo, nome in CAMADA.items():
        if tipo.startswith(prefixo):
            return nome
    return "Tecnologia"


def mostrar_erro(exc: ErroApi) -> None:
    st.error(f"{exc.mensagem} ({exc.codigo})")


def resumo_entrada(r: dict[str, Any]) -> str:
    res = r.get("resultado", {})
    e = r.get("entrada", {})
    partes = [f"{e.get('id', '?')} interpretada: {len(res.get('novos', []))} item(ns) novo(s)"]
    if res.get("unidos"):
        partes.append(f"{len(res['unidos'])} unido(s) a itens existentes")
    if res.get("superados"):
        partes.append(f"{len(res['superados'])} superado(s)")
    if res.get("conflitos"):
        partes.append(f"{len(res['conflitos'])} conflito(s)")
    texto = ", ".join(partes) + "."
    if r.get("perguntas"):
        texto += f" Tenho {len(r['perguntas'])} pergunta(s) na aba **Perguntas**."
    return texto


# ------------------------------------------------------------------ barra lateral

with st.sidebar:
    st.title("🏛️ ArchAgent")
    st.caption(
        "⚠️ As entradas enviadas aqui vão para a API do DashScope (Alibaba Cloud, "
        "Singapura). Não envie dados sensíveis."
    )
    try:
        saude = api.saude()
        archi = saude.get("tool_archi", {}).get("status")
        st.caption(f"Agente ok · Archi {'ok' if archi == 'ok' else 'indisponível'}")
    except ErroApi as exc:
        st.error(f"Agente indisponível em {AGENT_URL}: {exc.mensagem}")
        st.stop()

    with st.form("nova", clear_on_submit=True):
        titulo = st.text_input("Nova sessão", placeholder="Ex.: Portal de pedidos")
        if st.form_submit_button("Criar sessão", width="stretch") and titulo.strip():
            nova = api.criar_sessao(titulo)
            st.session_state["sid"] = nova["id"]

    sessoes = api.sessoes()
    if not sessoes:
        st.info("Crie uma sessão para começar.")
        st.stop()
    ids = [s["id"] for s in sessoes]
    atual = st.session_state.get("sid", ids[0])
    sid = st.selectbox(
        "Sessões",
        ids,
        index=ids.index(atual) if atual in ids else 0,
        format_func=lambda i: f"{next(s['titulo'] for s in sessoes if s['id'] == i)} · {i}",
    )
    st.session_state["sid"] = sid

    uso = api.uso(sid)
    if uso["limite"]:
        st.progress(
            min(uso["total"] / uso["limite"], 1.0),
            text=f"Tokens: {uso['total']:,} de {uso['limite']:,}".replace(",", "."),
        )
    if uso["bloqueado"]:
        st.error("Limite de tokens da sessão atingido: novas chamadas ao LLM estão bloqueadas.")
    elif uso["aviso"]:
        st.warning("A sessão passou de 80% do limite de tokens.")

detalhe = api.sessao(sid)
sessao = detalhe["sessao"]
st.header(sessao["titulo"])
st.caption(f"{sessao['id']} · status: {sessao['status'].replace('_', ' ')}")

aba_conversa, aba_entradas, aba_briefing, aba_perguntas, aba_modelo = st.tabs(
    ["💬 Conversa", "📥 Entradas", "📋 Briefing", "❓ Perguntas", "🧩 Modelo"]
)

# ------------------------------------------------------------------ conversa

with aba_conversa:
    for msg in detalhe.get("conversa", []):
        papel = "user" if msg["papel"] == "arquiteto" else "assistant"
        with st.chat_message(papel):
            st.markdown(msg["texto"])
    envio = st.chat_input(
        "Escreva uma mensagem ou anexe transcrições e desenhos…",
        accept_file="multiple",
        file_type=TIPOS_ARQUIVO,
    )
    if envio:
        try:
            for arq in envio.files:
                with st.spinner(f"Lendo {arq.name}…"):
                    r = api.enviar_arquivo(sid, arq.name, arq.getvalue())
                st.success(resumo_entrada(r))
            if envio.text:
                with st.spinner("Pensando…"):
                    r = api.enviar_mensagem(sid, envio.text)
                if "resposta" not in r:
                    st.success(resumo_entrada(r))
            st.rerun()
        except ErroApi as exc:
            mostrar_erro(exc)

# ------------------------------------------------------------------ entradas

with aba_entradas:
    entradas = detalhe.get("entradas", [])
    if not entradas:
        st.info("Nenhuma entrada ainda. Envie arquivos ou mensagens na aba Conversa.")
    for e in entradas:
        icone = {"interpretada": "✅", "falhou": "❌"}.get(e["status"], "⏳")
        st.markdown(
            f"{icone} **{e['id']}** — {e.get('nome_arquivo') or 'mensagem'} "
            f"· {e['tipo']} ({e['formato']}) · {e['tamanho_bytes']} bytes"
        )
        if e.get("observacao"):
            st.caption(e["observacao"])

# ------------------------------------------------------------------ briefing

with aba_briefing:
    dados = api.briefing(sid)
    itens = dados["itens"]
    ativos = [i for i in itens if i["status"] == "ativo"]
    col1, col2 = st.columns([3, 1])
    col1.markdown(
        f"**{len(ativos)}** itens ativos · "
        + ("✅ confirmado" if dados["confirmado_em"] else "não confirmado")
    )
    if col2.button(
        "Confirmar briefing",
        disabled=not ativos or bool(dados["confirmado_em"]),
        width="stretch",
    ):
        api.confirmar(sid)
        st.rerun()
    abertos = [i for i in ativos if i["tipo"] in ("conflito", "pendencia")]
    if abertos:
        st.warning("Em aberto: " + "; ".join(f"{i['id']} {i['nome']}" for i in abertos))
    por_tipo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for i in itens:
        por_tipo[i["tipo"]].append(i)
    for tipo, rotulo in ROTULOS_TIPO.items():
        lista = por_tipo.get(tipo)
        if not lista:
            continue
        with st.expander(
            f"{rotulo} ({sum(i['status'] == 'ativo' for i in lista)})",
            expanded=tipo in ("conflito", "pendencia"),
        ):
            st.dataframe(
                [
                    {
                        "id": i["id"],
                        "nome": i["nome"],
                        "confiança": i["confianca"],
                        "status": i["status"]
                        + (f" → {i['superado_por']}" if i.get("superado_por") else ""),
                        "origem": "; ".join(
                            f"{o['entrada']} {o['local']}".strip() for o in i["origens"]
                        ),
                        "descrição": i.get("descricao", ""),
                    }
                    for i in lista
                ],
                width="stretch",
                hide_index=True,
            )

# ------------------------------------------------------------------ perguntas

with aba_perguntas:
    perguntas = api.perguntas(sid)
    if not perguntas:
        st.info("Nenhuma pergunta pendente.")
    for p in perguntas:
        with st.form(f"q-{p['id']}"):
            st.markdown(f"**{p['id']}** · sobre {p['item']} · impacto {p['impacto']}")
            st.markdown(p["texto"])
            resposta = st.text_input("Resposta", key=f"r-{p['id']}")
            c1, c2 = st.columns(2)
            responder = c1.form_submit_button("Responder", width="stretch")
            pular = c2.form_submit_button("Pular", width="stretch")
            if responder or pular:
                try:
                    with st.spinner("Atualizando o briefing…"):
                        api.responder(sid, p["id"], resposta or None, pular and not responder)
                    st.rerun()
                except ErroApi as exc:
                    mostrar_erro(exc)

# ------------------------------------------------------------------ modelo

with aba_modelo:
    confirmado = bool(api.briefing(sid)["confirmado_em"])
    if not confirmado:
        st.info("Confirme o briefing para gerar o modelo.")
    if st.button("Gerar modelo", type="primary", disabled=not confirmado):
        try:
            job = api.gerar_modelo(sid)
            with st.status(f"Gerando {job['modelo']}…", expanded=True) as status:
                for ev in api.eventos(sid):
                    if ev.get("modelo") == job["modelo"]:
                        st.write(ev["mensagem"])
                status.update(label=f"{job['modelo']} pronto", state="complete")
            st.rerun()
        except ErroApi as exc:
            mostrar_erro(exc)

    modelos = api.modelos(sid)
    if modelos:
        ids_m = [m["id"] for m in modelos][::-1]
        mid = st.selectbox(
            "Versão",
            ids_m,
            format_func=lambda m: (
                f"{m} · "
                + ("viável" if next(x for x in modelos if x["id"] == m)["viavel"] else "não viável")
            ),
        )
        m = api.modelo(sid, mid)
        v = m["validacao"]
        (st.success if v["viavel"] else st.error)(
            f"{'Viável' if v['viavel'] else 'Não viável'} · {len(m['elementos'])} elementos · "
            f"{len(m['relacoes'])} relações · {len(m['visoes'])} visões · "
            f"{m.get('rodadas_correcao', 0)} rodada(s) de correção"
        )
        cols = st.columns(5)
        for col, c in zip(cols, ("V1", "V2", "V3", "V4", "V5"), strict=True):
            col.metric(c, "ok" if v["criterios"].get(c) else "falhou")
        contagem = Counter(camada(e["tipo"]) for e in m["elementos"])
        st.markdown(
            " · ".join(
                f"**{k}**: {contagem.get(k, 0)}" for k in ("Negócio", "Aplicação", "Tecnologia")
            )
        )
        d1, d2, d3 = st.columns(3)
        for col, tipo, nome, rot in (
            (d1, "archimate", f"{sid}-{mid}.archimate", ".archimate"),
            (d2, "exchange", f"{sid}-{mid}.xml", "Exchange Format"),
            (d3, "relatorio", f"{sid}-{mid}.md", "Relatório"),
        ):
            try:
                col.download_button(
                    f"Baixar {rot}",
                    api.arquivo(sid, mid, tipo),
                    file_name=nome,
                    width="stretch",
                )
            except ErroApi:
                col.button(f"{rot} indisponível", disabled=True, width="stretch")
        if v["erros"]:
            with st.expander(f"Erros ({len(v['erros'])})", expanded=True):
                for a in v["erros"]:
                    st.markdown(f"- **{a['criterio']} {a['regra']}**: {a['mensagem']}")
        if v["avisos"]:
            with st.expander(f"Avisos ({len(v['avisos'])})"):
                for a in v["avisos"]:
                    st.markdown(f"- **{a['criterio']} {a['regra']}**: {a['mensagem']}")
        with st.expander("Relatório de viabilidade"):
            st.markdown(api.arquivo(sid, mid, "relatorio").decode("utf-8"))
