---
id: elemento-node
tipo: elemento
archimate: Node
camada: tecnologia
tags: [estrutura-ativa, servidor, cluster, nuvem, infraestrutura]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Nó (Node)

**Definição (com nossas palavras):** Um recurso de computação onde software roda ou dados ficam: servidor, máquina virtual, cluster, conta de nuvem.

**Use quando:** a entrada cita servidor, VM, cluster Kubernetes, ambiente de nuvem ou contêiner como ambiente de execução.

**Não use quando:** é o software de base (use [[elemento-system-software]]); é um equipamento físico de usuário (use [[elemento-device]]).

**Confusões comuns:** Nó × Software de sistema: o cluster é nó; o Kubernetes ou o PostgreSQL rodando nele é software de sistema.

**Como nomear:** substantivo do recurso. Ex.: "Cluster Kubernetes de produção".

**Relações típicas:** é composto por (Composition) [[elemento-system-software]] e [[elemento-device]]; é atribuído (Assignment) a [[elemento-system-software]] e [[elemento-artifact]] que nele rodam; realiza [[elemento-technology-service]]; serve [[elemento-application-component]]; é ligado por [[elemento-communication-network]].

**Exemplo:** "Servidor de aplicação" servindo a "API de Pedidos".
