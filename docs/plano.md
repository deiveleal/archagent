# Plano do Projeto — ArchAgent

> Status: **v1.0 — aprovado para a spec** · Data: 2026-11-08 · Responsável: Deive Leal

## 1. Visão

O ArchAgent é um agente de **análise e orientação** de arquitetura. Ele interpreta
**desenhos**, **transcrições de reunião**, **mensagens do arquiteto** e, mais adiante,
o **código** de uma aplicação para apoiar a criação, a alteração, o desenvolvimento
e a correção de bugs.

O agente **não escreve nem altera código**. Ele entrega modelos de arquitetura,
análises e recomendações que a equipe usa para decidir e implementar.

A conversa com o arquiteto é contínua: ele pode fazer perguntas, propor
possibilidades, trazer contexto ou corrigir o entendimento do agente a qualquer
momento. O agente usa essas mensagens como entrada da mesma forma que usa um
desenho ou uma transcrição.

## 2. Estratégia: passo a passo

O projeto cresce em etapas. Cada etapa entrega algo usável e só começa quando a
anterior foi validada.

| Etapa | Foco | O que valida |
| --- | --- | --- |
| **1 — MVP ArchiMate** | Entradas → briefing → modelo ArchiMate viável → abrir no Archi | O processo de entrada de informação e a criação de uma arquitetura viável |
| 2 — Leitura de código | Mapear a arquitetura real de um repositório e comparar com o modelo | O entendimento do código existente |
| 3 — Análise e recomendações | Melhoria, manutenção, sugestão de desenvolvimento, boas práticas, diagnóstico de bug | A utilidade das recomendações |
| 4 — Outras ferramentas e métodos | drawio, C4, Mermaid, ADR e outras notações e ferramentas | A generalização da saída |

**Este plano detalha a Etapa 1.** As etapas seguintes são descritas na seção 7 e
serão detalhadas quando a Etapa 1 for concluída.

### 2.1 Branches por agente

Cada agente é desenvolvido na **sua própria branch protegida**. Assim, o trabalho
num agente não quebra outro, e nada chega à `main` sem passar pelas verificações.

| Branch | Para que serve | Proteção |
| --- | --- | --- |
| `main` | Versão estável: documentação, núcleo compartilhado e agentes já validados | Sem push direto; só entra por PR com verificações aprovadas; sem force push; não pode ser apagada |
| `agent/<nome>` (ex.: `agent/archimate`) | Integração de um agente | As mesmas regras da `main`; só recebe PR das branches de tarefa daquele agente |
| `task/<nome>/<descricao>` (ex.: `task/archimate/f1-tabela-relacoes`) | Trabalho do dia a dia num agente | Livre; apagada depois do merge |
| `core/<descricao>` | Mudanças no núcleo compartilhado (provedor LLM, leitura das entradas, briefing) | Livre; PR direto para a `main` |
| `docs/<descricao>` | Mudanças só de documentação (`docs/`, README, `CLAUDE.md`) | Livre; PR direto para a `main` |
| `exp/<AAAA-MM-DD>-<assunto>` | Experimentos para validar hipóteses (seção 2.5) | Livre; **nunca** recebe merge em `main` nem em `agent/*`; não é apagada |

#### Regras das branches

- Uma branch de agente só altera a pasta do próprio agente (ex.: `src/archagent/agents/archimate/`) e a sua parte da base de conhecimento (ex.: `kb/archimate/`).
- O código compartilhado entre agentes muda só por `core/*`, direto na `main`. As branches de agente trazem essas mudanças da `main` com frequência.
- Um agente vai para a `main` quando a etapa dele fecha: critérios de saída atendidos e harness sem regressão.
- As verificações exigidas em todo PR são as definidas no harness (`docs/harness.md`): no mínimo ruff, mypy, pytest e a avaliação do agente afetado.
- **Toda tarefa finalizada sobe para o GitHub e atualiza a documentação.** Uma tarefa só é considerada finalizada quando: (1) a documentação afetada (`docs/`, README, `CLAUDE.md`) foi atualizada no mesmo commit ou PR; (2) a branch foi enviada (push) ao GitHub; (3) o PR foi aberto ou mesclado, conforme o tipo de branch. Nada fica só na máquina local.
- O repositório fica no **GitHub**. A proteção é configurada com *rulesets* do GitHub nas branches `main` e `agent/*`, e as verificações rodam no GitHub Actions.

