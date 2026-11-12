---
id: elemento-business-process
tipo: elemento
archimate: BusinessProcess
camada: negocio
tags: [comportamento, fluxo, atividade]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Processo de negócio (BusinessProcess)

**Definição (com nossas palavras):** Uma sequência de atividades do negócio que produz um resultado definido, com começo e fim.

**Use quando:** a entrada descreve passos em ordem, um fluxo ou algo que 'acontece quando...'.

**Não use quando:** o agrupamento é por competência e não tem sequência (use [[elemento-business-function]]); é um fato pontual (use [[elemento-business-event]]).

**Confusões comuns:** Processo × Função: processo tem ordem e resultado; função agrupa o que uma área sabe fazer. Processo de negócio × de aplicação: o de negócio é feito por pessoas.

**Como nomear:** verbo no infinitivo + objeto. Ex.: "Registrar pedido", "Aprovar crédito".

**Relações típicas:** recebe Assignment de [[elemento-business-actor]] ou [[elemento-business-role]]; é servido por [[elemento-application-component]] (ou por [[elemento-application-service]], quando a entrada o cita); realiza [[elemento-business-service]]; acessa [[elemento-business-object]]; dispara (Triggering) outros processos.

**Exemplo:** "Registrar pedido" atribuído ao "Cliente" e servido pelo componente "Sistema de Pedidos".
