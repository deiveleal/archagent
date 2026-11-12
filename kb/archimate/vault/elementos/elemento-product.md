---
id: elemento-product
tipo: elemento
archimate: Product
camada: negocio
tags: [composto, oferta, pacote]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Produto (Product)

**Definição (com nossas palavras):** Um pacote de serviços, e às vezes de objetos e contratos, oferecido como um todo aos clientes.

**Use quando:** a entrada fala de um produto vendido ou de um pacote de serviços com nome comercial.

**Não use quando:** é um único serviço (use [[elemento-business-service]]).

**Confusões comuns:** Produto × Serviço: produto agrega serviços e contratos.

**Como nomear:** nome comercial. Ex.: "Conta Digital".

**Relações típicas:** agrega [[elemento-business-service]], [[elemento-application-service]] e [[elemento-contract]].

**Exemplo:** "Plano Família" agregando "Suporte" e "Contrato do plano".
