---
id: elemento-business-event
tipo: elemento
archimate: BusinessEvent
camada: negocio
tags: [comportamento, gatilho]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Evento de negócio (BusinessEvent)

**Definição (com nossas palavras):** Algo que acontece num momento e dispara ou encerra comportamento do negócio, como 'pedido recebido'.

**Use quando:** a entrada fala de algo que acontece e inicia um fluxo: chegada de pedido, fim do mês, reclamação recebida.

**Não use quando:** é uma atividade com duração (use [[elemento-business-process]]).

**Confusões comuns:** Evento × Processo: evento não tem duração; processo tem.

**Como nomear:** fato no particípio. Ex.: "Pedido recebido".

**Relações típicas:** dispara (Triggering) [[elemento-business-process]].

**Exemplo:** "Pedido recebido" dispara "Separar pedido".
