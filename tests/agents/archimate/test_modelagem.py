from __future__ import annotations

from pathlib import Path

import pytest

from archagent.agents.archimate.modelagem import (
    ElementoLLM,
    ModeloLLM,
    RelacaoLLM,
    guia_de_tipos,
    mensagens_modelagem,
    para_llm,
    para_modelo,
)
from archagent.agents.archimate.rules import Regras
from archagent.agents.archimate.service import ArchimateService, BriefingNaoConfirmado
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.agents.archimate.vault import Vault
from archagent.core.briefing import Briefing, ItemBriefing, Origem
from archagent.core.llm import LLM, ScriptedBackend
from archagent.core.sessions import SessionStore

from .conftest import KB
from .test_api_health import ArchiFalso


def briefing() -> Briefing:
    b = Briefing()
    for tipo, nome in (
        ("ator", "Cliente"),
        ("processo", "Registrar pedido"),
        ("sistema", "API de Pedidos"),
        ("pendencia", "Onde roda?"),
    ):
        b.adicionar(ItemBriefing(tipo=tipo, nome=nome, origens=[Origem(entrada="E-001")]))  # type: ignore[arg-type]
    b.adicionar(ItemBriefing(tipo="ligacao", nome="API → Registrar", de="B-003", para="B-002"))
    return b


def bom() -> ModeloLLM:
    return ModeloLLM(
        elementos=[
            ElementoLLM(ref="e1", tipo="BusinessActor", nome="Cliente", origens=["B-001"]),
            ElementoLLM(
                ref="e2", tipo="BusinessProcess", nome="Registrar pedido", origens=["B-002"]
            ),
            ElementoLLM(
                ref="e3", tipo="ApplicationComponent", nome="API de Pedidos", origens=["B-003"]
            ),
        ],
        relacoes=[
            RelacaoLLM(tipo="Assignment", origem="e1", destino="e2", origens=["B-002"]),
            RelacaoLLM(tipo="Serving", origem="e3", destino="e2", origens=["B-005"]),
        ],
    )


def ruim() -> ModeloLLM:
    m = bom()
    m.relacoes[0] = RelacaoLLM(tipo="Assignment", origem="e2", destino="e1", origens=["B-002"])
    return m


def test_guia_usa_as_fichas(regras: Regras) -> None:
    guia = guia_de_tipos(regras, Vault.carregar(KB / "archimate" / "vault", True))
    assert "- ApplicationComponent (Componente de aplicação): use quando" in guia
    assert "[[" not in guia
    msgs = mensagens_modelagem(briefing(), regras, Vault.carregar(KB / "archimate" / "vault", True))
    assert "Padrões, anti-padrões" in msgs[0]["content"]
    assert "B-003 [sistema, media] API de Pedidos" in msgs[1]["content"]


def test_para_modelo_ids_e_premissas() -> None:
    llm = bom()
    llm.elementos.append(ElementoLLM(ref="e4", tipo="Node", nome="Servidor", origens=["B-004"]))
    llm.elementos.append(ElementoLLM(ref="e5", tipo="Node", nome="Outro"))
    m = para_modelo(llm, briefing(), "Portal")
    assert all(e.id.startswith("id-") for e in m.elementos)
    assert m.relacoes[0].origem == m.elementos[0].id
    servidor, outro = m.elementos[3], m.elementos[4]
    assert servidor.premissa and "pendência" in servidor.motivo_premissa  # RF-MOD-06
    assert outro.premissa and "completar" in outro.motivo_premissa
    volta = para_llm(m)
    assert volta.relacoes[0].origem == "e1"


def _svc(tmp: Path, regras: Regras, b: ScriptedBackend) -> tuple[ArchimateService, str]:
    s = ArchimateSettings(_env_file=None, kb_dir=KB, sessions_dir=tmp)  # type: ignore[call-arg]
    store = SessionStore(tmp)
    svc = ArchimateService(
        s, LLM(b, s), store, regras, Vault.carregar(KB / "archimate" / "vault", True), ArchiFalso()
    )  # type: ignore[arg-type]
    sid = store.criar("Portal").id
    br = briefing()
    br.confirmar()
    store.salvar_briefing(sid, br)
    return svc, sid


