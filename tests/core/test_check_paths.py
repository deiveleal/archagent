from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_paths", Path(__file__).resolve().parents[2] / "scripts" / "check_paths.py"
)
assert _spec and _spec.loader
check_paths = importlib.util.module_from_spec(_spec)
sys.modules["check_paths"] = check_paths
_spec.loader.exec_module(check_paths)


def test_task_so_altera_pasta_do_agente() -> None:
    ok = ["src/archagent/agents/archimate/x.py", "kb/archimate/a.md", "docs/spec.md"]
    assert check_paths.violacoes("task/archimate/f1", "agent/archimate", ok) == []
    erros = check_paths.violacoes(
        "task/archimate/f1", "agent/archimate", ["src/archagent/core/a.py"]
    )
    assert len(erros) == 1


def test_core_nao_altera_agente() -> None:
    assert check_paths.violacoes("core/x", "main", ["src/archagent/core/a.py"]) == []
    assert check_paths.violacoes("core/x", "main", ["src/archagent/agents/archimate/a.py"])
    assert check_paths.violacoes("core/x", "main", ["compose/agent-archimate.yml"])


def test_docs_so_altera_docs() -> None:
    assert check_paths.violacoes("docs/x", "main", ["docs/a.md", "README.md"]) == []
    assert check_paths.violacoes("docs/x", "main", ["src/a.py"])


def test_exp_nunca_entra_em_main() -> None:
    assert check_paths.violacoes("exp/2026-11-08-x", "main", [])
    assert check_paths.violacoes("core/x", "main", ["experiments/a.py"])


def test_base_padrao() -> None:
    assert check_paths.base_padrao("task/archimate/f1") == "agent/archimate"
    assert check_paths.base_padrao("core/x") == "main"
