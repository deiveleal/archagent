from __future__ import annotations

from pathlib import Path

import pytest

from archagent.core.briefing import Briefing, ItemBriefing, Origem, Pergunta, normalizar_nome
from archagent.core.sessions import (
    Entrada,
    LimiteDeEntradas,
    SessaoNaoEncontrada,
    SessionStore,
)


def item(tipo: str, nome: str, entrada: str = "E-001", **kw: object) -> ItemBriefing:
    return ItemBriefing(tipo=tipo, nome=nome, origens=[Origem(entrada=entrada)], **kw)  # type: ignore[arg-type]


def test_normalizar_nome() -> None:
    assert normalizar_nome("  API de Pedidos! ") == normalizar_nome("api de pedidos")
    assert normalizar_nome("Serviço") == "servico"


def test_uniao_de_itens_repetidos() -> None:
    b = Briefing()
    a = b.adicionar(item("sistema", "API de Pedidos", confianca="media"))
    c = b.adicionar(item("sistema", "api de pedidos", "E-002", confianca="alta"))
    assert a.id == c.id == "B-001"
    assert [o.entrada for o in a.origens] == ["E-001", "E-002"]
    assert a.confianca == "alta"
    assert len(b.itens) == 1


def test_mesmo_nome_tipos_diferentes_nao_une() -> None:
    b = Briefing()
    b.adicionar(item("sistema", "Pedido"))
    b.adicionar(item("dado", "Pedido"))
    assert len(b.itens) == 2


def test_conflito_liga_os_itens() -> None:
    b = Briefing()
    x = b.adicionar(item("decisao", "Banco PostgreSQL"))
    y = b.adicionar(item("decisao", "Banco Oracle"))
    c = b.registrar_conflito([x.id, y.id], "Duas escolhas de banco")
    assert c.tipo == "conflito"
    assert c.itens == [x.id, y.id]
    assert c.id in x.relacionados
    assert c in b.para_esclarecer()


def test_correcao_marca_superado_e_reaponta_ligacoes() -> None:
    b = Briefing()
    velho = b.adicionar(item("infraestrutura", "MySQL"))
    api = b.adicionar(item("sistema", "API"))
    lig = b.adicionar(item("ligacao", "API → MySQL", de=api.id, para=velho.id))
    novo = b.corrigir(velho.id, item("infraestrutura", "PostgreSQL", "E-002"))
    assert velho.status == "superado"
    assert velho.superado_por == novo.id
    assert velho.id in novo.relacionados
    assert lig.para == novo.id
    assert b.item(velho.id) is not None  # não apaga


def test_corrigir_item_inexistente() -> None:
    with pytest.raises(KeyError):
        Briefing().corrigir("B-999", item("ator", "X"))


def test_mudanca_apos_confirmacao_desfaz() -> None:
    b = Briefing()
    b.adicionar(item("ator", "Cliente"))
    b.confirmar()
    assert b.confirmado
    b.adicionar(item("ator", "Gerente"))
    assert not b.confirmado
    b.confirmar()
    b.descartar("B-001")
    assert not b.confirmado


def test_filtrar_e_resumo() -> None:
    b = Briefing()
    b.adicionar(item("ator", "Cliente"))
    b.adicionar(item("pendencia", "Onde roda?", confianca="baixa"))
    assert [i.id for i in b.filtrar(tipo="ator")] == ["B-001"]
    assert "B-002 [pendencia, baixa] Onde roda?" in b.resumo()


# ------------------------------------------------------------------ sessões


def test_sessao_persistida(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    s = store.criar("Portal")
    assert s.id.startswith("S-") and s.id.endswith("-0001")
    assert store.criar("Outra").id.endswith("-0002")
    e = store.adicionar_entrada(s.id, Entrada(id="", tipo="texto", formato="texto"), b"oi", "txt")
    assert e.id == "E-001"
    assert store.original(s.id, "E-001") == b"oi"
    b = Briefing()
    b.adicionar(item("ator", "Cliente"))
    b.confirmar()
    store.salvar_briefing(s.id, b)
    store.salvar_perguntas(s.id, [Pergunta(id="Q-001", item="B-001", texto="?")])
    store.registrar_mensagem(s.id, "arquiteto", "olá")
    store.registrar_uso(s.id, "interpretar", 150)
    # "reinício": um novo store lê tudo do disco
    novo = SessionStore(tmp_path)
    s2 = novo.obter(s.id)
    assert s2.status == "briefing_confirmado"
    assert s2.entradas == ["E-001"]
    assert s2.tokens_usados == 150
    assert novo.briefing(s.id).itens[0].nome == "Cliente"
    assert novo.perguntas(s.id)[0].id == "Q-001"
    assert novo.conversa(s.id)[0]["texto"] == "olá"
    assert novo.uso(s.id).por_no == {"interpretar": 150}
    assert [x.id for x in novo.listar()] == [f"{s.id[:-1]}2", s.id]


def test_sessao_inexistente_e_caminho_malicioso(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    for sid in ("S-nada", "../x", "S-1/../../x"):
        with pytest.raises(SessaoNaoEncontrada):
            store.obter(sid)
    s = store.criar("x")
    with pytest.raises(ValueError, match="fora"):
        store.gravar_arquivo(s.id, "../../fora.txt", "x")


def test_limite_de_entradas(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    s = store.criar("x")
    for _ in range(20):
        store.adicionar_entrada(s.id, Entrada(id="", tipo="texto", formato="texto"), b"a", "txt")
    with pytest.raises(LimiteDeEntradas):
        store.adicionar_entrada(s.id, Entrada(id="", tipo="texto", formato="texto"), b"a", "txt")


def test_confirmacao_desfeita_volta_status(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    s = store.criar("x")
    b = Briefing()
    b.confirmar()
    store.salvar_briefing(s.id, b)
    b.adicionar(item("ator", "A"))
    store.salvar_briefing(s.id, b)
    assert store.obter(s.id).status == "aberta"
