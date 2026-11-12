---
id: elemento-contract
tipo: elemento
archimate: Contract
camada: negocio
tags: [estrutura-passiva, acordo, sla]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Contrato (Contract)

**Definição (com nossas palavras):** Um objeto de negócio que formaliza direitos e obrigações entre partes, como um contrato ou um SLA.

**Use quando:** a entrada fala de acordos, SLAs ou termos formais entre partes.

**Não use quando:** é só uma informação comum (use [[elemento-business-object]]).

**Confusões comuns:** Contrato é um tipo especial de objeto de negócio.

**Como nomear:** substantivo. Ex.: "Contrato de fornecimento".

**Relações típicas:** é acessado por [[elemento-business-process]]; é agregado (Aggregation) por [[elemento-product]].

**Exemplo:** "SLA de atendimento" agregado pelo produto "Suporte Premium".
