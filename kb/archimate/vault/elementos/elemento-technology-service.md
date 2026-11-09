---
id: elemento-technology-service
tipo: elemento
archimate: TechnologyService
camada: tecnologia
tags: [comportamento, hospedagem, armazenamento, mensageria]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Serviço de tecnologia (TechnologyService)

**Definição (com nossas palavras):** Algo útil que a infraestrutura oferece ao software: hospedagem, armazenamento, mensageria, banco como serviço.

**Use quando:** a entrada fala do que a plataforma oferece: 'banco gerenciado', 'fila', 'armazenamento de arquivos'.

**Não use quando:** é o produto ou a máquina (use [[elemento-system-software]] ou [[elemento-node]]).

**Confusões comuns:** Serviço de tecnologia × Software de sistema: serviço é o que se oferece; software é quem oferece.

**Como nomear:** substantivo. Ex.: "Armazenamento de objetos".

**Relações típicas:** é realizado por [[elemento-node]] ou [[elemento-system-software]]; serve [[elemento-application-component]].

**Exemplo:** "Banco de dados gerenciado" servindo a "API de Pedidos".
