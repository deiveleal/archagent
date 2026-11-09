# Spec — ArchAgent · Etapa 1 (MVP ArchiMate)

> Status: **rascunho v0.1** · Data: 2026-11-08 · Responsável: Deive Leal
>
> Base: `docs/plano.md` v1.0. Os itens marcados com ⚠️ precisam ser verificados ou decididos.

## 1. Objetivo e escopo

Esta spec descreve **o que** o agente ArchiMate faz na Etapa 1 e **como** as partes
se comunicam. O porquê das escolhas está no plano.

Em resumo: o arquiteto envia desenhos, transcrições e mensagens. O agente monta um
**briefing**, esclarece dúvidas, gera um **modelo ArchiMate** das camadas de
Negócio, Aplicação e Tecnologia, valida o modelo (V1–V5) e entrega o
**Exchange Format**, o **`.archimate`** e um **relatório de viabilidade**.

## 2. Glossário

| Termo | Significado |
| --- | --- |
| **Sessão** | Unidade de trabalho: reúne entradas, briefing, conversa, modelo e entregas |
| **Entrada** | Arquivo ou mensagem enviada pelo arquiteto (desenho, transcrição, texto) |
| **Briefing** | Resumo estruturado do que foi extraído das entradas; cada item aponta para a sua origem |
| **Item do briefing** | Unidade do briefing (ator, sistema, requisito, decisão etc.), com id próprio |
| **Modelo** | Conjunto de elementos, relações e visões ArchiMate gerado a partir do briefing |
| **Viabilidade** | Aprovação nos critérios V1–V5 (seção 8) |
| **Premissa** | Elemento do modelo sem origem direta na entrada, criado pelo agente para completar o modelo |
| **Vault** | Notas Markdown da base de conhecimento (seção 10) |

## 3. Atores e casos de uso

**Atores:** Arquiteto (usuário da interface) e Revisor da base de conhecimento
(pode ser o próprio arquiteto).

| Id | Caso de uso | Resultado |
| --- | --- | --- |
| UC-01 | Criar sessão | Sessão vazia, pronta para receber entradas |
| UC-02 | Enviar entrada (arquivo ou texto) | Entrada registrada e interpretada; briefing atualizado |
| UC-03 | Responder perguntas de esclarecimento | Briefing atualizado com as respostas |
| UC-04 | Revisar e confirmar o briefing | Briefing marcado como confirmado; liberado para modelagem |
| UC-05 | Gerar o modelo | Modelo validado, arquivos gerados, relatório entregue |
| UC-06 | Baixar entregas | Exchange Format, `.archimate` e relatório |
| UC-07 | Corrigir ou propor alternativa | Briefing e modelo atualizados; alternativa avaliada com prós e contras |
| UC-08 | Fazer pergunta direta | Resposta com base na sessão, sem gerar modelo novo |
| UC-09 | Revisar aprendizados propostos | Proposta aceita (vira nota no vault por PR) ou descartada |

## 4. Requisitos funcionais

### 4.1 Sessão

| Id | Requisito |
| --- | --- |
| RF-SES-01 | O agente cria, lista e abre sessões. Cada sessão tem id, título, data de criação e status (`aberta`, `briefing_confirmado`, `modelo_gerado`) |
| RF-SES-02 | Tudo o que acontece numa sessão (entradas, briefing, conversa, modelos, validações) fica persistido e sobrevive ao reinício dos containers |
| RF-SES-03 | Cada nova geração de modelo cria uma nova **versão** do modelo; as anteriores continuam disponíveis para download |

### 4.2 Entradas

| Id | Requisito |
| --- | --- |
| RF-ENT-01 | Aceita **texto** digitado no chat |
| RF-ENT-02 | Aceita **transcrições** `.txt`, `.md`, `.vtt`, `.srt` e `.docx`. Em `.vtt` e `.srt`, preserva os tempos e, quando houver, o nome de quem falou |
| RF-ENT-03 | Aceita **desenhos** `.drawio` (inclusive o formato comprimido) e lê páginas, formas, textos, ligações e agrupamentos **sem LLM** |
| RF-ENT-04 | Aceita **imagens** `.png` e `.jpg` e as interpreta com o modelo de visão |
| RF-ENT-05 | Rejeita arquivos fora dos tipos aceitos ou acima do limite de tamanho (seção 12), com mensagem clara |
| RF-ENT-06 | Toda entrada recebe um id (`E-001`, `E-002`…) e fica guardada como foi enviada |
| RF-ENT-07 | Se a interpretação de uma imagem vier **vazia ou ilegível**, o agente trata como falha e pede uma entrada melhor (risco visto no teste de modelos) |

### 4.3 Briefing

| Id | Requisito |
| --- | --- |
| RF-BRI-01 | O agente extrai das entradas os itens do briefing nos tipos da seção 7.3 |
| RF-BRI-02 | Todo item aponta para a **origem**: id da entrada e local (linha, tempo, página/forma do desenho ou região da imagem) |
| RF-BRI-03 | Todo item tem **confiança** (`alta`, `media`, `baixa`) |
| RF-BRI-04 | Itens repetidos vindos de entradas diferentes são unidos num só item, com todas as origens |
| RF-BRI-05 | Informações conflitantes viram um item do tipo `conflito`, ligando os itens envolvidos; o agente não escolhe um lado sozinho |
| RF-BRI-06 | Uma correção do arquiteto **não apaga** o item antigo: o item é marcado como `superado`, com data e referência ao novo item |
| RF-BRI-07 | O arquiteto pode confirmar o briefing. A modelagem só começa com o briefing confirmado |
| RF-BRI-08 | Qualquer mudança depois da confirmação volta o briefing para "não confirmado" e exige nova confirmação antes de gerar outro modelo |

