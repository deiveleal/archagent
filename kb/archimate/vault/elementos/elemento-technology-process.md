---
id: elemento-technology-process
tipo: elemento
archimate: TechnologyProcess
camada: tecnologia
tags: [comportamento, rotina, backup]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Processo de tecnologia (TechnologyProcess)

**Definição (com nossas palavras):** Uma sequência de passos da infraestrutura, como backup, implantação ou rotação de logs.

**Use quando:** a entrada descreve rotinas de infraestrutura em etapas.

**Não use quando:** não há sequência (use [[elemento-technology-function]]).

**Confusões comuns:** Processo de tecnologia × de aplicação: o de tecnologia é da infraestrutura.

**Como nomear:** verbo no infinitivo. Ex.: "Fazer backup diário".

**Relações típicas:** recebe Assignment de [[elemento-node]] ou [[elemento-system-software]]; realiza [[elemento-technology-service]].

**Exemplo:** "Executar backup" do "Servidor de banco".
