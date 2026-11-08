# Acompanhamento — ArchAgent

> Atualizado em: 2026-11-08 · Responsável: Deive Leal
>
> Documento vivo. É atualizado **ao fim de toda tarefa**, no mesmo PR que a
> entrega (plano, seção 2.1).

## 1. Como usar este documento

| Seção | Quando atualizar |
| --- | --- |
| 2. Artefatos | Quando um artefato de orientação muda de versão ou de status |
| 3. Fases da Etapa 1 | Quando uma fase começa, muda de status ou fecha |
| 4. Entregas | Ao fim de toda tarefa: o que foi feito, branch e PR |
| 5. Pendências | Quando surge ou se resolve um ponto a verificar ou decidir |
| 6. Referências do arXiv | Sempre que uma sugestão se basear em artigo do arXiv |
| 7. Experimentos | Sempre que um experimento for feito |
| 8. Decisões | Quando uma decisão é tomada depois do plano v1.0 |
| 9. Backlog | Quando uma ideia fica para depois |

## 2. Artefatos de orientação

| Artefato | Arquivo | Versão | Status | Observação |
| --- | --- | --- | --- | --- |
| Plano | [`docs/plano.md`](plano.md) | v1.0 | Concluído | Atualizado com novas regras sem mudar de versão maior |
| Spec | [`docs/spec.md`](spec.md) | v0.1 | Em revisão | 5 pontos a verificar (seção 5 deste documento) |
| Harness | [`docs/harness.md`](harness.md) | v0.1 | Em revisão | 4 pontos a verificar (seção 5 deste documento) |
| Desenho de arquitetura | [`docs/arquitetura.drawio`](arquitetura.drawio) | v1.0 | Concluído | 4 páginas: contexto, containers, componentes do agente, fluxo do agente |
| Acompanhamento | `docs/acompanhamento.md` | — | Ativo | Este documento |

## 3. Fases da Etapa 1 (MVP ArchiMate)

| Fase | Status | Início | Fim | Critério de saída atingido? | PR |
| --- | --- | --- | --- | --- | --- |
| F0 — Fundação | Concluída | 2026-11-08 | 2026-11-08 | Sim, exceto tornar a CI obrigatória no ruleset (P-10) | #2, #3 |
| F1 — Base de conhecimento, modelo ArchiMate e validação | Em andamento | 2026-11-08 | — | — | — |
| F2 — Entrada por texto e transcrição | Concluída | 2026-11-08 | 2026-11-08 | Sim: briefing correto nos 5 exemplos ouro e metas N3 atingidas | #7, #11 |
| F3 — Modelagem a partir do briefing | Em andamento | 2026-11-08 | — | Os 5 exemplos geram modelos que passam em V1–V5 | — |
| F4 — Entrada por desenho | Não iniciada | — | — | — | — |
| F5 — Refinamento pela conversa e avaliação | Não iniciada | — | — | — | — |

Critérios de saída de cada fase: plano, seção 3.7.

## 4. Entregas