def test_modelo_viavel_sem_correcao(tmp_path: Path, regras: Regras) -> None:
    b = ScriptedBackend()
    b.add("modelar", bom())
    svc, sid = _svc(tmp_path, regras, b)
    m = svc.gerar_modelo(sid)
    assert m.validacao.viavel, m.validacao.erros
    assert m.validacao.criterios == {"V1": True, "V2": True, "V3": True, "V4": True, "V5": True}
    assert [no for no, _ in b.chamadas] == ["modelar"]
    pasta = svc.store.pasta_sessao(sid) / "modelos" / "M-001"
    assert {p.name for p in pasta.iterdir()} >= {
        "modelo.json",
        "modelo.xml",
        "modelo.archimate",
        "relatorio.md",
    }
    rel = (pasta / "relatorio.md").read_text()
    assert "**Viável**" in rel and "B-003 API de Pedidos" in rel
    assert svc.store.obter(sid).status == "modelo_gerado"
    assert svc.store.obter(sid).versoes_modelo == ["M-001"]


def test_ciclo_de_correcao(tmp_path: Path, regras: Regras) -> None:
    b = ScriptedBackend()
    b.add("modelar", ruim())
    b.add("corrigir", bom())
    svc, sid = _svc(tmp_path, regras, b)
    m = svc.gerar_modelo(sid)
    assert m.validacao.viavel
    nos = [no for no, _ in b.chamadas]
    assert nos == ["modelar", "corrigir"]
    pedido = b.chamadas[1][1][-1]["content"]
    assert "REL-PERMITIDA" in pedido and "invertida" in pedido


def test_correcao_para_na_terceira_rodada(tmp_path: Path, regras: Regras) -> None:
    b = ScriptedBackend()
    b.add("modelar", ruim())
    b.add("corrigir", ruim())
    svc, sid = _svc(tmp_path, regras, b)
    m = svc.gerar_modelo(sid)
    assert [no for no, _ in b.chamadas].count("corrigir") == 3
    assert not m.validacao.viavel
    assert any(e.regra == "REL-PERMITIDA" for e in m.validacao.erros)
    rel = (svc.store.pasta_sessao(sid) / "modelos" / "M-001" / "relatorio.md").read_text()
    assert "**Não viável**" in rel and "3 rodada(s)" in rel


def test_sem_confirmacao_nao_modela(tmp_path: Path, regras: Regras) -> None:
    svc, sid = _svc(tmp_path, regras, ScriptedBackend())
    br = svc.store.briefing(sid)
    br.adicionar(ItemBriefing(tipo="ator", nome="Gerente"))
    svc.store.salvar_briefing(sid, br)
    with pytest.raises(BriefingNaoConfirmado):
        svc.gerar_modelo(sid)


def test_archi_fora_reprova_v5(tmp_path: Path, regras: Regras) -> None:
    b = ScriptedBackend()
    b.add("modelar", bom())
    svc, sid = _svc(tmp_path, regras, b)
    svc.archi = ArchiFalso(ok=False)  # type: ignore[assignment]
    m = svc.gerar_modelo(sid)
    assert m.validacao.criterios["V5"] is False
    assert not m.validacao.viavel


def test_relatorio_separa_entradas_nao_usadas(regras: Regras) -> None:
    from archagent.agents.archimate.relatorio import gerar_relatorio
    from archagent.core.briefing import Briefing
    from archagent.core.sessions import Entrada, Uso

    from .conftest import modelo_portal

    entradas = [
        Entrada(id="E-001", tipo="transcricao", formato="txt", nome_arquivo="a.txt",
                status="falhou", observacao="Interpretação falhou (LLMError); envie de novo."),
        Entrada(id="E-002", tipo="transcricao", formato="txt", nome_arquivo="a.txt",
                status="interpretada"),
    ]  # fmt: skip
    rel = gerar_relatorio(modelo_portal(), regras, Briefing(), entradas, [], Uso(), 1.0, 0)
    usadas, _, resto = rel.partition("Não usadas:")
    assert "E-002" in usadas and "E-001" not in usadas
    assert "E-001 — a.txt (falhou: Interpretação falhou" in resto
