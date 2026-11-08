from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from archagent.agents.archimate.api import create_app
from archagent.agents.archimate.conversa import AvaliacaoAlternativa, RegistroCorrecoes, slug
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.agents.archimate.vault import ler_nota
from archagent.core.llm import LLM, ScriptedBackend

from .conftest import KB
from .test_api_health import ArchiFalso

INTERP = {
    "itens": [
        {
            "tipo": "sistema",
            "nome": "Portal Web",
            "local": "linha 1",
            "trecho": "Portal Web",
            "confianca": "alta",
        },
        {
            "tipo": "infraestrutura",
            "nome": "PostgreSQL",
            "local": "linha 1",
            "trecho": "PostgreSQL",
            "confianca": "alta",
        },
    ]
}


@pytest.fixture
def kb(tmp_path: Path) -> Path:
    destino = tmp_path / "kb"
    shutil.copytree(KB, destino)
    return destino


def cliente(tmp: Path, kb: Path) -> tuple[TestClient, ScriptedBackend]:
    s = ArchimateSettings(_env_file=None, kb_dir=kb, sessions_dir=tmp / "s")  # type: ignore[call-arg]
    b = ScriptedBackend()
    return TestClient(create_app(s, LLM(b, s), ArchiFalso())), b  # type: ignore[arg-type]


def nova(c: TestClient, b: ScriptedBackend) -> str:
    sid: str = c.post("/sessions", json={"titulo": "x"}).json()["sessao"]["id"]
    b.respostas["interpretar"] = []
    b.add("interpretar", INTERP)
    c.post(f"/sessions/{sid}/inputs", data={"texto": "O Portal Web grava no PostgreSQL."})
    return sid


def msg(c: TestClient, sid: str, texto: str) -> dict:  # type: ignore[type-arg]
    r = c.post(f"/sessions/{sid}/messages", json={"texto": texto})
    assert r.status_code == 200, r.text
    dados: dict = r.json()  # type: ignore[type-arg]
    return dados


def test_pergunta_responde_com_citacao(tmp_path: Path, kb: Path) -> None:
    c, b = cliente(tmp_path, kb)
    sid = nova(c, b)
    b.add("classificar", {"classe": "pergunta"})
    b.add(
        "responder",
        {
            "resposta": "O Portal Web (B-001) grava no PostgreSQL (B-002).",
            "citados": ["B-001", "B-002"],
            "sabe": True,
        },
    )
    r = msg(c, sid, "Onde o portal grava?")
    assert r["classe"] == "pergunta" and "B-001" in r["resposta"]
    contexto_enviado = b.chamadas[-1][1][1]["content"]
    assert "B-002 [infraestrutura" in contexto_enviado
    conversa = c.get(f"/sessions/{sid}").json()["conversa"]
    assert [m["papel"] for m in conversa[-2:]] == ["arquiteto", "agente"]


def test_informacao_vira_item(tmp_path: Path, kb: Path) -> None:
    c, b = cliente(tmp_path, kb)
    sid = nova(c, b)
    b.add("classificar", {"classe": "informacao"})
    b.respostas["interpretar"] = []
    b.add(
        "interpretar",
        {
            "itens": [
                {"tipo": "sistema", "nome": "SendGrid", "local": "linha 1", "trecho": "SendGrid"}
            ]
        },
    )
    r = msg(c, sid, "O portal manda e-mails pelo SendGrid.")
    assert r["classe"] == "informacao"
    assert r["detalhes"]["resultado"]["novos"] == ["B-003"]


def test_correcao_marca_superado(tmp_path: Path, kb: Path) -> None:
    c, b = cliente(tmp_path, kb)
    sid = nova(c, b)
    b.add("classificar", {"classe": "correcao", "tema": "Banco de dados"})
    b.respostas["interpretar"] = []
    b.add(
        "interpretar",
        {
            "itens": [
                {
                    "tipo": "infraestrutura",
                    "nome": "Oracle",
                    "local": "linha 1",
                    "trecho": "Oracle",
                    "substitui": "B-002",
                }
            ]
        },
    )
    r = msg(c, sid, "Na verdade o banco é Oracle.")
    assert r["detalhes"]["resultado"]["superados"] == ["B-002"]
    itens = {i["id"]: i for i in c.get(f"/sessions/{sid}/briefing").json()["itens"]}
    assert itens["B-002"]["status"] == "superado"