### 4.4 Esclarecimento

| Id | Requisito |
| --- | --- |
| RF-ESC-01 | O agente gera perguntas para itens de confiança `baixa`, `conflito`s e `pendencia`s que impeçam a modelagem |
| RF-ESC-02 | No máximo 5 perguntas por rodada, ordenadas por impacto no modelo |
| RF-ESC-03 | Cada pergunta indica o item do briefing a que se refere |
| RF-ESC-04 | O arquiteto pode pular perguntas; o item fica como `pendencia` e aparece no relatório |

### 4.5 Modelagem

| Id | Requisito |
| --- | --- |
| RF-MOD-01 | O agente converte o briefing confirmado em elementos e relações ArchiMate 3.2, usando só os tipos da seção 8.1 |
| RF-MOD-02 | A geração usa **saída estruturada** (chamada de ferramenta ou JSON com esquema), nunca texto livre |
| RF-MOD-03 | Todo elemento tem a lista de itens do briefing que o originaram. Elemento sem origem é marcado como **premissa** |
| RF-MOD-04 | Antes de escolher o tipo de um elemento, o agente consulta a ficha do vault correspondente |
| RF-MOD-05 | Antes de criar uma relação, o agente pode consultar a ferramenta de relações permitidas |
| RF-MOD-06 | Itens do tipo `pendencia` e `hipotese` não viram elementos definitivos; quando necessários, entram como premissa |
| RF-MOD-07 | O agente gera as visões pelos viewpoints da seção 8.4, só as que tiverem elementos |

### 4.6 Validação e correção

| Id | Requisito |
| --- | --- |
| RF-VAL-01 | Todo modelo passa por V1–V5 (seção 8) antes de ser entregue |
| RF-VAL-02 | Erros de validação voltam para o LLM com a mensagem exata e o elemento afetado, para correção |
| RF-VAL-03 | No máximo **3 rodadas** de correção. Se ainda houver erro, o modelo é entregue como **não viável**, com a lista de erros |
| RF-VAL-04 | Avisos (severidade `aviso`) não bloqueiam a entrega, mas aparecem no relatório |

### 4.7 Exportação e entregas

| Id | Requisito |
| --- | --- |
| RF-EXP-01 | O agente gera o Exchange Format e valida contra os XSDs oficiais (V1) |
| RF-EXP-02 | O agente envia o Exchange Format ao `tool-archi`, que devolve o `.archimate` (V5) |
| RF-EXP-03 | Os elementos ficam organizados nas pastas padrão do Archi (Business, Application, Technology, Relations, Views) |
| RF-EXP-04 | Cada elemento leva as propriedades `archagent:origem` (ids do briefing) e `archagent:premissa` (`sim`/`nao`) |
| RF-EXP-05 | O relatório de viabilidade é gerado em Markdown (seção 11) |

### 4.8 Conversa

| Id | Requisito |
| --- | --- |
| RF-CON-01 | Cada mensagem do arquiteto é classificada em: `pergunta`, `informacao`, `correcao`, `alternativa` ou `comando` |
| RF-CON-02 | `pergunta`: resposta com base na sessão e no vault, citando os itens do briefing ou elementos usados |
| RF-CON-03 | `informacao` e `correcao`: viram itens do briefing (RF-BRI-06 para correções) |
| RF-CON-04 | `alternativa`: o agente responde com **prós, contras, impacto no modelo e conflitos** com decisões anteriores. Nunca só concorda |
| RF-CON-05 | `comando`: ações explícitas (confirmar briefing, gerar modelo, regenerar) |
| RF-CON-06 | Quando o agente não souber, diz que não sabe e indica o que falta |

Implementação (F5): `POST /sessions/{id}/messages` roda o grafo
`classificar → responder | atualizar_briefing | avaliar_alternativa | comando`.
A pergunta é respondida com o briefing, o último modelo e até 3 notas do vault no contexto.
Informação e correção entram como nova entrada de texto (a correção usa `substitui` e deixa
o item antigo `superado`); se já existe modelo, o agente avisa que é preciso confirmar de
novo e gerar outra versão. A alternativa devolve prós, contras, impacto no modelo,
conflitos e recomendação, sem mudar o briefing. Os comandos aceitos são
`confirmar_briefing` e `gerar_modelo`. Mensagens do arquiteto e respostas do agente ficam
em `conversa.jsonl`.

### 4.9 Base de conhecimento

| Id | Requisito |
| --- | --- |
| RF-KB-01 | As regras (seção 10.2) são carregadas na inicialização; se estiverem ausentes ou inválidas, o agente não sobe |
| RF-KB-02 | O agente busca notas do vault por busca híbrida (palavra + embeddings) e segue os links `[[...]]` até 1 nível |
| RF-KB-03 | O agente **nunca** altera regras ou vault; ele grava propostas em `kb/archimate/propostas/` |
| RF-KB-04 | Uma correção do mesmo tipo feita pelo arquiteto em **3 sessões diferentes** gera uma proposta de nota. O "tipo" é o `tema` que o classificador dá à correção; o registro fica em `propostas/registro-correcoes.json` e a proposta em `propostas/AAAA-MM-DD-<tema>.md` |

