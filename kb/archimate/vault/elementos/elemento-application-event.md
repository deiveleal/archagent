---
id: elemento-application-event
tipo: elemento
archimate: ApplicationEvent
camada: aplicacao
tags: [comportamento, mensagem, gatilho]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Evento de aplicação (ApplicationEvent)

**Definição (com nossas palavras):** Algo que acontece no software e dispara comportamento: uma mensagem numa fila, um horário agendado.

**Use quando:** a entrada cita mensagens, eventos de domínio, webhooks ou agendamentos.

**Não use quando:** é um fato do negócio (use [[elemento-business-event]]).

**Confusões comuns:** Evento × Interface de fila: a fila é interface ou tecnologia; a mensagem é evento.

**Como nomear:** fato no particípio. Ex.: "Pagamento confirmado".

**Relações típicas:** dispara (Triggering) [[elemento-application-process]] ou [[elemento-application-function]].

**Exemplo:** "Pedido criado" dispara "Reservar estoque".
