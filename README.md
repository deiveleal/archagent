# ArchAgent

Agente de **análise e orientação de arquitetura**. Interpreta desenhos,
transcrições de reunião e mensagens do arquiteto e, na primeira etapa, gera
**modelos ArchiMate viáveis** para o Archi 5.

O agente não escreve nem altera código: entrega modelos, análises e
recomendações para a equipe decidir e implementar.

## Status

Fase de **documentação** da Etapa 1 (MVP ArchiMate). Ainda não há código.

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
vai para o repositório.
