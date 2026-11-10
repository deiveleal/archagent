"""Ferramentas da base de conhecimento do agente ArchiMate (harness §9).

python -m archagent.agents.archimate.kb_tools check [--kb kb]
python -m archagent.agents.archimate.kb_tools extract-relations <relationships.xml> "<fonte>"
python -m archagent.agents.archimate.kb_tools revisar --por "<nome>" (--todas | <id> ...)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from archagent.agents.archimate.exchange import exportar, validar_v1
from archagent.agents.archimate.layout import gerar_visoes
from archagent.agents.archimate.model import Elemento, Modelo, Relacao
from archagent.agents.archimate.rules import RegrasInvalidas, carregar_regras, extrair_relacoes
from archagent.agents.archimate.validation import validar_modelo
from archagent.agents.archimate.vault import Vault, ler_nota, validar_nota


@dataclass
class ItemEsperado:
    id: str
    tipo: str
    nome: str
    status: str = "ativo"


def carregar_exemplo(pasta: Path) -> tuple[list[ItemEsperado], Modelo]:
    """Converte briefing_esperado.json e modelo_esperado.json no modelo interno."""
    briefing = json.loads((pasta / "briefing_esperado.json").read_text(encoding="utf-8"))
    esperado = json.loads((pasta / "modelo_esperado.json").read_text(encoding="utf-8"))
    itens = [ItemEsperado(i["id"], i["tipo"], i["nome"]) for i in briefing["itens"]]
    elementos = [
        Elemento(
            tipo=e["tipo"],
            nome=e["nome"],
            origens=e.get("origens", []),
            premissa=e.get("premissa", False),
        )
        for e in esperado["elementos"]
    ]
    por_nome = {e.nome: e.id for e in elementos}
    relacoes = [
        Relacao(
            tipo=r["tipo"],
            origem=por_nome.get(r["origem"], r["origem"]),
            destino=por_nome.get(r["destino"], r["destino"]),
            nome=r.get("nome", ""),
            origens=r.get("origens", []),
            acesso=r.get("acesso"),
        )
        for r in esperado["relacoes"]
    ]
    return itens, Modelo(nome=pasta.name, elementos=elementos, relacoes=relacoes)


def checar(kb: Path) -> tuple[list[str], list[str]]:
    """Devolve (erros, informações)."""
    erros: list[str] = []
    info: list[str] = []
    try:
        regras = carregar_regras(kb)
    except RegrasInvalidas as exc:
        return [str(exc)], info

    # Regras: relacoes.json bate com a extração da fonte registrada
    pasta_regras = kb / "archimate" / "regras"
    gravado = json.loads((pasta_regras / "relacoes.json").read_text(encoding="utf-8"))
    fonte = pasta_regras / "fonte" / "relationships.xml"
    if not fonte.exists():
        erros.append("regras: fonte/relationships.xml ausente")
    elif extrair_relacoes(fonte, gravado.get("fonte", "")) != gravado:
        erros.append("regras: relacoes.json não bate com a extração de fonte/relationships.xml")

    # XSDs carregáveis
    try:
        validar_v1(exportar(Modelo()), regras.xsd_dir)
    except Exception as exc:
        erros.append(f"xsd: não foi possível carregar os XSDs: {exc}")

    # Vault
    pasta_vault = kb / "archimate" / "vault"
    notas = []
    for arq in sorted(pasta_vault.rglob("*.md")):
        try:
            notas.append(ler_nota(arq))
        except (ValueError, OSError) as exc:
            erros.append(f"vault: {exc}")
    ids = {n.id for n in notas}
    for n in notas:
        erros += [f"vault: {e}" for e in validar_nota(n, ids)]
    fichas = {n.archimate for n in notas if n.tipo == "elemento"}
    faltam = sorted(set(regras.elementos) - fichas)
    if faltam:
        erros.append(f"vault: elementos do MVP sem ficha: {', '.join(faltam)}")
    rascunhos = Vault(notas).rascunhos
    if rascunhos:
        info.append(
            f"vault: {len(rascunhos)} notas em rascunho (o agente só usa 'revisado' "
            "quando VAULT_INCLUIR_RASCUNHOS=false)"
        )

    # Exemplos ouro
    pasta_ex = kb / "archimate" / "exemplos"
    exemplos = sorted(p for p in pasta_ex.iterdir() if p.is_dir()) if pasta_ex.exists() else []
    for ex in exemplos:
        faltando = [
            f
            for f in ("briefing_esperado.json", "modelo_esperado.json", "notas.md")
            if not (ex / f).exists()
        ]
        if not (ex / "entrada").is_dir() or not any((ex / "entrada").iterdir()):
            faltando.append("entrada/")
        if faltando:
            erros.append(f"exemplo {ex.name}: falta {', '.join(faltando)}")
            continue
        itens, modelo = carregar_exemplo(ex)
        modelo.visoes = gerar_visoes(modelo, regras)
        achados = validar_v1(exportar(modelo), regras.xsd_dir)
        achados += validar_modelo(modelo, regras, itens)
        erros += [
            f"exemplo {ex.name}: {a.criterio} {a.regra}: {a.mensagem}"
            for a in achados
            if a.severidade == "erro"
        ]
    info.append(f"exemplos ouro: {len(exemplos)}")

    # Propostas
    for arq in sorted((kb / "archimate" / "propostas").glob("*.md")):
        if arq.name == "README.md":
            continue
        texto = arq.read_text(encoding="utf-8")
        for secao in ("Correção observada", "Sessões", "Nota proposta"):
            if not re.search(rf"^#+\s*{secao}", texto, re.MULTILINE | re.IGNORECASE):
                erros.append(f"proposta {arq.name}: falta a seção '{secao}'")
    return erros, info


def marcar_revisadas(
    vault: Path, por: str, ids: list[str] | None, quando: date | None = None
) -> list[str]:
    """Marca notas do vault como revisadas pelo arquiteto (P-12). Devolve os ids marcados.

    `ids=None` marca todas as que estão em rascunho. Id inexistente é erro.
    """
    if not por.strip():
        raise ValueError("informe quem revisou (--por)")
    dia = (quando or date.today()).isoformat()
    arquivos = {ler_nota(a).id: a for a in sorted(vault.rglob("*.md")) if a.name != "README.md"}
    faltando = sorted(set(ids or []) - arquivos.keys())
    if faltando:
        raise ValueError(f"notas inexistentes: {', '.join(faltando)}")
    alvo = (
        ids
        if ids is not None
        else [i for i, a in arquivos.items() if ler_nota(a).status != "revisado"]
    )
    nome = json.dumps(por.strip(), ensure_ascii=False)
    for nid in alvo:
        arq = arquivos[nid]
        texto = arq.read_text(encoding="utf-8")
        _, meta, corpo = texto.split("---", 2)
        meta = re.sub(r"(?m)^status:.*$", "status: revisado", meta)
        meta = re.sub(r"(?m)^revisado_por:.*$", f"revisado_por: {nome}", meta)
        meta = re.sub(r"(?m)^revisado_em:.*$", f"revisado_em: {dia}", meta)
        arq.write_text(f"---{meta}---{corpo}", encoding="utf-8")
    return list(alvo)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kb_tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--kb", type=Path, default=Path("kb"))
    e = sub.add_parser("extract-relations")
    e.add_argument("xml", type=Path)
    e.add_argument("fonte")
    e.add_argument("--saida", type=Path, default=Path("kb/archimate/regras/relacoes.json"))
    r = sub.add_parser("revisar", help="marca notas do vault como revisadas")
    r.add_argument("ids", nargs="*")
    r.add_argument("--por", required=True)
    r.add_argument("--todas", action="store_true")
    r.add_argument("--vault", type=Path, default=Path("kb/archimate/vault"))
    args = p.parse_args(argv)
    if args.cmd == "revisar":
        if bool(args.ids) == args.todas:
            p.error("informe os ids das notas ou --todas")
        try:
            feitas = marcar_revisadas(args.vault, args.por, None if args.todas else args.ids)
        except ValueError as exc:
            print(f"ERRO: {exc}")
            return 1
        print(f"{len(feitas)} nota(s) marcadas como revisadas por {args.por}")
        return 0
    if args.cmd == "extract-relations":
        dados: dict[str, Any] = extrair_relacoes(args.xml, args.fonte)
        args.saida.write_text(
            json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"{args.saida}: {len(dados['permitidas'])} conceitos")
        return 0
    erros, info = checar(args.kb)
    for i in info:
        print(f"info: {i}")
    for erro in erros:
        print(f"ERRO: {erro}")
    print("kb-check: " + ("reprovado" if erros else "ok"))
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
