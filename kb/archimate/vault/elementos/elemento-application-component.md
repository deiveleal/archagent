---
id: elemento-application-component
tipo: elemento
archimate: ApplicationComponent
camada: aplicacao
tags: [estrutura-ativa, software, sistema, modulo]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Componente de aplicação (ApplicationComponent)

**Definição (com nossas palavras):** Uma parte de software que pode ser implantada e trocada de forma independente: sistema, aplicação, microsserviço ou módulo.

**Use quando:** a entrada cita um sistema, uma aplicação, uma API como software, um microsserviço ou um módulo.

**Não use quando:** fala do que o software oferece (use [[elemento-application-service]]); do ponto de acesso (use [[elemento-application-interface]]); do servidor onde roda (use [[elemento-node]] ou [[elemento-system-software]]).

**Confusões comuns:** Componente × Serviço: o componente é o software; o serviço é o que ele oferece. Banco de dados como produto (PostgreSQL) é [[elemento-system-software]], não componente.

**Como nomear:** substantivo, nome do sistema ou módulo. Ex.: "API de Pedidos".

**Relações típicas:** realiza [[elemento-application-service]]; é servido por [[elemento-technology-service]] ou [[elemento-system-software]]; é realizado por [[elemento-artifact]]; acessa [[elemento-data-object]].

**Exemplo:** "API de Pedidos" realiza "Serviço de pedidos" e é servida pelo "PostgreSQL".