### 2.2 Integração com ferramentas: MCP oficial primeiro

Sempre que uma ferramenta tiver **servidor MCP oficial** (publicado por quem mantém a
ferramenta), o agente usa esse MCP em vez de uma integração própria. Os MCPs são
consumidos no LangGraph pelo `langchain-mcp-adapters`.

A ordem de preferência é:

1. MCP oficial da ferramenta.
2. Formato de arquivo padrão e aberto, com geração e validação próprias.
3. MCP da comunidade, só depois de avaliar manutenção, licença e segurança, e registrar a decisão.

| Ferramenta | MCP oficial? | Decisão |
| --- | --- | --- |
| Archi / ArchiMate | **Não.** Existem só MCPs da comunidade, como o `archimate-mcp` | Etapa 1 usa o Open Exchange Format com geração e validação próprias. Os MCPs da comunidade podem ser avaliados, mas não substituem a validação própria |
| draw.io | **Sim:** `jgraph/drawio-mcp` (Apache-2.0), da equipe do draw.io | Usado quando o agente gerar ou abrir diagramas drawio (Etapa 4). A leitura de `.drawio` como entrada continua sendo feita pelo parser do XML |
| GitHub | **Sim:** `github/github-mcp-server` | Usado quando um agente precisar consultar repositórios, branches ou PRs no GitHub |

Esta tabela é revisada no início de cada etapa, porque novos MCPs oficiais podem surgir.

### 2.3 Tudo em containers

Todo agente e toda ferramenta roda no **seu próprio container**. Assim, cada um
pode ser construído, atualizado, testado e reiniciado sem mexer nos outros.

| Serviço | Container | Observação |
| --- | --- | --- |
| Interface | `ui` (Streamlit) | Não contém lógica de agente; conversa com os agentes por HTTP |
| Agente ArchiMate | `agent-archimate` | LangGraph exposto por uma API FastAPI; traz a base `kb/archimate/` e os validadores |
| Archi | `tool-archi` | Archi 5 pela linha de comando, sem interface gráfica: converte o Exchange Format em `.archimate` e confirma que o modelo abre (V5) |
| MCPs | um container por MCP (ex.: `mcp-drawio` com a imagem oficial `jgraph/drawio-mcp`) | Entram à medida que as etapas precisam deles |
| Próximos agentes | `agent-<nome>` | Cada novo agente ganha o seu container, na sua branch |

#### Regras dos containers

- Cada agente tem o seu `Dockerfile` e o seu arquivo de compose (ex.: `compose/agent-archimate.yml`), incluídos no `docker-compose.yml` principal. Os dois ficam na branch do agente.
- O núcleo compartilhado é um pacote Python instalado na imagem de cada agente. Ele não é copiado de um agente para outro.
- A configuração vem só de variáveis de ambiente (modelo LLM, endereços dos serviços, chaves como `DASHSCOPE_API_KEY`). Nada fica fixo no código, e as chaves nunca entram no repositório nem na imagem.
- Todo container tem healthcheck e uma versão de imagem identificada.
- As sessões e os arquivos gerados ficam em volumes. Na Etapa 2, os repositórios analisados entram como volume **somente leitura** (`:ro`).
- Os serviços conversam numa rede interna do compose. Só a interface fica exposta para fora.
- Os testes e o harness rodam dentro dos containers, do mesmo jeito localmente e na CI.

### 2.4 Base de conhecimento por agente

Cada agente tem a sua base de conhecimento, separada por **tipo de uso**. A
separação segue a divisão de memória semântica, episódica e procedural do CoALA
(arXiv 2309.02427). Os artigos que embasam cada parte estão registrados no
acompanhamento.

