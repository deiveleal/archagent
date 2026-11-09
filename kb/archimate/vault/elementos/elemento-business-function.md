---
id: elemento-business-function
tipo: elemento
archimate: BusinessFunction
camada: negocio
tags: [comportamento, capacidade, area]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Função de negócio (BusinessFunction)

**Definição (com nossas palavras):** Um agrupamento estável de comportamento do negócio, por competência ou recurso, sem sequência definida.

**Use quando:** a entrada fala de áreas de atuação, como 'Gestão de estoque' ou 'Contabilidade', sem descrever passos.

**Não use quando:** há passos em ordem (use [[elemento-business-process]]).

**Confusões comuns:** Função × Processo (ver [[elemento-business-process]]).

**Como nomear:** substantivo de atividade. Ex.: "Gestão de clientes".

**Relações típicas:** recebe Assignment de [[elemento-business-role]]; compõe [[elemento-business-process]]; é servida por [[elemento-application-service]].

**Exemplo:** "Gestão de estoque" composta pelo processo "Repor produto".
