---
id: elemento-technology-collaboration
tipo: elemento
archimate: TechnologyCollaboration
camada: tecnologia
tags: [estrutura-ativa, cluster]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Colaboração de tecnologia (TechnologyCollaboration)

**Definição (com nossas palavras):** Um conjunto de nós que trabalham juntos para um comportamento comum, como um cluster de alta disponibilidade.

**Use quando:** a entrada descreve nós que só juntos oferecem algo, como réplicas de banco.

**Não use quando:** um nó basta (use [[elemento-node]]).

**Confusões comuns:** Colaboração × Nó do tipo cluster: escolha uma forma e mantenha.

**Como nomear:** substantivo coletivo. Ex.: "Réplicas do banco".

**Relações típicas:** agrega [[elemento-node]]; é atribuída a [[elemento-technology-interaction]].

**Exemplo:** "Cluster de réplicas" agregando três nós.
