---
id: elemento-application-process
tipo: elemento
archimate: ApplicationProcess
camada: aplicacao
tags: [comportamento, automacao, batch]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Processo de aplicação (ApplicationProcess)

**Definição (com nossas palavras):** Uma sequência de passos automáticos executada por software, com resultado definido.

**Use quando:** a entrada descreve um job, um batch ou uma orquestração automática em etapas.

**Não use quando:** não há sequência (use [[elemento-application-function]]); são pessoas que executam (use [[elemento-business-process]]).

**Confusões comuns:** Processo de aplicação × de negócio: o de aplicação é automático.

**Como nomear:** verbo no infinitivo + objeto. Ex.: "Processar pagamentos".

**Relações típicas:** recebe Assignment de [[elemento-application-component]]; realiza [[elemento-application-service]]; é disparado por [[elemento-application-event]].

**Exemplo:** "Conciliar pagamentos" executado pelo componente "Financeiro".