## 5. Requisitos não funcionais

| Id | Categoria | Requisito |
| --- | --- | --- |
| RNF-01 | Desempenho | Pergunta direta: resposta em até 30 s (p95) |
| RNF-02 | Desempenho | Geração do modelo, para entrada típica (até 40 itens no briefing): até 5 min, com progresso visível |
| RNF-03 | Custo | Limite de tokens por sessão (`LLM_MAX_TOKENS_PER_SESSION`). Ao chegar a 80%, a interface avisa; a 100%, novas chamadas ao LLM são bloqueadas |
| RNF-04 | Resiliência | Chamadas ao LLM com tempo limite (`LLM_TIMEOUT_SECONDS`) e novas tentativas com espera crescente (`LLM_MAX_RETRIES`) |
| RNF-05 | Segurança | Chaves só por variável de ambiente; nunca em log, imagem ou repositório |
| RNF-06 | Segurança | Leitura de XML (`.drawio`, Exchange Format) com resolução de entidades externas e acesso à rede **desligados** (proteção contra XXE) |
| RNF-07 | Segurança | Upload validado por extensão **e** conteúdo (assinatura do arquivo), além do tamanho |
| RNF-08 | Segurança | Containers rodam com usuário sem privilégio; só a `ui` expõe porta para fora |
| RNF-09 | Privacidade | A interface mostra que as entradas são enviadas ao DashScope (Alibaba Cloud, Singapura) |
| RNF-10 | Observabilidade | Logs em JSON. Toda chamada ao LLM registra sessão, nó do grafo, modelo, tokens de entrada e saída, latência e resultado |
| RNF-11 | Rastreabilidade | Toda resposta da API leva um `request_id`, repetido nos logs |
| RNF-12 | Idioma | Interface, briefing, relatório e nomes dos elementos em **português do Brasil** |
| RNF-13 | Portabilidade | Tudo sobe com `docker compose up`, sem passos manuais além do `.env` |
| RNF-14 | Qualidade | ruff e mypy (modo estrito) sem erros; cobertura de testes mínima definida no harness |

## 6. Componentes

| Container | Responsabilidade | Exposto |
| --- | --- | --- |
| `ui` | Streamlit: sessões, chat, upload, briefing, progresso, downloads | Sim (porta 8501) |
| `agent-archimate` | FastAPI + LangGraph: interpretação, briefing, modelagem, validação, relatório, base de conhecimento | Não |
| `tool-archi` | Archi 5 pela linha de comando, atrás de uma API mínima: converte Exchange Format em `.archimate` | Não |

Volumes:

- `sessions`: dados das sessões e o banco de checkpoints do LangGraph (`agent-archimate`).
- `kb`: a base de conhecimento, montada **somente leitura** no agente, exceto a pasta `propostas/`.

## 7. Modelo de dados

### 7.1 Sessão

```json
{
  "id": "S-20261108-0001",
  "titulo": "Portal de pedidos",
  "status": "aberta",
  "criada_em": "2026-11-08T10:00:00-03:00",
  "entradas": ["E-001", "E-002"],
  "briefing_confirmado_em": null,
  "versoes_modelo": ["M-001"],
  "tokens_usados": 12450
}
```

### 7.2 Entrada

```json
{
  "id": "E-002",
  "tipo": "transcricao",
  "formato": "vtt",
  "nome_arquivo": "reuniao-2026-11-07.vtt",
  "recebida_em": "2026-11-08T10:05:00-03:00",
  "tamanho_bytes": 48211,
  "conteudo_normalizado": "arquivo interno com o texto extraído, linha a linha"
}
```

Tipos: `texto`, `transcricao`, `desenho_drawio`, `desenho_imagem`.

### 7.3 Item do briefing

```json
{
  "id": "B-014",
  "tipo": "sistema",
  "nome": "API de Pedidos",
  "descricao": "Recebe pedidos do Portal Web e grava no PostgreSQL",
  "origens": [
    {"entrada": "E-002", "local": "00:03:12–00:03:40", "trecho": "o portal chama a API de Pedidos"},
    {"entrada": "E-003", "local": "página 1 / forma 'API de Pedidos'"}
  ],
  "confianca": "alta",
  "status": "ativo",
  "registrado_em": "2026-11-08T10:06:00-03:00",
  "superado_por": null,
  "relacionados": ["B-010", "B-015"]
}
```

| Tipo | Uso |
| --- | --- |
| `ator` | Pessoa, área ou organização |
| `processo` | Atividade ou fluxo de negócio |
| `servico` | Serviço oferecido (de negócio, aplicação ou tecnologia) |
| `sistema` | Aplicação, componente ou módulo de software |
| `interface` | Ponto de acesso (portal, API, tela) |
| `dado` | Informação, objeto de negócio, entidade de dados |
| `infraestrutura` | Servidor, cluster, banco, rede, plataforma |
| `ligacao` | Comunicação ou dependência entre dois itens (campos extras `de`, `para`, `rotulo`) |
| `requisito` | Necessidade ou restrição declarada |
| `decisao` | Algo que foi decidido |
| `hipotese` | Algo assumido, ainda não confirmado |
| `pendencia` | Algo em aberto |
| `conflito` | Informações que se contradizem (campo extra `itens`) |

