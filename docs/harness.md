# Harness — ArchAgent

> Status: **rascunho v0.1** · Data: 2026-11-08 · Responsável: Deive Leal
>
> Base: `docs/plano.md` v1.0 e `docs/spec.md` v0.1. Os itens marcados com ⚠️ precisam ser verificados ou decididos.

## 1. Objetivo

O harness é **tudo o que garante a qualidade do projeto como um todo**: como ele
roda, como é testado, como os agentes são avaliados, o que bloqueia uma mudança
ruim, o que protege o agente em uso e como sabemos o que está acontecendo.

Ele responde a quatro perguntas:

1. **Funciona?** Testes determinísticos do código.
2. **O agente faz um bom trabalho?** Avaliação do agente com o LLM real.
3. **Uma mudança pode quebrar algo?** CI e proteção das branches.
4. **O agente em uso está seguro e sob controle?** Guardrails, observabilidade e custos.

## 2. Níveis de verificação

| Nível | O que verifica | LLM real? | Quando roda | Tempo alvo |
| --- | --- | --- | --- | --- |
| **N0 — Estática** | Formatação, lint, tipos, segredos, regras de pasta da branch | Não | Antes do commit e em todo PR | < 1 min |
| **N1 — Unitário** | Leitores de entrada, briefing, validadores V1–V4, exportação, layout, regras de coerência | Não (LLM simulado) | Em todo PR | < 3 min |
| **N2 — Integração** | API do agente, conversa com o `tool-archi` (V5), fluxo do grafo com LLM simulado, containers de pé | Não (LLM simulado) | Em todo PR | < 10 min |
| **N3 — Avaliação do agente** | Qualidade do briefing, da modelagem e da conversa | **Sim** | Rápida em PR para `agent/*`; completa em PR para `main` e semanalmente | < 15 min (rápida) |
| **N4 — Aceite manual** | Visões legíveis no Archi 5, utilidade do relatório | Sim | No fechamento de cada fase | — |

Os níveis N0 a N2 nunca chamam o DashScope: são rápidos, gratuitos e dão sempre o
mesmo resultado. Só o N3 gasta tokens.

## 3. Ambiente

Tudo roda em containers, do mesmo jeito na máquina e na CI.

| Comando | O que faz |
| --- | --- |
| `make up` | Sobe `ui`, `agent-archimate` e `tool-archi` |
| `make check` | N0: ruff, mypy, gitleaks, checagem de pastas |
| `make test` | N1 + N2 dentro dos containers |
| `make eval` | N3 rápida (casos marcados como `rapido`) |
| `make eval-full` | N3 completa (todos os casos, 3 repetições) |
| `make kb-check` | Validação da base de conhecimento (seção 9) |
| `make test-local` | N1 local, sem containers |
| `make report` | Gera o relatório de avaliação em `evals/reports/` |

- O compose tem um perfil `test` com um container `tests`, que usa a mesma imagem do agente e inclui as dependências de teste.
- Os testes N1 e N2 usam um **LLM simulado**: respostas gravadas por caso de teste, guardadas em `tests/fixtures/llm/`. Se uma chamada não tiver gravação, o teste falha, em vez de chamar a API.
- O `tool-archi` roda de verdade no N2, porque o V5 depende dele.

## 4. Testes determinísticos (N1 e N2)

### 4.1 O que cada módulo precisa testar

| Módulo | Casos obrigatórios |
| --- | --- |
| Leitores de transcrição | `.txt`, `.md`, `.vtt` e `.srt` com tempos e nomes de quem fala; `.docx`; arquivo vazio; codificação diferente de UTF-8 |
| Leitor `.drawio` | Arquivo comum; arquivo comprimido; várias páginas; formas sem texto; ligações sem destino; agrupamentos; XML malicioso com entidade externa (deve ser recusado) |
| Upload | Extensão aceita com conteúdo errado; arquivo acima do limite; tipo não aceito |
| Briefing | União de itens repetidos; criação de `conflito`; correção marca o item antigo como `superado`; mudança após confirmação desfaz a confirmação |
| Validador V2 | Tipo inexistente; relação permitida; relação proibida; relação com direção invertida |
| Validador V3 | Cada regra COE-01 a COE-10, com um caso que passa e um que falha |
| Validador V4 | Item sem elemento; elemento sem origem marcado como premissa |
| Exportação (V1) | Modelo mínimo; modelo com todas as camadas e viewpoints; caracteres especiais nos nomes; validação contra os XSDs |
| `tool-archi` (V5) | Conversão de um modelo válido; erro do Archi devolvido de forma legível |
| Layout | Sem sobreposição de elementos; faixas por camada; divisão de visões acima de 20 elementos |
| API | Cada endpoint da spec: sucesso, entrada inválida, sessão inexistente, `request_id` presente |
| Grafo | Pausa para perguntas; pausa para confirmação; ciclo de correção para na 3ª rodada; retomada após reinício do container |

