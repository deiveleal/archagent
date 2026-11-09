from __future__ import annotations

import json
import shutil
from pathlib import Path

from archagent.agents.archimate.kb_tools import checar, main
from archagent.agents.archimate.vault import Vault, ler_nota, tokens, validar_nota

from .conftest import KB

VAULT = KB / "archimate" / "vault"


def vault() -> Vault:
    return Vault.carregar(VAULT, incluir_rascunhos=True)


def test_tokens_sem_acento_e_camelcase() -> None:
    assert tokens("ApplicationComponent é Serviço") == ["application", "component", "servico"]


def test_so_revisadas_por_padrao() -> None:
    v = Vault.carregar(VAULT)
    assert all(n.status == "revisado" for n in v.notas.values())
    assert len(v.rascunhos) >= 35


def test_ficha_elemento() -> None:
    ficha = vault().ficha("ApplicationComponent")
    assert ficha is not None
    assert "API de Pedidos" in ficha.corpo


def test_busca_encontra_banco_e_segue_links() -> None:
    resultado = vault().buscar("onde guardar dados no banco PostgreSQL", limite=2)
    ids = [n.id for n in resultado]
    assert "padrao-banco-de-dados" in ids[:2] or "antipadrao-banco-como-componente" in ids[:2]
    # links de 1 nível entram depois das principais
    assert len(ids) > 2


def test_busca_filtra_por_tipo() -> None:
    resultado = vault().buscar("banco de dados", tipo="antipadrao")
    assert resultado and resultado[0].tipo == "antipadrao"


def test_nota_invalida(tmp_path: Path) -> None:
    arq = tmp_path / "x.md"
    arq.write_text("---\nid: y\ntipo: outro\nstatus: revisado\n---\n# X\n[[nada]]\n")
    erros = validar_nota(ler_nota(arq), {"y"})
    texto = " ".join(erros)
    assert "falta o campo 'tags'" in texto
    assert "tipo 'outro'" in texto
    assert "revisado_por" in texto
    assert "[[nada]]" in texto
    assert "diferente do nome" in texto


def test_kb_check_ok() -> None:
    erros, info = checar(KB)
    assert erros == []
    assert any("exemplos ouro: 5" in i for i in info)
    assert main(["check", "--kb", str(KB)]) == 0


def test_kb_check_reprova_exemplo_quebrado(tmp_path: Path) -> None:
    copia = tmp_path / "kb"
    shutil.copytree(KB, copia)
    ex = copia / "archimate" / "exemplos" / "EX-001-portal-pedidos" / "modelo_esperado.json"
    dados = json.loads(ex.read_text())
    for r in dados["relacoes"]:
        if r["origem"] == "PostgreSQL":
            r["tipo"] = "Composition"
    ex.write_text(json.dumps(dados))
    (copia / "archimate" / "vault" / "elementos" / "elemento-node.md").unlink()
    erros, _ = checar(copia)
    texto = "\n".join(erros)
    assert "REL-PERMITIDA" in texto
    assert "sem ficha: Node" in texto