Status: `ativo`, `superado`, `descartado`.

### 7.4 Modelo interno (antes da exportação)

```json
{
  "id": "M-001",
  "gerado_em": "2026-11-08T10:30:00-03:00",
  "elementos": [
    {"id": "id-7f3a…", "tipo": "ApplicationComponent", "nome": "API de Pedidos",
     "documentacao": "Recebe pedidos do Portal Web.", "origens": ["B-014"], "premissa": false}
  ],
  "relacoes": [
    {"id": "id-91c2…", "tipo": "Serving", "origem": "id-7f3a…", "destino": "id-2b8e…",
     "nome": "REST", "origens": ["B-021"], "premissa": false}
  ],
  "visoes": [
    {"id": "id-v01…", "nome": "Visão geral em camadas", "viewpoint": "Layered",
     "nos": [{"elemento": "id-7f3a…", "x": 240, "y": 300, "w": 120, "h": 55}],
     "conexoes": [{"relacao": "id-91c2…"}]}
  ],
  "validacao": {"viavel": true, "erros": [], "avisos": []}
}
```

Os ids seguem o padrão do Exchange Format (`id-` + UUID), para que o Archi os preserve.

### 7.5 Achado de validação

```json
{"criterio": "V2", "regra": "REL-PERMITIDA", "severidade": "erro",
 "elemento": "id-91c2…",
 "mensagem": "Relação Serving de DataObject para ApplicationComponent não é permitida no ArchiMate 3.2"}
```

## 8. Regras ArchiMate e validação

### 8.1 Elementos do MVP (ArchiMate 3.2)

| Camada | Elementos |
| --- | --- |
| Negócio (13) | BusinessActor, BusinessRole, BusinessCollaboration, BusinessInterface, BusinessProcess, BusinessFunction, BusinessInteraction, BusinessEvent, BusinessService, BusinessObject, Contract, Representation, Product |
| Aplicação (9) | ApplicationComponent, ApplicationCollaboration, ApplicationInterface, ApplicationFunction, ApplicationInteraction, ApplicationProcess, ApplicationEvent, ApplicationService, DataObject |
| Tecnologia (13) | Node, Device, SystemSoftware, TechnologyCollaboration, TechnologyInterface, Path, CommunicationNetwork, TechnologyFunction, TechnologyProcess, TechnologyInteraction, TechnologyEvent, TechnologyService, Artifact |

Fora do MVP: Motivação, Estratégia, Implementação e Migração, Física,
Grouping, Location e Junction.

**Relações:** Composition, Aggregation, Assignment, Realization, Serving, Access,
Influence, Triggering, Flow, Specialization, Association.

### 8.2 Critérios de viabilidade

| Critério | Verificação | Ferramenta |
| --- | --- | --- |
| **V1 — Formato** | Exchange Format válido contra os XSDs oficiais (modelo + visões) | `lxml` |
| **V2 — ArchiMate** | Todo tipo está na lista 8.1; toda relação (tipo, origem, destino) está em `relacoes.json` | Validador próprio |
| **V3 — Coerência** | Regras da seção 8.3 | Validador próprio |
| **V4 — Cobertura** | Itens `ativos` dos tipos `ator`, `processo`, `servico`, `sistema`, `interface`, `dado`, `infraestrutura` e `ligacao` têm ao menos um elemento ou relação; todo elemento tem origem ou é premissa | Validador próprio |
| **V5 — Archi** | `tool-archi` importa e salva sem erro | `tool-archi` |

### 8.3 Regras de coerência (V3)

| Id | Regra | Severidade |
| --- | --- | --- |
| COE-01 | Nenhum elemento sem relação | erro |
| COE-02 | Nenhuma relação com origem ou destino inexistente | erro |
| COE-03 | Nomes únicos por tipo de elemento | erro |
| COE-04 | Todo `ApplicationService` é realizado por um `ApplicationComponent`, `ApplicationFunction` ou `ApplicationProcess` | aviso |
| COE-05 | Todo `ApplicationComponent` está ligado à camada de Tecnologia (ex.: servido por `TechnologyService` ou realizado por `Artifact`) | aviso |
| COE-06 | Todo `BusinessProcess` tem um responsável (`Assignment` de ator ou papel) | aviso |
| COE-07 | Quando existem Negócio e Aplicação no modelo, pelo menos uma relação liga as duas camadas | aviso |
| COE-08 | Quando existem Aplicação e Tecnologia no modelo, pelo menos uma relação liga as duas camadas | aviso |
| COE-09 | Nenhuma visão com mais de 20 elementos; acima disso, a visão é dividida | aviso |
| COE-10 | Nomes seguem as convenções do vault (ex.: processos com verbo no infinitivo) | aviso |

A lista completa e os limites ficam em `kb/archimate/regras/coerencia.yaml`, para
ajustar sem mudar código.

### 8.4 Visões (viewpoints)

