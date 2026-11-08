"""Checagem de pastas por tipo de branch (docs/harness.md §6.3).

Uso: python scripts/check_paths.py [--branch NOME] [--base REF]

Na CI, a branch e a base vêm de GITHUB_HEAD_REF / GITHUB_BASE_REF.
Arquivos iguais aos da `origin/main` não contam: são mudanças do núcleo que
a branch apenas trouxe da `main`.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS_PERMITIDOS = ("docs/", "README.md", "CLAUDE.md")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=RAIZ,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def ref_existe(ref: str) -> bool:
    try:
        git("rev-parse", "--verify", "--quiet", ref)
    except subprocess.CalledProcessError:
        return False
    return True


def igual_a_main(arquivo: str) -> bool:
    if not ref_existe("origin/main"):
        return False
    try:
        na_main = git("rev-parse", f"origin/main:{arquivo}").strip()
        aqui = git("rev-parse", f"HEAD:{arquivo}").strip()
    except subprocess.CalledProcessError:
        return False
    return na_main == aqui


def arquivos_alterados(base: str) -> list[str]:
    saida = git("diff", "--name-only", f"{base}...HEAD")
    return [a for a in saida.splitlines() if a and not igual_a_main(a)]


def permitidos_agente(agente: str) -> tuple[str, ...]:
    return (
        f"src/archagent/agents/{agente}/",
        f"kb/{agente}/",
        f"compose/agent-{agente}.yml",
        f"evals/casos/{agente}/",
        f"evals/{agente}/",
        f"tests/agents/{agente}/",
        f"tests/fixtures/{agente}/",
        "docker-compose.yml",  # só a linha de include do agente
        *DOCS_PERMITIDOS,
    )


def violacoes(branch: str, base: str, alterados: list[str]) -> list[str]:
    erros: list[str] = []
    if branch.startswith("exp/") and (base == "main" or base.startswith("agent/")):
        erros.append("Branches exp/* nunca são mescladas em main nem em agent/* (plano §2.5).")
    for arq in alterados:
        if arq.startswith("experiments/") and not branch.startswith("exp/"):
            erros.append(f"{arq}: experiments/ só muda em branch exp/*")
    m = re.match(r"^(?:task/([^/]+)/.+|agent/([^/]+))$", branch)
    if m:
        agente = m.group(1) or m.group(2)
        ok = permitidos_agente(agente)
        erros += [
            f"{a}: fora das pastas do agente '{agente}'"
            for a in alterados
            if not a.startswith(ok) and not a.startswith("experiments/")
        ]
    elif branch.startswith("core/"):
        erros += [
            f"{a}: branch core/* não altera pastas de agente"
            for a in alterados
            if a.startswith(("src/archagent/agents/", "compose/agent-"))
            and not a.startswith("src/archagent/agents/__init__")
        ]
    elif branch.startswith("docs/"):
        erros += [
            f"{a}: branch docs/* só altera docs/, README.md e CLAUDE.md"
            for a in alterados
            if not a.startswith(DOCS_PERMITIDOS)
        ]
    return erros


def imports_de_experiments() -> list[str]:
    erros = []
    padrao = re.compile(r"^\s*(from|import)\s+experiments\b", re.MULTILINE)
    for arq in (RAIZ / "src").rglob("*.py"):
        if padrao.search(arq.read_text(encoding="utf-8")):
            erros.append(f"{arq.relative_to(RAIZ)}: src/ não pode importar de experiments/")
    return erros


def base_padrao(branch: str) -> str:
    m = re.match(r"^task/([^/]+)/", branch)
    return f"agent/{m.group(1)}" if m else "main"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--branch", default=os.environ.get("GITHUB_HEAD_REF") or None)
    p.add_argument("--base", default=os.environ.get("GITHUB_BASE_REF") or None)
    args = p.parse_args(argv)
    branch = args.branch or git("rev-parse", "--abbrev-ref", "HEAD").strip()
    base = args.base or base_padrao(branch)
    base_ref = f"origin/{base}" if ref_existe(f"origin/{base}") else base

    erros = imports_de_experiments()
    if branch in ("main", "HEAD") or (branch.startswith("agent/") and not args.base):
        alterados: list[str] = []
    elif ref_existe(base_ref):
        alterados = arquivos_alterados(base_ref)
    else:
        print(f"Aviso: base '{base_ref}' não encontrada; só a checagem de imports foi feita.")
        alterados = []
    erros += violacoes(branch, base, alterados)
    if erros:
        print(f"Checagem de pastas reprovada (branch {branch} → {base}):")
        print("\n".join(f"  - {e}" for e in erros))
        return 1
    print(f"Checagem de pastas ok (branch {branch} → {base}, {len(alterados)} arquivos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