| Parte | O que guarda | Formato | Quem escreve | Base no arXiv |
| --- | --- | --- | --- | --- |
| **1. Regras** | Metamodelo, relações permitidas, esquemas de validação | JSON + validadores em código; nunca só no prompt | Script (ex.: extraído do Archi) | 2607.26100, 2510.25890 |
| **2. Vault** | Fichas dos elementos, padrões, anti-padrões, convenções | Notas Markdown curtas, com cabeçalho de metadados e links `[[...]]`, compatíveis com Obsidian | Pessoa, revisada por PR | 2502.12110 |
| **3. Exemplos ouro** | Pares entrada → resultado esperado | Pasta de casos; os mesmos casos alimentam o harness | Pessoa | — |
| **4. Memória das sessões** | Entradas, briefing, decisões e correções, com origem e data. Um fato corrigido é marcado como superado, não apagado | Arquivos por sessão, num volume do container | Agente | 2501.13956 |
| **5. Aprendizados propostos** | Correções que se repetem viram sugestões de nota nova para o vault | Rascunhos em `propostas/` | Agente propõe; pessoa aprova por PR | 2502.12110, 2309.02427 |

#### Regras da base de conhecimento

- `kb/core/` guarda o que vale para todos os agentes (glossário do negócio, convenções gerais). `kb/<agente>/` guarda o que é só daquele agente. Cada branch de agente só altera a própria pasta.
- As **regras** são consultadas por ferramenta e pelos validadores, nunca por busca semântica.
- O **vault** é consultado por busca híbrida (por palavra e por embeddings), seguindo os links entre as notas. Enquanto for pequeno, o resumo inteiro pode ir no contexto do modelo.
- O agente **nunca altera** o vault nem as regras diretamente; ele só propõe, e uma pessoa aprova (arXiv 2309.02427 alerta para o risco de o agente reescrever o próprio conhecimento).
- O vault e as regras ficam versionados no git. A memória das sessões fica em volume, fora do git.
- GraphRAG ou serviços de memória como o Zep só entram se o harness mostrar que a busca simples deixou de bastar (arXiv 2506.05690).

### 2.5 Experimentos isolados

Experimentos para validar hipóteses são bem-vindos, mas **não podem contaminar o
código pronto e validado**.

| Regra | Como |
| --- | --- |
| Branch própria | Todo experimento vive numa branch `exp/<AAAA-MM-DD>-<assunto>`, criada a partir da `main` |
| Pasta própria | Dentro da branch, o código fica só em `experiments/<AAAA-MM-DD>-<assunto>/`, com as suas próprias dependências |
| Container próprio, se precisar | Perfil `exp` do compose; nunca altera os containers dos agentes |
| Sem mistura | Código de `src/` nunca importa nada de `experiments/`; experimento nunca altera `src/`, `kb/`, `evals/` nem `compose/` dos agentes |
| Sem merge | A branch `exp/*` nunca é mesclada em `main` nem em `agent/*`; fica guardada para consulta e reprodução |
| Registro | Cada experimento tem um `README.md` com hipótese, método, resultado e decisão, e é registrado na seção "Experimentos" do acompanhamento. Se usar artigo do arXiv, o artigo também é registrado |
| Promoção | Se a hipótese for confirmada, a solução é **reimplementada** numa branch `task/*` ou `core/*`, com testes, passando por todo o harness. Nada é copiado direto do experimento sem esse caminho |
| Segredos | Experimentos usam o mesmo `.env`, sem copiar a chave para arquivos do experimento |

## 3. Etapa 1 — MVP ArchiMate

### 3.1 Objetivo

Receber informação de arquitetura em diferentes formatos e transformá-la num
**modelo ArchiMate viável**, que abre no **Archi 5** sem erro e representa o que foi
pedido.

### 3.1.1 Formato de saída

O formato de saída **depende do que está sendo montado**. Cada agente declara na
spec os formatos que suporta e quando usa cada um.

