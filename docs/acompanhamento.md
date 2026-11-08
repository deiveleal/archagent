# Acompanhamento — ArchAgent

> Atualizado em: 2026-11-08 · Responsável: Deive Leal
>
> Documento vivo. Registra o status das fases, as decisões, as referências
> científicas usadas e o backlog. A estrutura completa será fechada quando este
> artefato for trabalhado na sua vez (item 5 do plano).

## 1. Status

| Item | Status | Observação |
| --- | --- | --- |
| Plano (`docs/plano.md`) | Concluído (v1.0) | Pronto para a spec |
| Spec (`docs/spec.md`) | Em revisão (v0.1) | 5 pontos a verificar na seção 19 |
| Harness (`docs/harness.md`) | Em revisão (v0.1) | 4 pontos a verificar na seção 13 |
| Desenho de arquitetura (`docs/arquitetura.drawio`) | Não iniciado | |
| Acompanhamento (este documento) | Em andamento | Criado para registrar as referências do arXiv |

## 2. Referências científicas (arXiv)

**Regra:** toda sugestão ou decisão baseada em artigo do arXiv registra o artigo
aqui, com o que foi aproveitado dele e onde foi aplicado. Uma sugestão sem o
registro do artigo não é adotada.

Status possíveis: **em avaliação** (sugestão ainda não aceita), **adotado**
(influenciou uma decisão), **descartado** (avaliado e não usado, com o motivo).

| arXiv | Título | O que aproveitamos | Onde se aplica | Status | Registrado em |
| --- | --- | --- | --- | --- | --- |
| [2309.02427](https://arxiv.org/abs/2309.02427) | Cognitive Architectures for Language Agents (CoALA) | Separar a memória do agente em semântica, episódica e procedural; evitar que o agente escreva sozinho na memória procedural | Estrutura da base de conhecimento por agente | Adotado | 2026-11-08 |
| [2502.12110](https://arxiv.org/abs/2502.12110) | A-MEM: Agentic Memory for LLM Agents | Notas curtas e ligadas (estilo Zettelkasten) como formato do conhecimento; o agente propõe novas notas e ligações | Vault de notas Markdown; pasta de aprendizados propostos | Adotado | 2026-11-08 |
| [2501.13956](https://arxiv.org/abs/2501.13956) | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | Marcar fatos corrigidos como superados, com data, em vez de apagar | Memória das sessões e briefing (correções do arquiteto) | Adotado | 2026-11-08 |
| [2506.05690](https://arxiv.org/abs/2506.05690) | When to use Graphs in RAG | GraphRAG nem sempre supera a busca simples; não adotar grafo numa base pequena | Busca no vault (busca híbrida simples no MVP) | Adotado | 2026-11-08 |
| [2607.26100](https://arxiv.org/abs/2607.26100) | LLMs for Software Engineering Diagrams: A Systematic Review of UML and ER modelling | LLMs violam o metamodelo mesmo com sintaxe correta; só o prompt não basta | Regras do ArchiMate em dados + validadores (V2, V3) | Adotado | 2026-11-08 |
| [2510.25890](https://arxiv.org/abs/2510.25890) | Metamodel-Guided Model Generation with Layered Constraints | Validar o modelo gerado contra restrições explícitas do metamodelo, fora do LLM | Ciclo validar → corrigir do agente ArchiMate | Adotado | 2026-11-08 |
| [2501.03566](https://arxiv.org/abs/2501.03566) | Applying LLMs in Knowledge Graph-based Enterprise Modeling: Challenges and Opportunities | A supervisão de um especialista humano é essencial na modelagem com LLM | Confirmação do briefing pelo arquiteto; revisão dos modelos | Adotado | 2026-11-08 |
| [2404.13076](https://arxiv.org/abs/2404.13076) | LLM Evaluators Recognize and Favor Their Own Generations | Modelos favorecem os próprios textos quando avaliam; usar um juiz de modelo diferente do agente | Juiz LLM da avaliação (`docs/harness.md`, seção 5.4) | Em avaliação | 2026-11-08 |
| [2306.05685](https://arxiv.org/abs/2306.05685) | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | Juízes LLM preferem a primeira resposta e as mais longas; usar rubrica fechada e avaliar nas duas ordens | Juiz LLM da avaliação (`docs/harness.md`, seção 5.4) | Em avaliação | 2026-11-08 |

## 3. Experimentos

**Regra:** experimentos ficam isolados em branch `exp/*` e pasta `experiments/`,
sem merge no código validado (plano, seção 2.5). Todo experimento é registrado
aqui.

| Id | Data | Hipótese | Resultado | Decisão | Onde está |
| --- | --- | --- | --- | --- | --- |
| EXP-001 | 2026-11-08 | Algum modelo do Token Plan faz bem as três tarefas do agente: chamada de ferramenta, saída JSON e leitura de imagem | 6 modelos testados. `qwen3.8-max`: melhor modelagem e leitura de imagem perfeita (17–20 s). `deepseek-v4.1-flash-1017`: bom e rápido (6–8 s). `qwen3.8-flash`: falhou na ferramenta. `deepseek-v4-pro-0813`: respondeu vazio à imagem sem dar erro. `glm-5.3`: não aceita imagem | `qwen3.8-max` para texto e visão; `deepseek-v4.1-flash-1017` como alternativa rápida e juiz | Feito antes da regra de isolamento, em pasta temporária fora do repositório; rodada única, entrada pequena |

## 4. Decisões

As decisões do projeto estão na seção 6 do plano. A partir da spec, as decisões
novas passam a ser registradas aqui, com data e motivo.

## 5. Backlog

| Item | Etapa | Origem |
| --- | --- | --- |
| Partir de um modelo `.archimate` existente (ler e alterar) | Depois da Etapa 1 | Decisão do plano |
| Avaliar `deepseek-v4.1-flash-1017` como modelo rápido para etapas simples | Etapa 1 (harness) | Teste de modelos, 2026-11-08 |
| Adotar GraphRAG ou HippoRAG se o vault passar de algumas centenas de notas | Futuro | arXiv 2506.05690 |
| Adotar Zep/Graphiti se houver memória entre sessões | Futuro | arXiv 2501.13956 |
