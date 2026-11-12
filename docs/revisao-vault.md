# Revisão do vault pelo arquiteto (P-12)

> Criado em 2026-11-09. **Concluído em 2026-11-12:** as 46 notas estão `revisado` (P-12 resolvida). O documento fica como registro da revisão.

A F1 só fecha quando as 46 notas de `kb/archimate/vault/` estiverem revisadas pelo
arquiteto (plano §3.7). Até a revisão, todas estavam em `rascunho`, e o agente as usava por causa de
`VAULT_INCLUIR_RASCUNHOS=true` (decisão D-07). Depois dela, o padrão voltou a `false`.

## 1. O que a pré-revisão já conferiu

Feita pelo Claude Code em 2026-11-09, sem marcar nada como revisado:

- **Direção das relações** em "Relações típicas", contra a tabela do Archi 5.10
  (`kb/archimate/regras/relacoes.json`, a mesma que o validador V2 usa).
- **Coerência entre notas** e com as decisões já tomadas (D-12: camadas ligadas direto por Serving).
- Formato, links `[[...]]` e campos obrigatórios: o `make kb-check` já confere.

Correções feitas (direção estava invertida ou ambígua):

| Nota | Antes | Depois |
| --- | --- | --- |
| `elemento-node` | "compõe" software de sistema e dispositivo | **é composto por** eles; é atribuído ao software e aos artefatos que nele rodam |
| `elemento-system-software` | "é atribuído ao nó" (Assignment SystemSoftware → Node não existe) | **recebe Assignment** do nó ou do dispositivo |
| `elemento-artifact` | "é atribuído ao nó" (Assignment Artifact → Node não existe) | **recebe Assignment** do nó |
| `elemento-business-function` | "compõe" processo (o exemplo dizia o contrário) | **é composta por** processos |
| `padrao-conteineres-e-nuvem` | a imagem "é atribuída ao nó" | o nó recebe a imagem por Assignment |
| `antipadrao-sistema-como-ator` | ligar o sistema ao negócio por um serviço de aplicação | Serving direto; serviço só quando a entrada o cita (D-12) |

## 2. O que fica para o arquiteto

A pré-revisão não substitui o seu julgamento sobre o **conteúdo**. Em cada nota, confira:

1. A definição está certa e clara para quem modela no dia a dia?
2. "Use quando" e "Não use quando" batem com a prática da sua equipe?
3. Os exemplos e os nomes seguem as convenções que vocês usam?
4. Falta alguma confusão comum que você já viu acontecer?

Para corrigir, edite a nota direto ou peça a mudança ao Claude Code.

## 3. Como marcar como revisada

```bash
# notas específicas
uv run python -m archagent.agents.archimate.kb_tools revisar --por "Deive Leal" elemento-node elemento-device
# todas as que ainda estão em rascunho
uv run python -m archagent.agents.archimate.kb_tools revisar --por "Deive Leal" --todas
make kb-check
```

O comando grava `status: revisado`, `revisado_por` e `revisado_em` (data de hoje).
Quando todas estiverem revisadas, `VAULT_INCLUIR_RASCUNHOS` pode voltar para `false`.

## 4. Lista das notas

### Elementos (35)

