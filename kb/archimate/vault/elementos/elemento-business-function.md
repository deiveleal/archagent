---
id: elemento-business-function
tipo: elemento
archimate: BusinessFunction
camada: negocio
tags: [comportamento, capacidade, area]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Função de negócio (BusinessFunction)

**Definição (com nossas palavras):** Um agrupamento estável de comportamento do negócio, por competência ou recurso, sem sequência definida.

**Use quando:** a entrada fala de áreas de atuação, como 'Gestão de estoque' ou 'Contabilidade', sem descrever passos.

**Não use quando:** há passos em ordem (use [[elemento-business-process]]).

**Confusões comuns:** Função × Processo (ver [[elemento-business-process]]).

**Como nomear:** substantivo de atividade. Ex.: "Gestão de clientes".

**Relações típicas:** recebe Assignment de [[elemento-business-role]]; é composta por (Composition) [[elemento-business-process]]; é servida por [[elemento-application-component]] (ou por [[elemento-application-service]], quando a entrada o cita).

**Exemplo:** "Gestão de estoque" composta pelo processo "Repor produto".