| Data | Tarefa | Branch | Commit / PR |
| --- | --- | --- | --- |
| 2026-11-08 | Plano v1.0, spec v0.1, harness v0.1, README, `.env.example` | `main` (commit inicial, antes das regras de proteção) | `d2a0064` |
| 2026-11-08 | Repositório público criado (`deiveleal/archagent`), branch `agent/archimate` criada, regras de proteção ativadas | — | Ruleset `protecao-main-e-agentes` |
| 2026-11-08 | Desenho de arquitetura (drawio) e acompanhamento completo | `docs/arquitetura-acompanhamento` | PR #1 |
| 2026-11-08 | F0 — núcleo: `pyproject`/`uv`, config, logs JSON, cliente LLM (DashScope + replay), `ui` mínima, compose, Makefile, CI, checagem de pastas, `CLAUDE.md` | `core/f0-fundacao` | PR #2 |
| 2026-11-08 | F0 — agente: API FastAPI (`/health`, `/health/llm`), formato de erro com `request_id`, container `agent-archimate` sem porta publicada | `task/archimate/f0-api` | PR #3 |
| 2026-11-08 | F1 — container `tool-archi`: Archi 5.10.0 + Xvfb + API `/health` e `/convert`; erro do Archi legível; testes N1 e N2 | `core/f1-tool-archi` | PR #4 |
| 2026-11-08 | F1 — agente: regras (elementos, relações do Archi 5.10, coerência, XSDs), modelo interno, validadores V1–V4, exportação Exchange Format, layout por viewpoint, cliente do `tool-archi` (V5), vault (35 fichas + padrões, anti-padrões e convenções, em rascunho), busca BM25, 5 exemplos ouro, `kb-check` | `task/archimate/f1-kb-validacao` | PR #5 |
| 2026-11-08 | Sincronização `main` → `agent/archimate` | `main` | PR #6 |
| 2026-11-08 | F2 — núcleo: leitores de entrada (txt, md, vtt, srt, docx, drawio, imagem) com validação e proteção XXE, briefing, sessões em arquivo, `kb/core`, workflows `kb.yml` e `eval.yml` | `core/f2-entradas-briefing` | PR #7 |
| 2026-11-08 | Sincronização `main` → `agent/archimate` | `sync/main-para-agent-archimate` | PR #10 (substitui o #8, que tinha conflito) |
| 2026-11-08 | Núcleo: `LLM_ENABLE_THINKING` (modo de raciocínio do Qwen3 desligado por padrão) | `core/llm-sem-raciocinio` | PR #9 |
| 2026-11-08 | F2 — agente: interpretação das entradas pelo LLM (com origem conferida), perguntas de esclarecimento, grafo de entrada no LangGraph, endpoints de sessão, entrada, briefing, perguntas e uso; 13 casos N3 e executor da avaliação | `task/archimate/f2-briefing` | PR #11 |
| 2026-11-08 | F3 — agente: modelagem com guia de tipos do vault, ciclo validar → corrigir (até 3 rodadas), premissas, visões, exportação, V5, relatório de viabilidade, geração em segundo plano com eventos (SSE) e downloads; métricas de modelagem na avaliação N3 | `task/archimate/f3-modelagem` | PR #12 |

## 5. Pendências

| Id | Pendência | Origem | Quando resolver |
| --- | --- | --- | --- |
| P-01 | ~~Comando exato da linha de comando do Archi 5 e necessidade de Xvfb~~ **Resolvida:** precisa de Xvfb; comando na spec §14 | Spec §19 | F1 (2026-11-08) |
| P-02 | ~~Algoritmo de layout das visões~~ **Resolvida:** spec §8.4 | Spec §19 | F1 (2026-11-08) |
| P-03 | ~~Checkpointer do LangGraph em SQLite~~ **Resolvida:** não é necessário; estado na sessão (D-10) | Spec §19 | F2 (2026-11-08) |
| P-04 | ~~Modelo de embeddings para a busca no vault~~ **Resolvida:** só busca por palavra (BM25) no MVP; spec §10.6 | Spec §19 | F1 (2026-11-08) |
| P-05 | ~~Versões dos XSDs do Exchange Format~~ **Resolvida:** XSDs do Archi 5.10.0 | Spec §19 | F1 (2026-11-08) |
| P-06 | Limite de tokens por execução do `eval.yml` | Harness §13 | Depois da 1ª avaliação completa |
| P-07 | Se o `deepseek-v4.1-flash-1017` funciona bem como juiz com temperatura 0 | Harness §13 | F3 |
| P-08 | ~~Se o Archi 5 roda na CI do GitHub~~ **Resolvida:** roda; os testes N2 com o `tool-archi` passam no `ubuntu-latest` | Harness §13 | F1 (2026-11-08) |
| P-09 | Regra de aprovação de revisor quando entrar mais alguém | Harness §13 | Quando houver segunda pessoa |
| P-10 | Adicionar as verificações obrigatórias (`N0`, `N1 + N2`, depois `eval` e `kb`) ao ruleset. **Precisa ser feito pelo responsável:** o agente de IA não tem permissão para mudar a proteção das branches | Decisão D-02 | Agora |
| P-12 | Revisão das 46 notas do vault pelo arquiteto (hoje em `rascunho`; o agente usa os rascunhos com `VAULT_INCLUIR_RASCUNHOS=true`) | Critério de saída da F1 | Antes de fechar a F1 |
| P-13 | Abrir no Archi 5 um `.archimate` gerado e conferir se as visões estão legíveis (V5 manual) | Critério de saída da F1 | Antes de fechar a F1 |
| P-15 | O `eval.yml` precisa subir o `tool-archi` para medir a viabilidade (V5) na CI | Avaliação da F3 | Próximo PR do núcleo |
| P-14 | Cadastrar o secret `DASHSCOPE_API_KEY` no GitHub para o `eval.yml` (o agente de IA não lê o `.env`) | Harness §6.1 | Antes da 1ª avaliação na CI |
| P-11 | Chave SSH desta máquina não está cadastrada no GitHub; o envio está sendo feito por HTTPS com o login do `gh` | Decisão D-03 | Quando conveniente |