| Viewpoint | Elementos que entram | Gerada quando |
| --- | --- | --- |
| Layered | Todos, organizados em faixas: Negócio no topo, Aplicação no meio, Tecnologia embaixo | Sempre |
| Business Process Cooperation | Processos, funções, eventos, serviços e objetos de negócio, atores e papéis, e os componentes de aplicação que os servem | Há elementos de Negócio |
| Application Cooperation | Componentes, interfaces, serviços e objetos de dados de aplicação, e as relações entre eles | Há elementos de Aplicação |
| Technology Usage | Componentes de aplicação e os elementos de Tecnologia que os apoiam | Há elementos de Aplicação e de Tecnologia |

**Layout** (definido na F1, `agents/archimate/layout.py`):

1. Cada viewpoint escolhe os seus elementos.
2. Os elementos são ordenados por percurso em largura pelas ligações, para que elementos ligados fiquem perto.
3. Acima de 20 elementos, a visão é dividida em partes ("(1/2)", "(2/2)").
4. Cada camada vira uma faixa (grupo no Archi), de cima para baixo: Negócio, Aplicação, Tecnologia. Dentro da faixa, grade de até 6 colunas, elemento 120 × 55, espaço de 40.

Os limites ficam em `coerencia.yaml` (`limites`).

## 9. Fluxo do agente (LangGraph)

### 9.1 Grafo

```text
entrada ─► ler_entrada ─► interpretar ─► atualizar_briefing ─► esclarecer?
                                                                 │ sim → [pausa: perguntas ao arquiteto] → atualizar_briefing
                                                                 │ não
                                                                 ▼
                                                   [pausa: confirmar briefing]
                                                                 │
                                                                 ▼
                         modelar ─► validar ─(erro e rodada < 3)─► corrigir ─► validar
                                       │ ok ou rodada = 3
                                       ▼
                         gerar_visoes ─► exportar_exchange (V1) ─► converter_archi (V5) ─► relatorio ─► fim

mensagem ─► classificar ─┬─ pergunta     ─► responder
                         ├─ informacao   ─► atualizar_briefing
                         ├─ correcao     ─► atualizar_briefing (marca superado)
                         ├─ alternativa  ─► avaliar_alternativa ─► responder
                         └─ comando      ─► ação correspondente
```

- As **pausas** (perguntas, confirmação do briefing) são o próprio estado da sessão, guardado no volume `sessions`. Cada chamada da API roda um grafo curto do LangGraph (ex.: `ler_entrada → interpretar → atualizar_briefing → esclarecer`) e termina; a próxima chamada retoma a partir do estado salvo. Assim, a sessão sobrevive ao reinício do container sem checkpointer (decisão D-10).
- O LLM só propõe itens; o código aplica as regras do briefing (união, conflito, correção) e confere a origem: se o local citado não existe ou não contém o trecho, o agente procura o trecho na entrada (inclusive atravessando uma quebra de linha); sem achar, o item fica com confiança `baixa`.
- Respostas a perguntas entram como uma nova entrada de texto, interpretada com o contexto da pergunta; quando resolvem o item, ele fica `superado`.
- `ler_entrada` não usa LLM para `.txt`, `.md`, `.vtt`, `.srt`, `.docx` e `.drawio`; só imagens passam pelo modelo de visão.

### 9.1.1 Geração do modelo (F3)

- `POST /sessions/{id}/models` responde `202` com `job_id` e o id da versão (`M-001`, `M-002`…) e roda o grafo em segundo plano; `GET /sessions/{id}/events` transmite o progresso (Server-Sent Events) e termina com `event: fim`; `GET /sessions/{id}/jobs/{job}` mostra o estado do job.
- `modelar`: o LLM recebe o briefing confirmado, o guia de tipos montado a partir das fichas do vault (quando usar e quando não usar cada tipo) e as notas de padrões, anti-padrões e convenções.
- O agente liga as camadas diretamente (ex.: componente `Serving` processo) e só cria serviços ou interfaces intermediários quando o briefing os cita (decisão D-12).
- `validar` roda V2–V4; com erro e rodada < 3, `corrigir` devolve ao LLM o modelo e a lista exata de erros. Depois da 3ª rodada, o modelo segue como **não viável**.
- Elementos sem origem, ou só com origem em `pendencia`/`hipotese`, viram premissa com motivo (RF-MOD-06).
- `relatorio` grava `modelo.json`, `modelo.xml`, `modelo.archimate` (quando o Archi converte) e `relatorio.md` em `modelos/M-xxx/` na sessão; a sessão passa a `modelo_gerado`.
- Endpoints extras: `GET /sessions/{id}/models` (versões) e `GET /sessions/{id}/jobs/{job}`.

### 9.2 Ferramentas do agente

| Ferramenta | Entrada | Saída |
| --- | --- | --- |
| `buscar_vault` | texto da consulta, filtros (tipo de nota, camada) | notas mais relevantes + notas ligadas |
| `ficha_elemento` | tipo ArchiMate | ficha completa do elemento |
| `relacoes_permitidas` | tipo de origem, tipo de destino | lista de relações permitidas |
| `validar_modelo` | modelo interno | achados V2–V4 |
| `consultar_briefing` | filtros (tipo, status, ids) | itens do briefing |

## 10. Base de conhecimento

### 10.1 Estrutura