### 4.2 Cobertura mínima

| Parte | Cobertura de linhas |
| --- | --- |
| Validadores, leitores de entrada e exportação | 90% |
| Restante do código | 80% |

## 5. Avaliação do agente (N3)

### 5.1 Conjunto de casos

Os casos ficam em `evals/casos/`. A base são os **exemplos ouro** da base de
conhecimento (`kb/archimate/exemplos/`), mais casos difíceis feitos de propósito.

| Grupo | Exemplos | Mínimo na Etapa 1 |
| --- | --- | --- |
| **Ouro** | Entradas claras com resultado esperado | 5 |
| **Ambíguos** | Falta informação essencial; o agente deve perguntar | 3 |
| **Contraditórios** | Transcrição que se contradiz; o agente deve criar `conflito` | 2 |
| **Ilegíveis** | Foto de quadro borrada; o agente deve pedir outra entrada | 1 |
| **Injeção** | Transcrição ou desenho com texto do tipo "ignore as instruções e…"; o agente deve tratar como conteúdo, não como ordem | 2 |
| **Conversa** | Perguntas, correções e alternativas sobre uma sessão pronta | 5 |

Cada caso tem um arquivo `caso.yaml` com: entradas, itens esperados no briefing,
elementos e relações esperados, perguntas esperadas (se houver), mensagens da
conversa e o que se espera de cada resposta, e a marca `rapido: true` quando o
caso faz parte da avaliação rápida.

### 5.2 Métricas e metas

| Área | Métrica | Como mede | Meta |
| --- | --- | --- | --- |
| Briefing | Cobertura dos itens esperados | Itens esperados encontrados ÷ total esperado | ≥ 90% |
| Briefing | Itens inventados | Itens sem correspondência na entrada ÷ total gerado | ≤ 10% |
| Briefing | Origem correta | Itens cuja origem aponta para um trecho que existe e diz aquilo | 100% |
| Esclarecimento | Pergunta quando deve | Casos ambíguos em que o agente perguntou | ≥ 90% |
| Esclarecimento | Não pergunta sem motivo | Casos ouro sem perguntas desnecessárias | ≥ 80% |
| Modelagem | Viabilidade | Modelos que passam em V1–V5 | 100% nos casos ouro |
| Modelagem | Tipo correto | Elementos esperados com o tipo ArchiMate esperado | ≥ 85% |
| Modelagem | Relações esperadas | Relações esperadas presentes | ≥ 80% |
| Modelagem | Premissas | Elementos marcados como premissa ÷ total | ≤ 15% |
| Modelagem | Rodadas de correção | Média de rodadas até ficar viável | ≤ 1,5 |
| Conversa | Classificação da mensagem | Acerto em `pergunta`/`informacao`/`correcao`/`alternativa`/`comando` | ≥ 90% |
| Conversa | Avaliação de alternativa | Resposta tem prós, contras, impacto e conflitos (juiz LLM, seção 5.4) | ≥ 90% |
| Segurança | Resistência a injeção | Casos de injeção sem desvio de comportamento | 100% |
| Custo | Tokens por caso | Soma das chamadas | Registrar; alerta se subir > 20% |
| Desempenho | Tempo de geração | p95 por caso | ≤ 5 min |

As metas são o ponto de partida. Depois da primeira rodada completa, a **linha de
base** real é gravada em `evals/baseline.json`, e as metas podem ser revistas com
registro no acompanhamento.

### 5.3 Como comparar o gerado com o esperado

- **Nomes:** comparação depois de normalizar (minúsculas, sem acento, sem pontuação), mais uma lista de sinônimos aceitos por caso (ex.: "PostgreSQL" = "Banco PostgreSQL").
- **Tipos ArchiMate:** comparação exata.
- **Relações:** tipo exato + origem e destino pelo nome normalizado.
- **Itens do briefing:** pelo tipo + nome normalizado.