- [x] `elemento-application-collaboration` — Colaboração de aplicação (ApplicationCollaboration)
- [x] `elemento-application-component` — Componente de aplicação (ApplicationComponent)
- [x] `elemento-application-event` — Evento de aplicação (ApplicationEvent)
- [x] `elemento-application-function` — Função de aplicação (ApplicationFunction)
- [x] `elemento-application-interaction` — Interação de aplicação (ApplicationInteraction)
- [x] `elemento-application-interface` — Interface de aplicação (ApplicationInterface)
- [x] `elemento-application-process` — Processo de aplicação (ApplicationProcess)
- [x] `elemento-application-service` — Serviço de aplicação (ApplicationService)
- [x] `elemento-artifact` — Artefato (Artifact) — **corrigida na pré-revisão**
- [x] `elemento-business-actor` — Ator de negócio (BusinessActor)
- [x] `elemento-business-collaboration` — Colaboração de negócio (BusinessCollaboration)
- [x] `elemento-business-event` — Evento de negócio (BusinessEvent)
- [x] `elemento-business-function` — Função de negócio (BusinessFunction) — **corrigida na pré-revisão**
- [x] `elemento-business-interaction` — Interação de negócio (BusinessInteraction)
- [x] `elemento-business-interface` — Interface de negócio (BusinessInterface)
- [x] `elemento-business-object` — Objeto de negócio (BusinessObject)
- [x] `elemento-business-process` — Processo de negócio (BusinessProcess)
- [x] `elemento-business-role` — Papel de negócio (BusinessRole)
- [x] `elemento-business-service` — Serviço de negócio (BusinessService)
- [x] `elemento-communication-network` — Rede de comunicação (CommunicationNetwork)
- [x] `elemento-contract` — Contrato (Contract)
- [x] `elemento-data-object` — Objeto de dados (DataObject)
- [x] `elemento-device` — Dispositivo (Device)
- [x] `elemento-node` — Nó (Node) — **corrigida na pré-revisão**
- [x] `elemento-path` — Caminho (Path)
- [x] `elemento-product` — Produto (Product)
- [x] `elemento-representation` — Representação (Representation)
- [x] `elemento-system-software` — Software de sistema (SystemSoftware) — **corrigida na pré-revisão**
- [x] `elemento-technology-collaboration` — Colaboração de tecnologia (TechnologyCollaboration)
- [x] `elemento-technology-event` — Evento de tecnologia (TechnologyEvent)
- [x] `elemento-technology-function` — Função de tecnologia (TechnologyFunction)
- [x] `elemento-technology-interaction` — Interação de tecnologia (TechnologyInteraction)
- [x] `elemento-technology-interface` — Interface de tecnologia (TechnologyInterface)
- [x] `elemento-technology-process` — Processo de tecnologia (TechnologyProcess)
- [x] `elemento-technology-service` — Serviço de tecnologia (TechnologyService)

### Padrões (4)

- [x] `padrao-banco-de-dados` — Dados guardados em banco
- [x] `padrao-camadas-ligadas` — Camadas ligadas por serviços
- [x] `padrao-conteineres-e-nuvem` — Aplicações em contêineres e nuvem — **corrigida na pré-revisão**
- [x] `padrao-integracao-por-api` — Integração entre sistemas por API

### Antipadrões (4)

- [x] `antipadrao-associacao-generica` — Association para tudo
- [x] `antipadrao-banco-como-componente` — Banco de dados como componente de aplicação
- [x] `antipadrao-elemento-solto` — Elemento solto
- [x] `antipadrao-sistema-como-ator` — Sistema modelado como ator de negócio — **corrigida na pré-revisão**

### Convenções (3)

- [x] `convencao-escolha-de-relacoes` — Escolha da relação
- [x] `convencao-nomes` — Nomes dos elementos
- [x] `convencao-origem-e-premissa` — Origem e premissa

## 5. Resultado da revisão (2026-11-12)

Revisão do arquiteto (Deive Leal), em 5 lotes, com apoio do Claude Code. Todas as
relações citadas nas notas foram conferidas contra `kb/archimate/regras/relacoes.json`
(Archi 5.10): nenhuma proibida. Mudanças de conteúdo aprovadas:

| Nota | Mudança |
| --- | --- |
| `convencao-escolha-de-relacoes` | Realization cobre também artefato → componente e objeto de dados → objeto de negócio |
| `convencao-nomes` | Regras para serviços (substantivo de ação, sem repetir o processo) e funções (área de atuação) |
| `padrao-camadas-ligadas` | Ator → papel → processo quando a entrada cita cargo ou papel |
| `padrao-integracao-por-api` | Direção da Composition explícita; a interface pode servir quem chama quando não há serviço citado |
| `elemento-business-process`, `elemento-business-function` | Servidos diretamente pelo componente (D-12); serviço só quando citado |
| `elemento-business-service`, `elemento-application-service`, `elemento-application-function` | Regras de nome alinhadas à convenção |
| `elemento-contract` | "Ligado a produto" vira Aggregation pelo produto |
| `elemento-business-event` | Também pode ser disparado por processo (evento de fim) |
| `elemento-business-actor` | "Usa interface" vira Serving da interface ou Composition |
| `elemento-application-interface` | Exemplo "Portal Web" como interface contradizia o prompt e a D-11; agora "Tela de checkout" do componente "Portal Web" |
| `elemento-application-component` | Inclui o Serving direto ao processo de negócio (D-12); exemplo sem serviço inventado |
| `elemento-device` | "Compõe nó" vira Composition nó → dispositivo |
| `elemento-path` | Exemplo "VPN" contradizia a nota de rede; agora "Ligação matriz–filial" realizada pela "VPN corporativa" |
