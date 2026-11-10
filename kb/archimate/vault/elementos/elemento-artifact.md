---
id: elemento-artifact
tipo: elemento
archimate: Artifact
camada: tecnologia
tags: [estrutura-passiva, arquivo, pacote, imagem]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Artefato (Artifact)

**Definição (com nossas palavras):** Um arquivo ou pacote concreto implantado na infraestrutura: imagem de contêiner, JAR, script, arquivo de configuração.

**Use quando:** a entrada cita imagem Docker, pacote, binário ou arquivo implantado.

**Não use quando:** são os dados lógicos (use [[elemento-data-object]]).

**Confusões comuns:** Artefato × Objeto de dados: o artefato é o arquivo físico.

**Como nomear:** nome do arquivo ou pacote. Ex.: "pedidos-api:1.4 (imagem)".

**Relações típicas:** realiza [[elemento-application-component]] ou [[elemento-data-object]]; recebe Assignment do [[elemento-node]] onde é implantado.

**Exemplo:** "Imagem pedidos-api" realiza a "API de Pedidos" e é implantada no cluster.
