"""Interface Streamlit do ArchAgent (spec §15).

Não contém lógica de agente: tudo passa pela API do agente (spec §13).
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

AGENT_URL = os.environ.get("AGENT_ARCHIMATE_URL", "http://agent-archimate:8000")

st.set_page_config(page_title="ArchAgent", page_icon="🏛️", layout="wide")
st.title("ArchAgent")

with st.sidebar:
    st.caption(
        "As entradas enviadas aqui vão para a API do DashScope "
        "(Alibaba Cloud, Singapura). Não envie dados sensíveis."
    )

try:
    saude = httpx.get(f"{AGENT_URL}/health", timeout=5).json()
    st.success(f"Agente ArchiMate: {saude.get('status', '?')}")
    st.json(saude)
except httpx.HTTPError as exc:
    st.error(f"Agente ArchiMate indisponível em {AGENT_URL}: {exc}")
