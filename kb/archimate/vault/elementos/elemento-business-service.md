---
id: elemento-business-service
tipo: elemento
archimate: BusinessService
camada: negocio
tags: [comportamento, oferta, valor]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Serviço de negócio (BusinessService)

**Definição (com nossas palavras):** Algo útil que o negócio oferece a quem está fora dele, descrito pelo valor e não pelo como.

**Use quando:** a entrada fala do que a empresa oferece aos clientes ou a outras áreas.

**Não use quando:** é oferecido por software (use [[elemento-application-service]]).

**Confusões comuns:** Serviço × Processo: serviço é o que se oferece; processo é como se entrega.

**Como nomear:** substantivo ou verbo que expressa o valor. Ex.: "Entrega de pedidos".

**Relações típicas:** é realizado por [[elemento-business-process]]; serve [[elemento-business-actor]] e [[elemento-business-role]].

**Exemplo:** "Entrega em domicílio" realizado por "Entregar pedido".