def test_alternativa_tem_pros_contras_impacto_conflitos(tmp_path: Path, kb: Path) -> None:
    c, b = cliente(tmp_path, kb)
    sid = nova(c, b)
    b.add("classificar", {"classe": "alternativa"})
    b.add(
        "avaliar_alternativa",
        AvaliacaoAlternativa(
            pros=["Esquema flexível"],
            contras=["Perde transações"],
            impacto_no_modelo="Troca o SystemSoftware PostgreSQL por MongoDB",
            conflitos=["B-002 PostgreSQL"],
            recomendacao="Só se o esquema mudar muito.",
        ),
    )
    r = msg(c, sid, "E se usássemos MongoDB?")
    assert r["classe"] == "alternativa"
    for trecho in ("**Prós**", "**Contras**", "**Impacto no modelo**", "**Conflitos", "B-002"):
        assert trecho in r["resposta"]
    # alternativa não muda o briefing
    assert len(c.get(f"/sessions/{sid}/briefing").json()["itens"]) == 2


def test_comandos(tmp_path: Path, kb: Path) -> None:
    c, b = cliente(tmp_path, kb)
    sid = nova(c, b)
    b.add("classificar", {"classe": "comando", "acao": "gerar_modelo"})
    r = msg(c, sid, "gera o modelo")
    assert r["detalhes"]["erro"] is True and "Confirme" in r["resposta"]
    b.respostas["classificar"] = []
    b.add("classificar", {"classe": "comando", "acao": "confirmar_briefing"})
    assert "confirmado" in msg(c, sid, "pode confirmar")["resposta"]
    assert c.get(f"/sessions/{sid}").json()["sessao"]["status"] == "briefing_confirmado"
    b.respostas["classificar"] = []
    b.add("classificar", {"classe": "comando", "acao": "nenhuma"})
    assert "Não entendi" in msg(c, sid, "faz aquilo")["resposta"]


def test_mensagem_vazia_e_sessao_inexistente(tmp_path: Path, kb: Path) -> None:
    c, _ = cliente(tmp_path, kb)
    assert c.post("/sessions/S-x/messages", json={"texto": "oi"}).status_code == 404
    sid = c.post("/sessions", json={"titulo": "x"}).json()["sessao"]["id"]
    assert c.post(f"/sessions/{sid}/messages", json={"texto": "  "}).status_code == 400


def test_proposta_depois_de_3_sessoes(tmp_path: Path) -> None:
    reg = RegistroCorrecoes(tmp_path / "propostas")
    assert reg.registrar("Banco como software", "S-1", "banco é SystemSoftware") is None
    assert reg.registrar("banco-como-software", "S-1", "de novo") is None
    assert reg.registrar("banco como software!", "S-2", "outra") is None
    arq = reg.registrar("banco-como-software", "S-3", "terceira")
    assert arq is not None and arq.name.endswith("-banco-como-software.md")
    texto = arq.read_text()
    for secao in ("## Correção observada", "## Sessões", "## Nota proposta"):
        assert secao in texto
    assert "S-1, S-2, S-3" in texto
    # a nota proposta segue o formato do vault (spec §10.3)
    bloco = texto.split("```markdown\n", 1)[1].split("```", 1)[0]
    nota = tmp_path / "convencao-banco-como-software.md"
    nota.write_text(bloco)
    assert ler_nota(nota).status == "rascunho"
    # não repete a proposta
    assert reg.registrar("banco-como-software", "S-4", "quarta") is None


def test_slug() -> None:
    assert slug("Processo no Infinitivo!") == "processo-no-infinitivo"
