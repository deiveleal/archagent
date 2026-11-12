---
id: elemento-technology-interface
tipo: elemento
archimate: TechnologyInterface
camada: tecnologia
tags: [estrutura-ativa, porta, protocolo]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Interface de tecnologia (TechnologyInterface)

**Definição (com nossas palavras):** O ponto de acesso a serviços de tecnologia: uma porta, um protocolo, um endpoint de infraestrutura.

**Use quando:** a entrada cita portas, protocolos ou endpoints técnicos, como 'porta 5432' ou 'JDBC'.

**Não use quando:** é a API de negócio do software (use [[elemento-application-interface]]).

**Confusões comuns:** Interface de tecnologia × de aplicação: a de tecnologia é de infraestrutura.

**Como nomear:** substantivo. Ex.: "JDBC 5432".

**Relações típicas:** faz parte de [[elemento-node]] ou [[elemento-system-software]]; serve [[elemento-application-component]].

**Exemplo:** "Endpoint JDBC" do "PostgreSQL".
