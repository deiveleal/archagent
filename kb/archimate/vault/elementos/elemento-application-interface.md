---
id: elemento-application-interface
tipo: elemento
archimate: ApplicationInterface
camada: aplicacao
tags: [estrutura-ativa, api, tela, endpoint]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Interface de aplicação (ApplicationInterface)

**Definição (com nossas palavras):** O ponto de acesso pelo qual um componente oferece os seus serviços: uma tela, uma API REST, uma fila.

**Use quando:** a entrada cita uma tela, um endpoint, uma API REST/GraphQL ou um contrato de integração.

**Não use quando:** o foco é o software em si (use [[elemento-application-component]]); o canal é do negócio (use [[elemento-business-interface]]).

**Confusões comuns:** Interface × Componente: 'API de Pedidos' como sistema é componente; 'REST /pedidos' é interface dele.

**Como nomear:** substantivo do ponto de acesso. Ex.: "API REST de pedidos", "Tela de checkout".

**Relações típicas:** faz parte (Composition) de [[elemento-application-component]]; serve [[elemento-business-actor]] ou outro componente; disponibiliza [[elemento-application-service]] (Assignment).

**Exemplo:** "Portal Web" (tela) do componente "Front-end de vendas".
