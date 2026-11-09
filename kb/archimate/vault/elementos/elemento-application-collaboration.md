---
id: elemento-application-collaboration
tipo: elemento
archimate: ApplicationCollaboration
camada: aplicacao
tags: [estrutura-ativa, integracao]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Colaboração de aplicação (ApplicationCollaboration)

**Definição (com nossas palavras):** Um conjunto de componentes de aplicação que trabalham juntos para um comportamento comum.

**Use quando:** a entrada descreve vários sistemas que só juntos entregam algo, como uma integração entre ERP e CRM.

**Não use quando:** um componente só basta (use [[elemento-application-component]]).

**Confusões comuns:** Colaboração × fluxo entre componentes: use colaboração só quando o conjunto tem identidade própria.

**Como nomear:** substantivo coletivo. Ex.: "Integração Vendas".

**Relações típicas:** agrega [[elemento-application-component]]; é atribuída a [[elemento-application-interaction]].

**Exemplo:** "Integração ERP–CRM" agregando os dois componentes.
