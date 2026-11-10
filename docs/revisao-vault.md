# Revisão do vault pelo arquiteto (P-12)

> Criado em 2026-11-09. Some quando a P-12 for resolvida (todas as notas `revisado`).

A F1 só fecha quando as 46 notas de `kb/archimate/vault/` estiverem revisadas pelo
arquiteto (plano §3.7). Hoje todas estão em `rascunho`, e o agente as usa por causa de
`VAULT_INCLUIR_RASCUNHOS=true` (decisão D-07).

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

- [ ] `elemento-application-collaboration` — Colaboração de aplicação (ApplicationCollaboration)
- [ ] `elemento-application-component` — Componente de aplicação (ApplicationComponent)
- [ ] `elemento-application-event` — Evento de aplicação (ApplicationEvent)
- [ ] `elemento-application-function` — Função de aplicação (ApplicationFunction)
- [ ] `elemento-application-interaction` — Interação de aplicação (ApplicationInteraction)
- [ ] `elemento-application-interface` — Interface de aplicação (ApplicationInterface)
- [ ] `elemento-application-process` — Processo de aplicação (ApplicationProcess)
- [ ] `elemento-application-service` — Serviço de aplicação (ApplicationService)
- [ ] `elemento-artifact` — Artefato (Artifact) — **corrigida na pré-revisão**
- [ ] `elemento-business-actor` — Ator de negócio (BusinessActor)
- [ ] `elemento-business-collaboration` — Colaboração de negócio (BusinessCollaboration)
- [ ] `elemento-business-event` — Evento de negócio (BusinessEvent)
- [ ] `elemento-business-function` — Função de negócio (BusinessFunction) — **corrigida na pré-revisão**
- [ ] `elemento-business-interaction` — Interação de negócio (BusinessInteraction)
- [ ] `elemento-business-interface` — Interface de negócio (BusinessInterface)
- [ ] `elemento-business-object` — Objeto de negócio (BusinessObject)
- [ ] `elemento-business-process` — Processo de negócio (BusinessProcess)
- [ ] `elemento-business-role` — Papel de negócio (BusinessRole)
- [ ] `elemento-business-service` — Serviço de negócio (BusinessService)
- [ ] `elemento-communication-network` — Rede de comunicação (CommunicationNetwork)
- [ ] `elemento-contract` — Contrato (Contract)
- [ ] `elemento-data-object` — Objeto de dados (DataObject)
- [ ] `elemento-device` — Dispositivo (Device)
- [ ] `elemento-node` — Nó (Node) — **corrigida na pré-revisão**
- [ ] `elemento-path` — Caminho (Path)
- [ ] `elemento-product` — Produto (Product)
- [ ] `elemento-representation` — Representação (Representation)
- [ ] `elemento-system-software` — Software de sistema (SystemSoftware) — **corrigida na pré-revisão**
- [ ] `elemento-technology-collaboration` — Colaboração de tecnologia (TechnologyCollaboration)
- [ ] `elemento-technology-event` — Evento de tecnologia (TechnologyEvent)
- [ ] `elemento-technology-function` — Função de tecnologia (TechnologyFunction)
- [ ] `elemento-technology-interaction` — Interação de tecnologia (TechnologyInteraction)
- [ ] `elemento-technology-interface` — Interface de tecnologia (TechnologyInterface)
- [ ] `elemento-technology-process` — Processo de tecnologia (TechnologyProcess)
- [ ] `elemento-technology-service` — Serviço de tecnologia (TechnologyService)

### Padrões (4)

- [ ] `padrao-banco-de-dados` — Dados guardados em banco
- [ ] `padrao-camadas-ligadas` — Camadas ligadas por serviços
- [ ] `padrao-conteineres-e-nuvem` — Aplicações em contêineres e nuvem — **corrigida na pré-revisão**
- [ ] `padrao-integracao-por-api` — Integração entre sistemas por API

### Antipadrões (4)

- [ ] `antipadrao-associacao-generica` — Association para tudo
- [ ] `antipadrao-banco-como-componente` — Banco de dados como componente de aplicação
- [ ] `antipadrao-elemento-solto` — Elemento solto
- [ ] `antipadrao-sistema-como-ator` — Sistema modelado como ator de negócio — **corrigida na pré-revisão**

### Convenções (3)

- [ ] `convencao-escolha-de-relacoes` — Escolha da relação
- [ ] `convencao-nomes` — Nomes dos elementos
- [ ] `convencao-origem-e-premissa` — Origem e premissa
