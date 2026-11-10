# ArchAgent

Agente de **análise e orientação de arquitetura**. Interpreta desenhos,
transcrições de reunião e mensagens do arquiteto e, na primeira etapa, gera
**modelos ArchiMate viáveis** para o Archi 5.

O agente não escreve nem altera código: entrega modelos, análises e
recomendações para a equipe decidir e implementar.

## Status

Etapa 1 (MVP ArchiMate) em construção. Andamento das fases em
[acompanhamento](docs/acompanhamento.md).

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [Plano](docs/plano.md) | Visão, etapas, regras do projeto, fases, riscos e decisões |
| [Spec](docs/spec.md) | Requisitos, dados, regras de validação, fluxo do agente, APIs |
| [Harness](docs/harness.md) | Testes, avaliação do agente, CI, guardrails, observabilidade e custos |
| [Arquitetura](docs/arquitetura.drawio) | Desenho em draw.io: contexto, containers, componentes e fluxo do agente |
| [Acompanhamento](docs/acompanhamento.md) | Status, referências do arXiv, experimentos e backlog |

## Stack prevista

Python 3.13 · LangGraph · FastAPI · Streamlit · Alibaba Cloud Model Studio
(DashScope) · Archi 5 · Docker Compose · GitHub Actions

## Configuração

Copie `.env.example` para `.env` e preencha a chave do DashScope. O `.env` nunca
vai para o repositório. Se a porta 8501 já estiver em uso, defina `UI_PORT`.

## Como rodar

| Comando | O que faz |
| --- | --- |
| `uv sync --all-extras` | Instala as dependências localmente (Python 3.13) |
| `make up` | Sobe os containers (`docker compose up`): agente, Archi, interface e servidor MCP |
| `make check` | Verificação estática: ruff, mypy, gitleaks, pastas |
| `make test-local` | Testes unitários com cobertura |
| `make test` | Testes no container de testes |

## Como usar

1. `make up` e abra `http://localhost:8501` (ou a porta de `UI_PORT`).
2. Crie uma sessão na barra lateral.
3. Na aba **Conversa**, escreva ou anexe transcrições (`.txt`, `.md`, `.vtt`, `.srt`, `.docx`) e desenhos (`.drawio`, `.png`, `.jpg`).
4. Responda as **Perguntas** e revise o **Briefing**; depois clique em **Confirmar briefing**.
5. Na aba **Modelo**, clique em **Gerar modelo** e baixe o `.archimate` (abre no Archi 5), o Exchange Format e o relatório de viabilidade.

### Pelo Claude Code (MCP)

O container `mcp` expõe o agente como ferramentas MCP em `http://localhost:8700/mcp`
(porta em `MCP_PORT`, só na máquina local). Com `make up` rodando, abra o Claude Code na
raiz do repositório: o [`.mcp.json`](.mcp.json) já registra o servidor `archagent`
(aprove-o quando o Claude Code perguntar). Fora do repositório:

```bash
claude mcp add --transport http archagent http://localhost:8700/mcp
```

Depois é só pedir, por exemplo: "crie uma sessão no ArchAgent com esta transcrição e gere o
modelo". Ferramentas: `criar_sessao`, `enviar_texto`, `enviar_arquivo`, `ver_briefing`,
`listar_perguntas`, `responder_pergunta`, `confirmar_briefing`, `gerar_modelo`,
`ver_modelo`, `baixar_arquivo`, `enviar_mensagem` e outras (spec §15.1).

Regras para agentes de IA que trabalham neste repositório: [CLAUDE.md](CLAUDE.md).
