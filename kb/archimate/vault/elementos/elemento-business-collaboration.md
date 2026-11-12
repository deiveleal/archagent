---
id: elemento-business-collaboration
tipo: elemento
archimate: BusinessCollaboration
camada: negocio
tags: [estrutura-ativa, parceria, conjunto]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Colaboração de negócio (BusinessCollaboration)

**Definição (com nossas palavras):** Um conjunto de atores ou papéis que trabalham juntos para um objetivo comum, de forma temporária ou permanente.

**Use quando:** a entrada fala de um comitê, uma parceria ou uma equipe formada por várias áreas para uma atividade conjunta.

**Não use quando:** um só ator basta (use [[elemento-business-actor]]).

**Confusões comuns:** Colaboração × Ator do tipo organização: a colaboração existe por causa da atividade conjunta.

**Como nomear:** substantivo coletivo. Ex.: "Comitê de Crédito".

**Relações típicas:** agrega [[elemento-business-role]] ou [[elemento-business-actor]]; é atribuída a [[elemento-business-interaction]].

**Exemplo:** "Comitê de Mudanças" agregando "Arquiteto" e "Gerente de operações".
