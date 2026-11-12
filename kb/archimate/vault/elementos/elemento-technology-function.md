---
id: elemento-technology-function
tipo: elemento
archimate: TechnologyFunction
camada: tecnologia
tags: [comportamento, infraestrutura]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Função de tecnologia (TechnologyFunction)

**Definição (com nossas palavras):** Um comportamento interno de um nó ou software de sistema, como replicação ou balanceamento.

**Use quando:** a entrada detalha o que a infraestrutura faz por dentro.

**Não use quando:** o que importa é o que é oferecido (use [[elemento-technology-service]]).

**Confusões comuns:** Função × Serviço de tecnologia: a função é interna.

**Como nomear:** substantivo. Ex.: "Replicação de dados".

**Relações típicas:** recebe Assignment de [[elemento-node]] ou [[elemento-system-software]]; realiza [[elemento-technology-service]].

**Exemplo:** "Balanceamento de carga" do "Nginx".
