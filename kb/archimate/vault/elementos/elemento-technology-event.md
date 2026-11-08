---
id: elemento-technology-event
tipo: elemento
archimate: TechnologyEvent
camada: tecnologia
tags: [comportamento, alerta, gatilho]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Evento de tecnologia (TechnologyEvent)

**Definição (com nossas palavras):** Algo que acontece na infraestrutura e dispara comportamento: falha de nó, disco cheio, horário de backup.

**Use quando:** a entrada cita alertas, falhas ou agendamentos de infraestrutura.

**Não use quando:** é um evento do software (use [[elemento-application-event]]).

**Confusões comuns:** Evento de tecnologia × de aplicação.

**Como nomear:** fato no particípio. Ex.: "Disco cheio".

**Relações típicas:** dispara [[elemento-technology-process]].

**Exemplo:** "Nó indisponível" dispara "Fazer failover".
