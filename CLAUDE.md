# CLAUDE.md — regras para agentes de IA neste repositório

Leia antes de mudar qualquer coisa: [plano](docs/plano.md), [spec](docs/spec.md),
[harness](docs/harness.md) e [acompanhamento](docs/acompanhamento.md).

## Regras

- **Branches** (plano §2.1): `core/*` e `docs/*` → PR para `main`; `task/<agente>/*` → PR para
  `agent/<agente>`; `exp/*` nunca é mesclada. Nada de push direto em `main` ou `agent/*`.
- **Pastas**: uma branch de agente só altera `src/archagent/agents/<agente>/`, `kb/<agente>/`,
  `compose/agent-<agente>.yml`, `evals/casos/<agente>/`, `tests/agents/<agente>/` e `docs/`.
  `scripts/check_paths.py` confere isso no N0.
- **Containers**: um por agente e por ferramenta; configuração só por variável de ambiente.
- **MCP oficial primeiro** (plano §2.2).
- **arXiv**: toda sugestão baseada em artigo do arXiv é registrada em `docs/acompanhamento.md` §6.
- **Segredos**: nunca ler, copiar ou registrar o conteúdo do `.env`.
- **Antes de propor commit**: `make check` e `make test-local` (ou `make test` nos containers).
- **Fim de tarefa**: atualizar a documentação afetada e enviar ao GitHub (push + PR).
- **Linha de base**: não alterar `evals/baseline.json` sem pedido explícito.
- **Experimentos**: só em branch `exp/*` e pasta `experiments/`; `src/` nunca importa de `experiments/`.
- **Agente não escreve código nem altera `kb/` diretamente**: só grava propostas em
  `kb/<agente>/propostas/`.

## Comandos

| Comando | O que faz |
| --- | --- |
| `uv sync --all-extras` | Instala tudo localmente |
| `make check` | N0: ruff, mypy, gitleaks, pastas |
| `make test-local` | N1 local com cobertura |
| `make test` | N1 + N2 no container de testes |
| `make up` / `make down` | Sobe / derruba os containers |
| `make kb-check` | Valida a base de conhecimento |
| `make eval` | Avaliação rápida do agente (gasta tokens) |

## Estrutura

`src/archagent/core/` (núcleo compartilhado), `src/archagent/agents/<agente>/`,
`src/archagent/ui/`, `tools/<ferramenta>/`, `kb/`, `evals/`, `tests/`, `scripts/`, `compose/`.