O `agent-archimate` entrega **os dois formatos**, gerados assim:

1. O agente gera o **Open Group ArchiMate Exchange Format** (XML) e valida contra os XSDs oficiais.
2. O container `tool-archi` roda o **Archi 5 pela linha de comando**: importa o Exchange Format e salva o **`.archimate`** nativo.
3. Se o Archi não conseguir importar ou salvar, o modelo é reprovado em V5 e volta para correção.

Assim, o agente só mantém um gerador (o do Exchange Format). Quem produz o
`.archimate` é o próprio Archi, o que evita diferenças entre os dois arquivos.
A linha de comando do Archi rodando em container é verificada logo no início da F1.

### 3.2 Fluxo

```text
Entradas: desenho / transcrição / mensagem do arquiteto
  → Interpretação: extrai requisitos, atores, processos, sistemas, dados,
    infraestrutura, decisões, hipóteses e pendências (briefing)
  → Esclarecimento: pergunta o que estiver ambíguo ou faltando
  → Modelagem: converte o briefing em elementos e relações ArchiMate
  → Validação: confere sintaxe, regras do ArchiMate, coerência e cobertura
    (se falhar, o agente corrige e valida de novo)
  → Exportação: gera o arquivo para o Archi, com as visões
  → Entrega: arquivo + relatório de viabilidade (o que foi modelado, de onde
    veio cada elemento, lacunas e premissas)
  ↺ Conversa: o arquiteto pergunta, sugere alternativas ou corrige; o agente
    atualiza o briefing e o modelo
```

### 3.3 O que é uma "arquitetura viável"

Um modelo é considerado viável quando passa nos cinco critérios abaixo:

| # | Critério | Como é verificado |
| --- | --- | --- |
| V1 | **Válido no formato** | O Exchange Format passa na validação dos XSDs oficiais |
| V2 | **Válido no ArchiMate** | Todos os tipos de elemento existem e todas as relações são permitidas pela especificação ArchiMate 3.2 |
| V3 | **Coerente** | Não há elementos soltos; as camadas se ligam (ex.: serviço de aplicação realizado por componente, componente apoiado por tecnologia) |
| V4 | **Cobre a entrada** | Cada requisito do briefing aponta para pelo menos um elemento; cada elemento aponta para a sua origem na entrada |
| V5 | **Abre no Archi** | Automático: o Archi 5 (`tool-archi`) importa o Exchange Format e salva o `.archimate` sem erro. Manual, na revisão: as visões aparecem legíveis |

### 3.4 Objetivos da Etapa 1

| # | Objetivo | Como saber que foi atingido |
| --- | --- | --- |
| O1 | Interpretar texto do arquiteto e transcrições | O briefing cobre os requisitos e decisões das entradas de exemplo |
| O2 | Interpretar desenhos | Os componentes e ligações de `.drawio` e de imagens aparecem corretamente no briefing |
| O3 | Esclarecer antes de modelar | Nas entradas ambíguas, o agente pergunta em vez de inventar |
| O4 | Gerar modelo ArchiMate viável | Os modelos de exemplo passam nos critérios V1 a V5 |
| O5 | Refinar pela conversa | As correções e alternativas do arquiteto são incorporadas no modelo sem quebrar a viabilidade |

### 3.5 Escopo da Etapa 1

#### Dentro

- Entradas de **texto do arquiteto**: perguntas, propostas, informações e correções, em conversa contínua.
- Entradas de **transcrição**: `.txt`, `.vtt`, `.srt`, `.md` e `.docx`.
- Entradas de **desenho**: `.drawio` e imagens (PNG/JPG de diagramas, fotos de quadro branco).
- Sessão de trabalho que reúne as entradas, o briefing, o modelo e o histórico da conversa.
- Camadas ArchiMate: **Negócio, Aplicação e Tecnologia**. Motivação, Estratégia, Implementação e Física ficam para depois.
- Visões geradas a partir dos **viewpoints oficiais do ArchiMate**: *Layered* (visão geral), *Business Process Cooperation*, *Application Cooperation* e *Technology Usage*. Só são geradas as visões que tiverem elementos.
- Convenções de modelagem (nomes, propriedades, cores) baseadas em **guias públicos** (especificação ArchiMate e *ArchiMate Cookbook*), ajustadas conforme a revisão dos modelos gerados.
- Entrega em Exchange Format e `.archimate`, como descrito na seção 3.1.1.
- Relatório de viabilidade em Markdown.