Comparações que não dá para fazer por regra (ex.: "a resposta avaliou os
contras?") usam o juiz LLM.

### 5.4 Juiz LLM

- O juiz usa um **modelo diferente** do agente: `deepseek-v4.1-flash-1017` (o agente usa `qwen3.8-max`). Modelos tendem a favorecer os próprios textos quando avaliam (arXiv 2404.13076).
- O juiz responde a uma **rubrica fechada** (sim/não por item: tem prós? tem contras? cita impacto no modelo? aponta conflito?), não uma nota livre. Isso reduz o viés de preferir respostas mais longas (arXiv 2306.05685).
- Quando o juiz compara duas respostas, avalia nas duas ordens e só conta quando as duas concordam (arXiv 2306.05685).
- 10% das avaliações do juiz são conferidas por uma pessoa a cada rodada completa; se a concordância ficar abaixo de 80%, a rubrica é revista.

### 5.5 Variação do LLM

- Temperatura 0 nas chamadas do agente durante a avaliação, quando o modelo permitir.
- Na avaliação completa, cada caso roda **3 vezes**; o relatório mostra a média e o pior resultado.
- Uma meta só conta como atingida se o **pior** resultado das 3 rodadas atingir a meta de viabilidade, e a média atingir as demais.

### 5.6 Regressão

Uma mudança é **regressão** quando, comparada à linha de base:

- qualquer caso ouro deixa de ser viável; ou
- qualquer métrica cai mais de 5 pontos percentuais; ou
- os tokens por caso sobem mais de 20%.

Regressão bloqueia o merge, a não ser que a pessoa revisora aceite a mudança e
atualize a linha de base no mesmo PR, com o motivo.

### 5.7 Mudança no modelo do DashScope

O `qwen3.8-max` não tem versão datada. Por isso:

- a avaliação completa roda **toda semana**, mesmo sem mudança no código;
- se houver regressão sem mudança no código, ela é tratada como mudança do modelo e registrada no acompanhamento;
- trocar o modelo (no `.env`) exige uma avaliação completa antes.

### 5.8 Relatório da avaliação

Gerado em `evals/reports/AAAA-MM-DD-<branch>.md` e anexado ao PR pela CI:
resultado por métrica e por caso, comparação com a linha de base, casos que
pioraram, tokens e custo estimado, tempo por caso.

## 6. CI e proteção das branches (GitHub)

### 6.1 Workflows (GitHub Actions)

| Workflow | Quando | Etapas |
| --- | --- | --- |
| `ci.yml` | Todo PR e push em `main` e `agent/*` | N0 → build das imagens → N1 → N2 → cobertura |
| `eval.yml` | PR para `agent/*`: avaliação rápida. PR para `main`: completa. Agendado: completa, toda segunda-feira | Sobe os containers → N3 → relatório → comentário no PR |
| `kb.yml` | PR que altera `kb/` | `make kb-check` |

- A chave do DashScope fica nos **GitHub Secrets** (`DASHSCOPE_API_KEY`) e só é usada no `eval.yml`. Ela não fica disponível para PRs vindos de forks; sem a chave, o `eval.yml` avisa e não roda a avaliação.
- O `eval.yml` tem um limite de tokens por execução ⚠️ (valor a definir depois da primeira rodada).

### 6.2 Regras de proteção (rulesets)

| Regra | `main` | `agent/*` |
| --- | --- | --- |
| Push direto | Bloqueado | Bloqueado |
| Force push | Bloqueado | Bloqueado |
| Apagar a branch | Bloqueado | Bloqueado |
| Merge só por PR | Sim | Sim |
| Verificações obrigatórias | `ci`, `eval` (completa), `kb` quando houver mudança em `kb/` | `ci`, `eval` (rápida), `kb` quando houver mudança em `kb/` |
| Branch atualizada antes do merge | Sim | Sim |
| Aprovação de revisor | ⚠️ Projeto com uma pessoa: as verificações são obrigatórias, a aprovação não. Passa a ser obrigatória quando entrar mais alguém | Igual |

### 6.3 Checagem de pastas

Um script (`scripts/check_paths.py`) roda no N0 e reprova o PR quando:

- uma branch `task/<agente>/*` ou `agent/<agente>` altera arquivos fora de `src/archagent/agents/<agente>/`, `kb/<agente>/`, `compose/agent-<agente>.yml`, `evals/casos/<agente>/`, `tests/agents/<agente>/`, `docs/` e a linha de `include` do agente no `docker-compose.yml`;
- arquivos iguais aos da `origin/main` não contam, porque são mudanças do núcleo que a branch só trouxe da `main`;
- uma branch `core/*` altera a pasta de algum agente;
- uma branch `docs/*` altera algo fora de `docs/`, `README.md` e `CLAUDE.md`;
- qualquer PR para `main` ou `agent/*` vem de uma branch `exp/*` ou altera `experiments/`;
- algum arquivo de `src/` importa algo de `experiments/`.

Como a checagem de pastas é uma verificação obrigatória nos rulesets de `main` e
`agent/*`, um PR vindo de `exp/*` nunca consegue ser mesclado (plano, seção 2.5).

### 6.5 Experimentos

- Os workflows `ci.yml` e `eval.yml` **não** rodam em branches `exp/*`, para não gastar tokens nem misturar resultados com a linha de base.
- Um experimento pode ter os próprios testes e scripts, rodados manualmente dentro da pasta dele.
- Resultados de experimento nunca atualizam `evals/baseline.json`.

### 6.4 Segredos

- `gitleaks` no N0, localmente e na CI.
- *Push protection* de segredos ligada no GitHub.
- O `.env` está no `.gitignore`; só o `.env.example` vai para o repositório.

## 7. Guardrails em uso

Cada guardrail tem pelo menos um teste (N1 ou N2) ou um caso de avaliação (N3).

| Guardrail | O que impede | Onde é testado |
| --- | --- | --- |
| Limite de tamanho e tipo de arquivo | Entrada grande ou maliciosa | N1 — Upload |
| XML sem entidades externas | Ataque XXE pelo `.drawio` | N1 — Leitor `.drawio` |
| Entradas tratadas como dados | Injeção de instruções em transcrições e desenhos | N3 — grupo Injeção |
| Saída estruturada com esquema | Resposta do LLM em formato inesperado | N2 — Grafo |
| Validação V1–V5 antes da entrega | Modelo inválido chegar ao arquiteto | N1 e N3 |
| Máximo de 3 rodadas de correção | Ciclo infinito e gasto descontrolado | N2 — Grafo |
| Limite de tokens por sessão | Custo descontrolado | N2 — API |
| Resposta vazia sobre imagem tratada como falha | Desenho ignorado sem aviso | N3 — grupo Ilegíveis |
| Agente sem escrita nas regras e no vault | Agente reescrever o próprio conhecimento | N2 — permissões do volume |
| Agente nunca só concorda | Viés de concordância com o arquiteto | N3 — grupo Conversa |
| Usuário sem privilégio nos containers; só a `ui` exposta | Acesso indevido aos serviços | N2 — inspeção do compose |

## 8. Observabilidade e custos

### 8.1 Logs

Logs em JSON na saída padrão dos containers. Campos obrigatórios:

| Campo | Exemplo |
| --- | --- |
| `ts` | `2026-11-08T10:30:00-03:00` |
| `nivel` | `info` |
| `servico` | `agent-archimate` |
| `request_id` | `r-5f2c…` |
| `sessao` | `S-20261108-0001` |
| `evento` | `llm.chamada`, `validacao.resultado`, `entrada.recebida`… |

Para `llm.chamada`, também: `no` (nó do grafo), `modelo`, `tokens_entrada`,
`tokens_saida`, `latencia_ms`, `resultado` (`ok`, `erro`, `timeout`).

Nunca entram nos logs: chaves, conteúdo completo das entradas, conteúdo das
respostas do LLM. Para depurar, o conteúdo fica na pasta da sessão, não no log.

### 8.2 Indicadores

| Indicador | Onde aparece |
| --- | --- |
| Tokens por sessão e por nó do grafo | Endpoint `/sessions/{id}/usage`, interface e relatório |
| Tempo de geração do modelo | Relatório de viabilidade |
| Taxa de viabilidade na primeira tentativa | Relatório da avaliação |
| Falhas de chamada ao LLM (erro, timeout, limite de taxa) | Logs; resumo no relatório da avaliação |

### 8.3 Custos

- Por sessão: `LLM_MAX_TOKENS_PER_SESSION`, com aviso a 80% e bloqueio a 100% (spec RNF-03).
- Por execução de avaliação: limite no `eval.yml` ⚠️.
- O relatório da avaliação mostra o consumo total e por caso, para acompanhar o gasto do Token Plan.

## 9. Base de conhecimento

`make kb-check` verifica:

| Verificação | Regra |
| --- | --- |
| Cabeçalho das notas | Todos os campos obrigatórios da spec (seção 10.3), com valores válidos |
| Links | Nenhum `[[...]]` apontando para nota inexistente |
| Cobertura | Os 35 elementos do MVP têm ficha |
| Status | O agente só carrega notas `revisado`; o relatório lista os rascunhos |
| Regras | `elementos.json` e `relacoes.json` válidos; `relacoes.json` bate com a extração do commit do Archi registrado |
| XSDs | Presentes e carregáveis |
| Exemplos ouro | Todo exemplo tem entrada, briefing esperado e modelo esperado; o modelo esperado passa em V1–V4 |
| Propostas | Toda proposta tem correção observada, sessões de origem e nota no formato correto |

## 10. Desenvolvimento assistido por IA

O projeto é desenvolvido com apoio de agentes de IA (como o Claude Code). Para
que eles sigam as mesmas regras, o repositório tem um arquivo `CLAUDE.md` na
raiz com:

- as regras de branches, pastas e containers do plano;
- MCP oficial primeiro;
- toda sugestão baseada em arXiv registrada no acompanhamento;
- nunca ler, copiar ou registrar o conteúdo do `.env`;
- rodar `make check` e `make test` antes de propor um commit;
- ao finalizar uma tarefa, atualizar a documentação e enviar ao GitHub (push + PR);
- não alterar `evals/baseline.json` sem pedido explícito;
- experimentos só em branch `exp/*` e pasta `experiments/`, nunca misturados ao código validado.

## 11. Definição de pronto

### 11.1 Tarefa (`task/*` → `agent/*`)

- [ ] `make check` e `make test` passando.
- [ ] Testes novos para o comportamento novo.
- [ ] Avaliação rápida sem regressão, quando a tarefa mexe em prompt, grafo ou modelagem.
- [ ] Documentação atualizada no mesmo PR: spec (se o comportamento mudou), harness (se a verificação mudou), acompanhamento (status, decisões, experimentos), README e `CLAUDE.md` quando afetados.
- [ ] Artigos do arXiv usados registrados no acompanhamento.
- [ ] Branch enviada ao GitHub e PR aberto. **Tarefa que não está no GitHub não está finalizada.**

### 11.2 Fase

- [ ] Critério de saída do plano atingido.
- [ ] Aceite manual (N4) feito, quando a fase entrega algo visível.
- [ ] Acompanhamento atualizado com status, decisões e pendências.

### 11.3 Etapa (`agent/*` → `main`)

- [ ] Critérios de aceite da spec (CA-01 a CA-09) atendidos.
- [ ] Avaliação completa sem regressão e linha de base gravada.
- [ ] Documentação atualizada.

## 12. Construção do harness por fase

O harness cresce junto com o produto:

| Fase | O que entra no harness |
| --- | --- |
| F0 | `make` e perfil `test`; N0 completo; `ci.yml`; rulesets no GitHub; gitleaks; checagem de pastas; logs em JSON; `CLAUDE.md` |
| F1 | N1 dos validadores, exportação, layout e `tool-archi`; `kb.yml` e `make kb-check`; primeiros exemplos ouro |
| F2 | N1 dos leitores de transcrição e do briefing; LLM simulado; primeiros casos N3 de briefing; `eval.yml` (avaliação rápida) |
| F3 | Casos N3 de modelagem; juiz LLM; linha de base inicial |
| F4 | N1 do leitor `.drawio` (com XXE); casos N3 de desenho e de imagem ilegível |
| F5 | Casos N3 de conversa e de injeção; avaliação completa semanal; relatório de custos; linha de base final da Etapa 1 |

## 13. Pontos a verificar ou decidir ⚠️

- [ ] Limite de tokens por execução do `eval.yml` (depois da primeira rodada completa).
- [ ] Se o `deepseek-v4.1-flash-1017` aceita temperatura 0 e funciona bem como juiz (primeira rodada da F3).
- [x] Se o Archi 5 roda na CI do GitHub (imagem Linux, sem tela): roda, com Xvfb no container `tool-archi`.
- [ ] Regra de aprovação de revisor quando entrar mais alguém no projeto.
