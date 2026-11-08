---
id: elemento-system-software
tipo: elemento
archimate: SystemSoftware
camada: tecnologia
tags: [estrutura-ativa, banco, sistema-operacional, middleware]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Software de sistema (SystemSoftware)

**Definição (com nossas palavras):** Software de base que dá ambiente para outros softwares: banco de dados, sistema operacional, servidor web, broker de mensagens.

**Use quando:** a entrada cita PostgreSQL, Oracle, Kafka, RabbitMQ, Nginx, Kubernetes, JVM.

**Não use quando:** é software do negócio (use [[elemento-application-component]]); é a máquina (use [[elemento-node]]).

**Confusões comuns:** Software de sistema × Componente: o banco é software de sistema; a aplicação que guarda os dados nele é componente.

**Como nomear:** nome do produto e papel. Ex.: "PostgreSQL", "Kafka de eventos".

**Relações típicas:** é atribuído a [[elemento-node]] (o nó compõe ou recebe Assignment); realiza [[elemento-technology-service]]; serve [[elemento-application-component]].

**Exemplo:** "PostgreSQL" servindo a "API de Pedidos".