#### Fora

- Leitura de código-fonte (Etapa 2).
- Recomendações de melhoria e diagnóstico de bug (Etapa 3).
- Outras notações e ferramentas (Etapa 4).
- Partir de um modelo `.archimate` existente, seja para ler ou para alterar. O MVP sempre gera um modelo novo; essa é a primeira evolução prevista depois da Etapa 1.
- Abrir o Archi com interface gráfica para a pessoa; ela abre o `.archimate` entregue.

### 3.6 Stack da Etapa 1

| Tema | Escolha |
| --- | --- |
| Linguagem | Python 3.13, gerenciado com `uv` |
| Orquestração do agente | LangGraph (grafo com ciclo validar → corrigir) |
| Provedor LLM | **Alibaba Cloud Model Studio (DashScope)**, pela API compatível com OpenAI |
| Endpoint | Token Plan, região Singapura (`ap-southeast-1`), configurado no `.env` |
| LLM de interpretação e modelagem | `qwen3.8-max` |
| LLM de visão (desenhos em imagem) | `qwen3.8-max` (o mesmo modelo, que aceita imagem) |
| Alternativa rápida | `deepseek-v4.1-flash-1017`, candidato para etapas simples, a confirmar no harness |
| Ferramenta de modelagem | Archi 5; a linha de comando dele roda no container `tool-archi` |
| Leitura de `.drawio` | Parser do XML, sem LLM |
| Modelo interno | Classes Pydantic para elementos, relações e visões ArchiMate |
| Regras do ArchiMate | Tabela de relações permitidas da especificação 3.2, carregada como dados |
| Geração e validação dos arquivos | `lxml` + XSDs oficiais do Exchange Format |
| Layout das visões | Layout automático por viewpoint, organizado por camada |
| Interface | Streamlit: conversa, upload das entradas, briefing, download do modelo e do relatório |
| Integrações | MCP oficial quando existir (seção 2.2), via `langchain-mcp-adapters` |
| Execução | Docker Compose, um container por agente e por ferramenta (seção 2.3) |
| Comunicação interface ↔ agente | API HTTP com FastAPI no container de cada agente |
| Repositório e CI | GitHub + GitHub Actions |
| Qualidade | Definida no harness: pytest, ruff, mypy e avaliação dos agentes, rodando nos containers |

### 3.7 Fases da Etapa 1

| Fase | Entregas | Critério de saída |
| --- | --- | --- |
| **F0 — Fundação** | Repositório no GitHub com rulesets, estrutura do projeto, `pyproject`, lint/testes, containers `ui` e `agent-archimate`, compose principal com os arquivos por agente, cliente DashScope, CI no GitHub Actions, README | `docker compose up` sobe os containers saudáveis; a `ui` fala com o agente; o agente recebe resposta do DashScope; a CI roda e bloqueia PR com falha |
| **F1 — Base de conhecimento, modelo ArchiMate e validação** | Base de conhecimento (`kb/core/` e `kb/archimate/`, seção 2.4): regras (metamodelo e tabela de relações extraídos do Archi, XSDs), vault (fichas dos elementos do MVP, padrões e anti-padrões, convenções), exemplos ouro, estrutura da memória das sessões e da pasta de propostas, busca no vault. Classes do modelo, validadores V2 e V3, exportador Exchange Format com XSD (V1), layout dos viewpoints, container `tool-archi` com a conversão para `.archimate` (V5) | Fichas revisadas pelo arquiteto; um modelo montado à mão é exportado, passa em V1–V3 e o `tool-archi` gera o `.archimate`, que abre no Archi 5 (V5) |
| **F2 — Entrada por texto e transcrição** | Leitores de transcrição, conversa com o arquiteto, geração do briefing, perguntas de esclarecimento | Briefing correto para 5 entradas de texto/transcrição de exemplo |
| **F3 — Modelagem a partir do briefing** | Conversão briefing → modelo, ciclo validar → corrigir, rastreabilidade (V4), relatório de viabilidade | Os 5 exemplos geram modelos que passam em V1–V5 |
| **F4 — Entrada por desenho** | Leitor `.drawio`, leitura de imagens com modelo de visão, integração ao briefing | Desenhos de exemplo geram briefing e modelo viáveis |
| **F5 — Refinamento pela conversa e avaliação** | Atualização do modelo a partir de correções e alternativas, avaliação completa do agente no harness, linha de base de qualidade | As correções de exemplo são incorporadas mantendo V1–V5; a avaliação roda na CI e registra a linha de base |

