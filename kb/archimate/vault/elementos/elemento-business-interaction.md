---
id: elemento-business-interaction
tipo: elemento
archimate: BusinessInteraction
camada: negocio
tags: [comportamento, conjunto]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Interação de negócio (BusinessInteraction)

**Definição (com nossas palavras):** Um comportamento feito em conjunto por dois ou mais atores ou papéis, que não dá para atribuir a um só.

**Use quando:** a entrada descreve uma negociação, reunião ou atividade que só existe com várias partes.

**Não use quando:** uma só parte executa (use [[elemento-business-process]]).

**Confusões comuns:** Interação × Processo com vários atores: na interação, ninguém executa sozinho.

**Como nomear:** verbo no infinitivo. Ex.: "Negociar contrato".

**Relações típicas:** recebe Assignment de [[elemento-business-collaboration]]; acessa [[elemento-business-object]].

**Exemplo:** "Negociar contrato" do "Comitê de Compras".