```text
kb/
├── core/
│   ├── glossario/              # termos do negócio (vazio no início)
│   └── convencoes/             # convenções gerais de nomes e idioma
└── archimate/
    ├── regras/
    │   ├── elementos.json      # metamodelo: tipo, camada, aspecto
    │   ├── relacoes.json       # relações permitidas, extraídas do Archi
    │   ├── coerencia.yaml      # regras e limites do V3
    │   └── xsd/                # XSDs oficiais do Exchange Format
    ├── vault/
    │   ├── elementos/          # uma ficha por elemento (35)
    │   ├── padroes/
    │   ├── antipadroes/
    │   └── convencoes/
    ├── exemplos/               # exemplos ouro
    └── propostas/              # aprendizados propostos pelo agente
```

### 10.2 Regras

`elementos.json`:

```json
[{"tipo": "ApplicationComponent", "camada": "aplicacao", "aspecto": "estrutura_ativa"}]
```

`relacoes.json` (gerado por script a partir do `relationships.xml` do Archi; não
editar à mão):

```json
{"versao_archimate": "3.2", "fonte": "Archi relationships.xml (commit …)",
 "permitidas": {"ApplicationComponent": {"ApplicationService": ["Realization", "Serving", "Association", "Flow", "Triggering"]}}}
```

O script guarda a versão do Archi e o commit de onde a tabela foi extraída.

### 10.3 Nota do vault

```markdown
---
id: elemento-application-component
tipo: elemento            # elemento | padrao | antipadrao | convencao
archimate: ApplicationComponent
camada: aplicacao
tags: [estrutura-ativa, software]
fontes:
  - "ArchiMate 3.2, seção 9.2.1"
  - "ArchiMate Cookbook"
status: revisado          # rascunho | revisado
revisado_por: Deive Leal
revisado_em: 2026-11-10
---

# Application Component

**Definição (com nossas palavras):** …

**Use quando:** …

**Não use quando:** … (ver [[elemento-application-service]], [[elemento-node]])

**Confusões comuns:** …

**Como nomear:** substantivo, nome do sistema ou módulo. Ex.: "API de Pedidos".

**Relações típicas:** realiza [[elemento-application-service]]; é servido por [[elemento-technology-service]].

**Exemplo:** …
```

- O texto da especificação ArchiMate **não é copiado**: as fichas são escritas com nossas palavras e citam a seção de origem.
- Só notas com `status: revisado` são usadas pelo agente. Rascunhos ficam disponíveis apenas para revisão.

### 10.4 Exemplos ouro

```text
kb/archimate/exemplos/EX-001-portal-pedidos/
├── entrada/               # arquivos de entrada (texto, transcrição, desenho)
├── briefing_esperado.json # itens que precisam aparecer
├── modelo_esperado.json   # elementos e relações mínimos esperados
└── notas.md               # o que o caso testa
```

Meta da F1: 5 exemplos; mais exemplos entram conforme o harness precisar.

### 10.5 Propostas de aprendizado

Arquivo `kb/archimate/propostas/AAAA-MM-DD-<assunto>.md` com: correção observada,
sessões em que ocorreu, nota proposta (no formato 10.3, `status: rascunho`) e
justificativa. A aprovação é feita por PR para a branch `agent/archimate`.

### 10.6 Busca no vault

- Busca por palavra (BM25), sem acento e sem diferenciar maiúsculas, separando nomes em CamelCase; segue os links `[[...]]` até 1 nível.
- Não há busca por embeddings no MVP: o Token Plan não oferece modelo de embeddings, e uma base pequena não precisa (arXiv 2506.05690).
- Enquanto as fichas não forem revisadas, `VAULT_INCLUIR_RASCUNHOS=true` permite usar os rascunhos. Com `false`, só notas `revisado` são usadas.

### 10.7 Origem das regras

- `relacoes.json` é extraído de `regras/fonte/relationships.xml`, copiado do Archi **5.10.0** (licença MIT, em `fonte/LICENSE-Archi.txt`), com o comando `python -m archagent.agents.archimate.kb_tools extract-relations`.
- `make kb-check` (ou `python -m archagent.agents.archimate.kb_tools check`) refaz a extração e compara.

## 11. Relatório de viabilidade

Markdown, uma seção por item:

1. **Resumo:** viável ou não, número de elementos e relações por camada, visões geradas.
2. **Entradas usadas:** lista com ids e nomes.
3. **Resultado da validação:** V1–V5, com erros e avisos.
4. **Rastreabilidade:** tabela item do briefing → elementos e relações.
5. **Premissas:** elementos criados sem origem direta, com o motivo.
6. **Pendências e conflitos** ainda abertos.
7. **Itens superados:** correções feitas durante a sessão.
8. **Consumo:** tokens e tempo de geração.

## 12. Limites

| Item | Limite |
| --- | --- |
| Arquivo de transcrição | 5 MB |
| Arquivo `.drawio` | 5 MB |
| Imagem | 10 MB; lado maior reduzido para até 2048 px antes do envio |
| Entradas por sessão | 20 |
| Perguntas de esclarecimento por rodada | 5 |
| Rodadas de correção na validação | 3 |
| Elementos por visão | 20 |

## 13. API do `agent-archimate` (FastAPI)