O harness cobre o projeto inteiro e cresce junto com as fases: ambiente e CI na
F0, testes dos validadores na F1, avaliação das entradas e da modelagem da F2 em
diante.

A F1 vem antes das entradas de propósito: primeiro garantimos que conseguimos
produzir e validar um ArchiMate correto. Depois ligamos o LLM a essa base já testada.

Cada fase só começa quando o critério de saída da anterior foi atendido e
registrado no acompanhamento.

## 4. Artefatos de orientação

Todos ficam na pasta `docs/` e são produzidos nesta ordem, um de cada vez. Nesta
primeira versão, eles cobrem a Etapa 1.

| # | Artefato | Arquivo | Conteúdo |
| --- | --- | --- | --- |
| 1 | **Plano** (este documento) | `docs/plano.md` | O que vamos construir, em que ordem e com quais riscos |
| 2 | **Spec** | `docs/spec.md` | Requisitos, formato do briefing, modelo interno ArchiMate, regras de validação, formato do relatório, fluxos |
| 3 | **Harness** | `docs/harness.md` | Tudo o que garante a qualidade do projeto como um todo: ambiente em containers, testes, avaliação dos agentes, CI e proteção das branches, guardrails, observabilidade e custos |
| 4 | **Desenho de arquitetura** | `docs/arquitetura.drawio` | Componentes, fluxos e implantação do ArchAgent |
| 5 | **Acompanhamento** | `docs/acompanhamento.md` | Status das fases, decisões tomadas, pendências e **referências do arXiv**: toda sugestão baseada em artigo do arXiv tem o artigo registrado ali |

## 5. Riscos da Etapa 1

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| O LLM gera relações não permitidas pelo ArchiMate | Alto | Validar contra a tabela de relações e devolver o erro ao LLM para corrigir; limitar o número de tentativas |
| O LLM inventa elementos que não estão na entrada | Alto | Todo elemento precisa citar a origem (V4); os que não citam são marcados como premissa no relatório |
| O LLM escolhe o tipo de elemento errado (ex.: processo em vez de função) | Médio | Regras de escolha de tipo no prompt; exemplos no harness; o arquiteto corrige pela conversa |
| Desenho à mão ou foto ilegível | Alto | Mostrar o briefing para confirmação antes de modelar; pedir uma entrada melhor quando a confiança for baixa |
| Transcrição longa, confusa ou contraditória | Alto | Separar decisões, dúvidas e conflitos no briefing; perguntar antes de modelar |
| Visões ilegíveis no Archi | Médio | Layout por camada; limite de elementos por visão; dividir em mais visões quando passar do limite |
| Incompatibilidade com o Archi 5 | Médio | Testar a abertura e a importação no Archi 5 já na F1 |
| A linha de comando do Archi não roda bem em container sem tela | Médio | Verificar no início da F1; se precisar, usar tela virtual (Xvfb) no container. Último recurso: entregar só o Exchange Format e a importação no Archi passa a ser manual |
| API do DashScope indisponível, lenta ou com limite de taxa | Médio | Novas tentativas com espera crescente, tempo limite por chamada e mensagem clara na interface |
| Custo de API cresce sem controle | Médio | Limite de tokens por sessão, registro de consumo por chamada e alerta no harness |
| Dados enviados para a nuvem da Alibaba | Médio | Usar o endpoint internacional; não enviar dados sensíveis no MVP; avisar na interface que as entradas vão para a API |
| O `qwen3.8-max` não tem versão datada e pode mudar sem aviso | Médio | O harness roda periodicamente e detecta regressão; o modelo é trocado só por configuração |
| Modelo ignora a imagem e responde vazio sem dar erro (visto no `deepseek-v4-pro`) | Médio | O agente trata resposta vazia sobre um desenho como falha e avisa o arquiteto |
| Agente concorda com tudo que o arquiteto propõe | Médio | Toda alternativa avaliada traz prós e contras e aponta conflitos com o modelo |
| Muitos containers deixam o ambiente pesado | Baixo | Perfis do compose para subir só os agentes e ferramentas em uso |
| O escopo cresce antes do MVP fechar | Médio | Novas ideias vão para o backlog do acompanhamento, organizadas por etapa |