## 6. Referências científicas (arXiv)

**Regra:** toda sugestão ou decisão baseada em artigo do arXiv registra o artigo
aqui, com o que foi aproveitado dele e onde foi aplicado. Uma sugestão sem o
registro do artigo não é adotada.

Status possíveis: **em avaliação** (sugestão ainda não aceita), **adotado**
(influenciou uma decisão), **descartado** (avaliado e não usado, com o motivo).

| arXiv | Título | O que aproveitamos | Onde se aplica | Status | Registrado em |
| --- | --- | --- | --- | --- | --- |
| [2309.02427](https://arxiv.org/abs/2309.02427) | Cognitive Architectures for Language Agents (CoALA) | Separar a memória do agente em semântica, episódica e procedural; evitar que o agente escreva sozinho na memória procedural | Estrutura da base de conhecimento por agente (plano §2.4) | Adotado | 2026-11-08 |
| [2502.12110](https://arxiv.org/abs/2502.12110) | A-MEM: Agentic Memory for LLM Agents | Notas curtas e ligadas (estilo Zettelkasten) como formato do conhecimento; o agente propõe novas notas e ligações | Vault de notas Markdown; pasta de aprendizados propostos | Adotado | 2026-11-08 |
| [2501.13956](https://arxiv.org/abs/2501.13956) | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | Marcar fatos corrigidos como superados, com data, em vez de apagar | Memória das sessões e briefing (correções do arquiteto) | Adotado | 2026-11-08 |
| [2506.05690](https://arxiv.org/abs/2506.05690) | When to use Graphs in RAG | GraphRAG nem sempre supera a busca simples; não adotar grafo numa base pequena | Busca no vault (busca híbrida simples no MVP) | Adotado | 2026-11-08 |
| [2607.26100](https://arxiv.org/abs/2607.26100) | LLMs for Software Engineering Diagrams: A Systematic Review of UML and ER modelling | LLMs violam o metamodelo mesmo com sintaxe correta; só o prompt não basta | Regras do ArchiMate em dados + validadores (V2, V3) | Adotado | 2026-11-08 |
| [2510.25890](https://arxiv.org/abs/2510.25890) | Metamodel-Guided Model Generation with Layered Constraints | Validar o modelo gerado contra restrições explícitas do metamodelo, fora do LLM | Ciclo validar → corrigir do agente ArchiMate | Adotado | 2026-11-08 |
| [2501.03566](https://arxiv.org/abs/2501.03566) | Applying LLMs in Knowledge Graph-based Enterprise Modeling: Challenges and Opportunities | A supervisão de um especialista humano é essencial na modelagem com LLM | Confirmação do briefing pelo arquiteto; revisão dos modelos | Adotado | 2026-11-08 |
| [2404.13076](https://arxiv.org/abs/2404.13076) | LLM Evaluators Recognize and Favor Their Own Generations | Modelos favorecem os próprios textos quando avaliam; usar um juiz de modelo diferente do agente | Juiz LLM da avaliação (harness §5.4) | Em avaliação | 2026-11-08 |
| [2306.05685](https://arxiv.org/abs/2306.05685) | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | Juízes LLM preferem a primeira resposta e as mais longas; usar rubrica fechada e avaliar nas duas ordens | Juiz LLM da avaliação (harness §5.4) | Em avaliação | 2026-11-08 |

## 7. Experimentos

**Regra:** experimentos ficam isolados em branch `exp/*` e pasta `experiments/`,
sem merge no código validado (plano, seção 2.5). Todo experimento é registrado
aqui.

| Id | Data | Hipótese | Resultado | Decisão | Onde está |
| --- | --- | --- | --- | --- | --- |
| EXP-001 | 2026-11-08 | Algum modelo do Token Plan faz bem as três tarefas do agente: chamada de ferramenta, saída JSON e leitura de imagem | 6 modelos testados. `qwen3.8-max`: melhor modelagem e leitura de imagem perfeita (17–20 s). `deepseek-v4.1-flash-1017`: bom e rápido (6–8 s). `qwen3.8-flash`: falhou na ferramenta. `deepseek-v4-pro-0813`: respondeu vazio à imagem sem dar erro. `glm-5.3`: não aceita imagem | `qwen3.8-max` para texto e visão; `deepseek-v4.1-flash-1017` como alternativa rápida e juiz | Feito antes da regra de isolamento, em pasta temporária fora do repositório; rodada única, entrada pequena |

### Resultados da avaliação

| Data | Branch | Casos | Cobertura | Inventados | Origem correta | Pergunta quando deve | Conflito | Injeção | Ilegível | Tokens/caso | p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-08 | `task/archimate/f2-briefing` | 13 (1 repetição) | 100% | 1% | 100% | 100% | 100% | 100% | 100% | 2.764 | 29 s |

| Data | Branch | Casos | Viabilidade | Tipo correto | Relações esperadas | Premissas | Rodadas | Tokens/caso | p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-08 | `task/archimate/f3-modelagem` | 5 ouro com modelo (13 no total) | 100% | 100% | 95% | 0% | 0,40 | 6.225 (média dos 13) | 74 s |

## 8. Decisões

As decisões até o plano v1.0 estão na seção 6 do plano. As decisões seguintes
ficam aqui.

| Id | Data | Decisão | Motivo |
| --- | --- | --- | --- |
| D-01 | 2026-11-08 | Repositório **público** no GitHub (`deiveleal/archagent`) | Escolha do responsável; permite usar regras de proteção na conta gratuita |
| D-02 | 2026-11-08 | Ruleset inicial em `main` e `agent/*`: só PR, sem force push, sem exclusão, sem aprovação obrigatória. Verificações obrigatórias entram na F0 | Ainda não existem workflows de CI para exigir |
| D-03 | 2026-11-08 | Envio ao GitHub por HTTPS, com o login do `gh` | A chave SSH desta máquina não está cadastrada no GitHub |
| D-05 | 2026-11-08 | Regras de relação e XSDs tirados do Archi **5.10.0**, com a fonte guardada em `kb/archimate/regras/fonte/` | Garante que o validador V2 e o Archi concordem; o `kb-check` confere a extração |
| D-06 | 2026-11-08 | Busca no vault só por palavra (BM25) no MVP | O Token Plan não oferece embeddings; base pequena (arXiv 2506.05690) |
| D-07 | 2026-11-08 | Fichas do vault criadas como `rascunho`; rascunhos em uso por configuração até a revisão | Permite seguir com as fases sem esconder que a revisão está pendente |
| D-08 | 2026-11-08 | Faixas de camada exportadas como containers; o Archi as converte em grupos | Visões legíveis; o Archi converte as coordenadas absolutas em relativas |
| D-09 | 2026-11-08 | Modo de raciocínio do `qwen3.8-max` desligado por padrão (`LLM_ENABLE_THINKING=false`) | Medido na extração do EX-001: ligado, 203 s e 9.162 tokens de saída (estoura o limite de 60 s); desligado, 19 s e 1.129 tokens. Reavaliar se a qualidade do briefing ficar abaixo da meta |
| D-10 | 2026-11-08 | Sem checkpointer do LangGraph: cada chamada da API roda um grafo curto; as pausas são o estado da sessão no volume | Mais simples e sobrevive ao reinício do container; os grafos não ficam parados esperando o arquiteto |
| D-11 | 2026-11-08 | O prompt de interpretação define quando usar `sistema` × `interface` × `servico` e pede nomes no singular | Na 1ª avaliação, "Portal Web", "API de Pedidos" e "Serviço de Pagamentos" foram classificados como interface/serviço; depois do ajuste, cobertura de 79–87% para 100% |
| D-12 | 2026-11-08 | Camadas ligadas diretamente (`Serving`); serviços e interfaces intermediários só quando o briefing os cita | Na 1ª avaliação da F3, o agente inventava serviços para ligar camadas: premissas em 20% (meta ≤ 15%) e relações diretas ausentes; depois do ajuste, premissas 0% e relações 91–95% |
| D-13 | 2026-11-08 | A avaliação aceita relações derivadas pelas regras do ArchiMate | Um modelo com serviço intermediário é equivalente ao com relação direta; sem isso, a métrica punia modelagem correta e mais detalhada |
| D-04 | 2026-11-08 | Novo tipo de branch `docs/<descricao>` para mudanças só de documentação, com PR direto para a `main` | Toda tarefa sobe ao GitHub, inclusive as de documentação, e a `main` só aceita PR |

## 9. Backlog

| Item | Etapa | Origem |
| --- | --- | --- |
| Partir de um modelo `.archimate` existente (ler e alterar) | Depois da Etapa 1 | Decisão do plano |
| Avaliar `deepseek-v4.1-flash-1017` como modelo rápido para etapas simples | Etapa 1 (harness) | EXP-001 |
| Adotar GraphRAG ou HippoRAG se o vault passar de algumas centenas de notas | Futuro | arXiv 2506.05690 |
| Adotar Zep/Graphiti se houver memória entre sessões | Futuro | arXiv 2501.13956 |