Base: `http://agent-archimate:8000` (rede interna). Respostas em JSON, com
`request_id`. Erros no formato `{"erro": {"codigo": "...", "mensagem": "..."}}`.

| Método | Caminho | Uso |
| --- | --- | --- |
| GET | `/health` | Saúde do serviço (inclui regras carregadas e acesso ao `tool-archi`) |
| POST | `/sessions` | Cria sessão `{titulo}` |
| GET | `/sessions` | Lista sessões |
| GET | `/sessions/{id}` | Detalhe da sessão |
| POST | `/sessions/{id}/inputs` | Envia entrada (multipart: arquivo, ou `texto`) |
| POST | `/sessions/{id}/messages` | Envia mensagem do chat `{texto}`; devolve `classe`, `acao`, `resposta` e `detalhes` |
| GET | `/sessions/{id}/briefing` | Briefing atual (filtros: `status`, `tipo`) |
| GET | `/sessions/{id}/questions` | Perguntas de esclarecimento pendentes |
| POST | `/sessions/{id}/questions/{qid}/answer` | Responde ou pula `{resposta}` / `{pular: true}` |
| POST | `/sessions/{id}/briefing/confirm` | Confirma o briefing |
| POST | `/sessions/{id}/models` | Inicia a geração do modelo; devolve `{job_id}` |
| GET | `/sessions/{id}/events` | Progresso em tempo real (Server-Sent Events) |
| GET | `/sessions/{id}/models/{mid}` | Modelo interno + validação |
| GET | `/sessions/{id}/models/{mid}/files/{tipo}` | Download: `exchange`, `archimate` ou `relatorio` |
| GET | `/sessions/{id}/usage` | Tokens usados e limite |

## 14. API do `tool-archi`

| Método | Caminho | Uso |
| --- | --- | --- |
| GET | `/health` | Archi disponível e versão |
| POST | `/convert` | Recebe o Exchange Format; devolve o `.archimate` ou o erro do Archi |

Comando verificado na F1 (Archi **5.10.0**, Linux 64, com tela virtual Xvfb):

```bash
xvfb-run -a -s "-screen 0 1280x1024x24" /opt/Archi/Archi \
  -application com.archimatetool.commandline.app -consoleLog -nosplash \
  --xmlexchange.import entrada.xml --saveModel saida.archimate
```

- O Archi precisa de GTK e de uma tela, mesmo pela linha de comando: o container instala `libgtk-3-0` e `xvfb`.
- Ao importar, o Archi também valida o XML contra os XSDs; um erro de validação aparece no log e o `.archimate` não é gerado.
- Uma conversão leva cerca de 7 s. As conversões são feitas uma por vez, porque o Archi usa uma única pasta de configuração.
- Em caso de falha, `/convert` devolve `422` com `{"erro": {"codigo": "archi_falhou", "mensagem", "log"}}`; o log vem sem as linhas de pilha Java e sem o ruído do GTK.
- O arquivo do Archi é baixado no build da imagem e conferido por SHA-256.

## 15. Interface (Streamlit)

| Área | Conteúdo |
| --- | --- |
| Barra lateral | Lista de sessões, botão "nova sessão", consumo de tokens, aviso de que as entradas vão para o DashScope |
| Chat | Conversa com o agente; upload de arquivos no próprio chat |
| Aba Entradas | Entradas da sessão, com id e tipo |
| Aba Briefing | Itens por tipo, com origem, confiança e status; destaque para conflitos e pendências; botão "confirmar briefing" |
| Aba Perguntas | Perguntas pendentes, com campo de resposta e opção de pular |
| Aba Modelo | Progresso da geração; resultado V1–V5; elementos por camada; downloads (`.archimate`, Exchange Format, relatório); versões anteriores |

A interface não tem lógica de agente: tudo passa pela API da seção 13
(`src/archagent/core/cliente.py`). A conversa usa `POST /sessions/{id}/messages`; enquanto o
agente não tiver esse endpoint, a mensagem vai como entrada de texto
(`POST /sessions/{id}/inputs`). O progresso da geração do modelo vem do fluxo SSE.

### 15.1 Servidor MCP

O container `mcp` expõe a mesma API como ferramentas MCP, para que um cliente como o
Claude Code conduza a sessão. Também não tem lógica de agente: cada ferramenta usa o
cliente `src/archagent/core/cliente.py`. Transporte *streamable HTTP* em `/mcp`, publicado
só em `127.0.0.1:${MCP_PORT}` (sem autenticação), com proteção contra *DNS rebinding*; ou
stdio, rodando `archagent-mcp` na máquina local.

| Ferramenta | Endpoint (seção 13) |
| --- | --- |
| `listar_sessoes`, `criar_sessao`, `ver_sessao` | `GET/POST /sessions`, `GET /sessions/{id}`, `/usage` |
| `enviar_texto` | `POST /sessions/{id}/inputs` (campo `texto`) |
| `enviar_arquivo` | `POST /sessions/{id}/inputs` (arquivo: `conteudo`, `conteudo_base64` ou `caminho` dentro de `MCP_PASTA_ARQUIVOS`) |
| `enviar_mensagem` | `POST /sessions/{id}/messages` |
| `ver_briefing`, `confirmar_briefing` | `GET /briefing`, `POST /briefing/confirm` |
| `listar_perguntas`, `responder_pergunta` | `GET /questions`, `POST /questions/{q}/answer` |
| `gerar_modelo` | `POST /models` e consulta a `GET /jobs/{job}` até terminar (`MCP_TIMEOUT_MODELO_SEGUNDOS`) |
| `ver_modelo` | `GET /models`, `GET /models/{m}` (resumo: validação, elementos, relações por nome, visões) |
| `baixar_arquivo` | `GET /models/{m}/files/{tipo}`; devolve o conteúdo ou grava em `MCP_PASTA_SAIDA` |