## 6. Decisões em aberto

Não há decisões abertas no plano. As próximas decisões, de detalhe, ficam na spec.

### Tomadas

- [x] Interface em Streamlit, falando com os agentes por API FastAPI.
- [x] MCP oficial tem prioridade sobre integrações próprias.
- [x] Um container por agente e por ferramenta.
- [x] Uma branch protegida por agente.
- [x] Repositório no GitHub.
- [x] Ferramenta de modelagem: Archi 5.
- [x] Formato de saída depende do que está sendo montado.
- [x] Harness cobre o projeto como um todo.
- [x] Provedor LLM: Alibaba Cloud Model Studio (DashScope), Token Plan em Singapura.
- [x] Modelo de texto e de visão: `qwen3.8-max`, escolhido em teste comparativo de 6 modelos (2026-11-08).
- [x] Saída do `agent-archimate`: Exchange Format gerado pelo agente + `.archimate` gerado pela linha de comando do Archi 5.
- [x] Camadas do MVP: Negócio, Aplicação e Tecnologia.
- [x] Visões: viewpoints oficiais (Layered, Business Process Cooperation, Application Cooperation, Technology Usage).
- [x] Convenções: guias públicos, ajustados com o uso.
- [x] O MVP sempre gera um modelo novo; partir de um modelo existente fica para depois da Etapa 1.
- [x] Base de conhecimento por agente em cinco partes: regras, vault, exemplos ouro, memória das sessões e aprendizados propostos (seção 2.4).
- [x] Toda sugestão baseada em artigo do arXiv tem o artigo registrado no acompanhamento.
- [x] Experimentos ficam isolados em branch e pasta próprias, sem merge no código validado (seção 2.5).
- [x] Toda tarefa finalizada sobe para o GitHub com a documentação atualizada (seção 2.1).

## 7. Etapas seguintes (visão)

**Etapa 2 — Leitura de código.** Ler um repositório local, só para leitura, e
mapear módulos, camadas, dependências e integrações. Comparar a arquitetura real
com o modelo ArchiMate.

**Etapa 3 — Análise e recomendações.** Relatórios de melhoria, manutenção,
sugestão de desenvolvimento, boas práticas e diagnóstico de bug. Cada
recomendação cita o trecho da entrada e o local do código. Classificação da
intenção: criar, alterar, desenvolver ou corrigir.

**Etapa 4 — Outras ferramentas e métodos.** Novas saídas (drawio, C4, Mermaid,
ADR) e novos métodos, reaproveitando o briefing e o modelo interno da Etapa 1.

Riscos já identificados para essas etapas: recomendações genéricas ou inventadas,
repositórios grandes demais para o contexto e envio de código sensível para APIs
externas.
