---
id: elemento-technology-interaction
tipo: elemento
archimate: TechnologyInteraction
camada: tecnologia
tags: [comportamento, sincronizacao]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Interação de tecnologia (TechnologyInteraction)

**Definição (com nossas palavras):** Um comportamento feito em conjunto por dois ou mais nós.

**Use quando:** a entrada descreve trocas entre nós, como sincronização entre réplicas.

**Não use quando:** um nó executa sozinho (use [[elemento-technology-function]]).

**Confusões comuns:** Interação × Flow entre nós.

**Como nomear:** verbo no infinitivo. Ex.: "Sincronizar réplicas".

**Relações típicas:** recebe Assignment de [[elemento-technology-collaboration]].

**Exemplo:** "Eleger líder" do cluster de réplicas.