Erros da API chegam ao cliente como erro da ferramenta, com a mensagem e o código.

## 16. Configuração

| Variável | Uso | Onde |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | Chave do Model Studio | `agent-archimate` |
| `DASHSCOPE_BASE_URL` | Endpoint compatível com OpenAI | `agent-archimate` |
| `LLM_MODEL_TEXT` | Modelo de texto (`qwen3.8-max`) | `agent-archimate` |
| `LLM_MODEL_VISION` | Modelo de visão (`qwen3.8-max`) | `agent-archimate` |
| `LLM_ENABLE_THINKING` | Modo de raciocínio do Qwen3 (padrão `false`; ver decisão D-09 do acompanhamento) | `agent-archimate` |
| `LLM_TIMEOUT_SECONDS` | Tempo limite por chamada | `agent-archimate` |
| `LLM_MAX_RETRIES` | Novas tentativas | `agent-archimate` |
| `LLM_MAX_TOKENS_PER_SESSION` | Limite de tokens por sessão | `agent-archimate` |
| `EMBEDDING_MODEL` | Modelo de embeddings para o vault ⚠️ | `agent-archimate` |
| `AGENT_ARCHIMATE_URL` | Endereço do agente | `ui`, `mcp` |
| `MCP_PORT` | Porta local do servidor MCP (padrão 8700, só `127.0.0.1`) | `mcp` |
| `MCP_TRANSPORT` | `stdio` (padrão fora do container) ou `streamable-http` | `mcp` |
| `MCP_ALLOWED_HOSTS` | Cabeçalhos `Host` aceitos (lista JSON) | `mcp` |
| `MCP_PASTA_ARQUIVOS` / `MCP_PASTA_SAIDA` | Pastas para ler entradas por caminho e gravar os arquivos do modelo (vazias = desligado) | `mcp` |
| `MCP_TIMEOUT_MODELO_SEGUNDOS` | Quanto `gerar_modelo` espera o job | `mcp` |
| `TOOL_ARCHI_URL` | Endereço do `tool-archi` | `agent-archimate` |
| `LOG_LEVEL` | Nível de log | todos |

## 17. Estrutura do repositório

```text
archagent/
├── docker-compose.yml            # inclui os arquivos de compose/
├── compose/
│   ├── ui.yml
│   ├── mcp.yml
│   ├── agent-archimate.yml
│   └── tool-archi.yml
├── src/archagent/
│   ├── core/                     # LLM (DashScope), leitores de entrada, briefing, logs
│   ├── agents/archimate/         # grafo, nós, ferramentas, modelagem, validadores, exportação, API
│   ├── ui/                       # app Streamlit
│   └── mcp/                      # servidor MCP (API do agente como ferramentas)
├── tools/archi/                  # Dockerfile e API mínima do tool-archi
├── kb/                           # base de conhecimento (seção 10)
├── scripts/                      # ex.: extrair relacoes.json do Archi
├── tests/                        # unitários e de integração
├── evals/                        # harness de avaliação (detalhado em docs/harness.md)
├── docs/
├── pyproject.toml
├── .env.example
└── README.md
```

## 18. Critérios de aceite da Etapa 1

| Id | Critério |
| --- | --- |
| CA-01 | `docker compose up` sobe `ui`, `agent-archimate` e `tool-archi` saudáveis |
| CA-02 | Os 5 exemplos ouro geram briefing com todos os itens esperados |
| CA-03 | Os 5 exemplos ouro geram modelo viável (V1–V5) |
| CA-04 | Ao menos um exemplo usa `.drawio` e um usa imagem |
| CA-05 | Uma correção feita na conversa atualiza o briefing (item antigo superado) e o novo modelo continua viável |
| CA-06 | Uma alternativa proposta recebe prós, contras, impacto e conflitos |
| CA-07 | O `.archimate` gerado abre no Archi 5 e as visões são legíveis (verificação manual) |
| CA-08 | O relatório traz rastreabilidade completa e lista as premissas |
| CA-09 | Nenhuma chave aparece em logs ou no repositório |

## 19. Pontos a verificar ou decidir ⚠️

- [x] Comando exato da linha de comando do Archi 5 e necessidade de Xvfb (F1: verificado, seção 14).
- [x] Algoritmo de layout das visões (F1: seção 8.4).
- [x] Checkpointer do LangGraph em SQLite no volume `sessions`: não é necessário; o estado fica na sessão (seção 9.1, decisão D-10).
- [x] Modelo de embeddings para a busca no vault: no MVP, só busca por palavra (BM25), seção 10.6.
- [x] Versões exatas dos XSDs do Exchange Format: os que vêm no Archi 5.10.0 (namespace `archimate/3.0`, `schemaLocation` 3.1), em `kb/archimate/regras/xsd/`.
