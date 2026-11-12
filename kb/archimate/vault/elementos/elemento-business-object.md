---
id: elemento-business-object
tipo: elemento
archimate: BusinessObject
camada: negocio
tags: [estrutura-passiva, informacao, conceito]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Objeto de negócio (BusinessObject)

**Definição (com nossas palavras):** Um conceito de informação importante para o negócio, como pedido, contrato ou cliente, sem dizer como é guardado.

**Use quando:** a entrada cita informações que o negócio usa: pedido, nota fiscal, cadastro.

**Não use quando:** é a estrutura de dados num sistema (use [[elemento-data-object]]); é um documento formal com obrigações (use [[elemento-contract]]).

**Confusões comuns:** Objeto de negócio × Objeto de dados: um é o conceito; o outro, os dados no sistema, que realizam o conceito.

**Como nomear:** substantivo no singular. Ex.: "Pedido".

**Relações típicas:** é acessado (Access) por [[elemento-business-process]]; é realizado por [[elemento-data-object]] e [[elemento-representation]].

**Exemplo:** "Pedido" lido e escrito por "Registrar pedido".
